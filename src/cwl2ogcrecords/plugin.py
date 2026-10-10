# Copyright 2026 Terradue
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""transpiler-mate plugin for CWL to OGC API - Records."""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from urllib.parse import unquote, urlsplit

from loguru import logger
from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)
from pystac import Link
from pystac.extensions.ogc_record import (
    Contact,
    ContactDetail,
    Language,
    OGCRecord,
    OrganizationContact,
    Theme,
    ThemeConcept,
)
from pystac.extensions.scientific import Publication, ScientificExtension, doi_to_url
from pystac.extensions.version import VersionExtension
from transpiler_mate.api import (
    AuthorRole,
    CreativeWork,
    DefinedTerm,
    Person,
    PluginExecutionError,
    SoftwareApplication,
    transpiler_plugin,
)

if TYPE_CHECKING:
    from transpiler_mate.api import TranspilerContext


__DEFAULT_LANGUAGE__: Language = Language(code="en-US", name="English (United States)")


APPLICATION_SCHEMA = "https://stac-extensions.github.io/application/v0.1.0/schema.json"


def _normalize_doi(value: str) -> str:
    """Normalize a DOI name, doi: identifier, or DOI resolver URL.

    This checks syntax only; it does not resolve the DOI or prove registration.

    Raises:
        ValueError: If the value is not a supported DOI representation.
    """
    value = value.strip()
    if value.lower().startswith("doi:"):
        value = value[4:]
    elif value.lower().startswith(("https://", "http://")):
        parsed = urlsplit(value)
        if parsed.netloc.lower() not in {"doi.org", "dx.doi.org"}:
            raise ValueError("Expected a doi.org resolver URL")
        if parsed.query or parsed.fragment:
            raise ValueError("DOI resolver URLs must not have a query or fragment")
        value = unquote(parsed.path.lstrip("/"))
    if not re.fullmatch(r"10\.[0-9]{4,9}/[^\s]+", value):
        raise ValueError("Expected a DOI name such as 10.1234/example")
    return value


DOI = Annotated[str, AfterValidator(_normalize_doi)]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CWL2OGCAPIRecordsOptions(BaseModel):
    """Options accepted by the CWL to OGC API - Records plugin."""

    model_config = ConfigDict(extra="forbid")

    output: Annotated[
        Path,
        Field(default=Path("ogc-record.json"), description="The output file path"),
    ]

    application_url: AnyHttpUrl | None = Field(
        default=None, description="Public CWL URL; defaults to an HTTP(S) context.source"
    )
    repository_url: AnyHttpUrl | None = Field(default=None, description="Source repository URL")
    manifest_url: AnyHttpUrl | None = Field(
        default=None, description="CodeMeta or dependency manifest URL"
    )
    application_input_url: AnyHttpUrl | None = Field(
        default=None, description="Example input parameters URL"
    )
    version_history_url: AnyHttpUrl | None = Field(
        default=None, description="Release history or changelog URL"
    )
    workflow_citation: NonEmptyText | None = Field(
        default=None, description="Recommended citation for the workflow itself"
    )
    publication_dois: list[DOI] = Field(
        default_factory=list, description="DOIs of papers describing the workflow"
    )


def _add_application_links(
    context: TranspilerContext, options: CWL2OGCAPIRecordsOptions, record: OGCRecord
) -> None:
    """Attach explicitly known application resources without publishing local paths."""
    source = options.application_url
    if source is None and context.source.scheme in {"http", "https"}:
        source = AnyHttpUrl(str(context.source))
    if source is not None:
        link = Link("application", str(source), media_type="application/cwl")
        link.extra_fields["application:container"] = "Common Workflow Language"
        entrypoint = context.process_id
        if entrypoint:
            link.extra_fields["application:entrypoint"] = entrypoint
        record.add_link(link)
    for relation, target in (
        ("vcs", options.repository_url),
        ("manifest", options.manifest_url),
        ("application-input", options.application_input_url),
    ):
        if target is not None:
            record.add_link(Link(relation, str(target)))
    if source is not None:
        # Application currently has no accessor in the project's PySTAC dependency.
        record.stac_extensions.append(APPLICATION_SCHEMA)


def _add_scientific_metadata(
    metadata: SoftwareApplication, options: CWL2OGCAPIRecordsOptions, record: OGCRecord
) -> None:
    """Keep the workflow's own DOI distinct from papers describing it."""
    doi = None
    if metadata.identifier:
        try:
            doi = _normalize_doi(str(metadata.identifier))
        except ValueError:
            # A generic software identifier is valid metadata, but not a DOI.
            logger.debug("Skipping non-DOI software identifier: {}", metadata.identifier)

    if not (doi or options.workflow_citation or options.publication_dois):
        return

    ScientificExtension.ext(record, add_if_missing=True).apply(
        doi=doi, citation=options.workflow_citation
    )

    if options.publication_dois:
        # PySTAC's publications setter adds cite-as links for papers too.
        # Reserve cite-as for the workflow and link describing papers as related.
        publication_dois = list(dict.fromkeys(options.publication_dois))
        record.properties["sci:publications"] = [
            Publication(doi=value, citation=None).to_dict() for value in publication_dois
        ]
        for publication_doi in publication_dois:
            record.add_link(Link("related", doi_to_url(publication_doi)))


def _add_workflow_extensions(
    context: TranspilerContext, options: CWL2OGCAPIRecordsOptions, record: OGCRecord
) -> None:
    """Enrich a workflow definition without inventing execution provenance."""
    _add_application_links(context, options, record)
    version = context.metadata.software_version.strip()
    if version or options.version_history_url:
        version_extension = VersionExtension.ext(record, add_if_missing=True)
        if version:
            version_extension.version = version
        if options.version_history_url:
            record.add_link(Link("version-history", str(options.version_history_url)))


def _theme_concept(term: DefinedTerm, code: str) -> ThemeConcept:
    concept = ThemeConcept(id=code)
    if term.name:
        concept["title"] = term.name
    if term.description:
        concept["description"] = term.description
    return concept


def _to_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)
    return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)


def _add_kw_themes(metadata: SoftwareApplication, record: OGCRecord) -> None:
    """Populate keywords and group complete defined terms by their scheme."""
    record.keywords = []
    record.themes = []
    themes: dict[AnyUrl, Theme] = {}

    if metadata.keywords:
        for raw_keyword in (
            metadata.keywords if isinstance(metadata.keywords, list) else [metadata.keywords]
        ):
            if isinstance(raw_keyword, str):
                record.keywords.append(raw_keyword)
            elif (
                isinstance(raw_keyword, DefinedTerm)
                and raw_keyword.in_defined_term_set
                and raw_keyword.term_code
            ):
                scheme: AnyUrl = raw_keyword.in_defined_term_set
                theme = themes.get(scheme)

                if theme is None:
                    theme = Theme(scheme=str(scheme), concepts=[])
                    themes[scheme] = theme

                theme["concepts"].append(_theme_concept(raw_keyword, raw_keyword.term_code))

        record.themes.extend(themes.values())


def _add_help_links(metadata: SoftwareApplication, record: OGCRecord) -> None:
    """Add help links for software documentation with a URL."""
    for creative_work in (
        metadata.software_help
        if isinstance(metadata.software_help, list)
        else [metadata.software_help]
    ):
        if creative_work.url:
            record.add_link(
                Link(rel="help", target=str(creative_work.url), title=creative_work.name)
            )


def _to_contact(author: Person | AuthorRole) -> Contact:
    position: str = "N/A"

    if isinstance(author, AuthorRole):
        position = author.role_name
        author = author.author

    affiliations = (
        author.affiliation if isinstance(author.affiliation, list) else [author.affiliation]
    )

    def _to_contact_detail(email: str) -> ContactDetail:
        return ContactDetail(value=email)

    emails: list[ContactDetail] = list(
        map(
            _to_contact_detail,
            (author.email if isinstance(author.email, list) else [author.email]),
        )
    )

    return OrganizationContact(
        identifier=str(author.identifier),
        name=f"{author.family_name}, {author.given_name}",
        organization=affiliations[0].name,
        position=position,
        emails=emails,
    )


@transpiler_plugin(
    name="cwl2ogcrecords",
    description="CWL to OGC API - Records Transpiler-Mate Plugin.",
    options_model=CWL2OGCAPIRecordsOptions,
)
def cwl2ogcrecords(context: TranspilerContext, options: CWL2OGCAPIRecordsOptions) -> None:
    """CWL to OGC API - Records Transpiler-Mate Plugin."""
    logger.info("Converting input CWL to OGC API - Records...")

    record: OGCRecord = OGCRecord(
        id=context.process_id if context.process_id else f"urn:uuid:{uuid.uuid4()}",
    )
    record.created = _to_datetime(context.metadata.date_created)
    record.updated = _to_datetime(datetime.now(timezone.utc))
    record.title = context.metadata.name
    record.description = context.metadata.description if context.metadata.description else None
    record.language = __DEFAULT_LANGUAGE__
    record.resource_languages = [__DEFAULT_LANGUAGE__]

    record.license = ": ".join(
        [
            (str(license.identifier) if isinstance(license, CreativeWork) else str(license))
            for license in (
                context.metadata.license
                if isinstance(context.metadata.license, list)
                else [context.metadata.license]
            )
        ]
    )

    record.contacts = list(
        map(
            _to_contact,
            context.metadata.author
            if isinstance(context.metadata.author, list)
            else [context.metadata.author],
        )
    )

    _add_kw_themes(context.metadata, record)
    _add_help_links(context.metadata, record)
    _add_workflow_extensions(context, options, record)
    _add_scientific_metadata(context.metadata, options, record)

    logger.success("Input CWL successfully converted to OGC API - Records!")

    try:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Serializing OGC API - Records metadata to {options.output.absolute()}")

        with options.output.open("w") as output_stream:
            json.dump(
                record.to_dict(include_self_link=False),
                output_stream,
                indent=2,
            )

        logger.success(
            f"OGC API - Records metadata successfully serialized to {options.output.absolute()}"
        )
    except Exception as e:
        raise PluginExecutionError(
            f"An error occurred when serializing to {options.output.absolute()}, see nested exception"
        ) from e
