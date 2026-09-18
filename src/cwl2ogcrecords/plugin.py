# Copyright 2026 Transpiler-Mate
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
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from loguru import logger
from pydantic import AnyUrl, BaseModel, ConfigDict, Field
from pystac import Link
from transpiler_mate.api import (
    AuthorRole,
    CreativeWork,
    DefinedTerm,
    Person,
    PluginExecutionError,
    SoftwareApplication,
    transpiler_plugin,
)

from .ogc_record import (
    Contact,
    ContactDetail,
    Language,
    OGCRecord,
    OrganizationContact,
    Theme,
    ThemeConcept,
)

if TYPE_CHECKING:
    from transpiler_mate.api import TranspilerContext


__DEFAULT_LANGUAGE__: Language = Language(code="en-US", name="English (United States)")


class CWL2OGCAPIRecordsOptions(BaseModel):
    """Options accepted by the CWL to OGC API - Records plugin."""

    model_config = ConfigDict(extra="forbid")

    output: Annotated[
        Path,
        Field(default=Path("ogc-record.json"), description="The output file path"),
    ]


def _to_datetime(value: date | datetime) -> str:
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.isoformat()
        return value.replace(tzinfo=timezone.utc).isoformat()
    return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc).isoformat()


def _add_kw_themes(metadata: SoftwareApplication, record: OGCRecord):
    record.keywords = []
    record.themes = []
    themes: dict[AnyUrl, Theme] = {}

    if metadata.keywords:
        for raw_keyword in (
            metadata.keywords
            if isinstance(metadata.keywords, list)
            else [metadata.keywords]
        ):
            if isinstance(raw_keyword, str):
                record.keywords.append(raw_keyword)
            elif (
                isinstance(raw_keyword, DefinedTerm)
                and raw_keyword.in_defined_term_set
                and raw_keyword.term_code
                and raw_keyword.name
                and raw_keyword.description
            ):
                scheme: AnyUrl = raw_keyword.in_defined_term_set
                theme = themes.get(scheme)

                if theme is None:
                    theme = Theme(scheme=str(scheme), concepts=[])
                    themes[scheme] = theme

                theme["concepts"].append(
                    ThemeConcept(
                        id=raw_keyword.term_code,
                        title=raw_keyword.name,
                        description=raw_keyword.description,
                        url=str(raw_keyword.in_defined_term_set),
                    )
                )

        if themes:
            for theme in themes.values():
                record.themes.append(theme)


def _add_help_links(metadata: SoftwareApplication, record: OGCRecord):
    for creative_work in (
        metadata.software_help
        if isinstance(metadata.software_help, list)
        else [metadata.software_help]
    ):
        if creative_work.url:
            record.add_link(
                Link(
                    rel="help", target=str(creative_work.url), title=creative_work.name
                )
            )


def _to_contact(author: Person | AuthorRole) -> Contact:
    position: str = "N/A"

    if isinstance(author, AuthorRole):
        position = author.role_name
        author = author.author

    affiliations = (
        author.affiliation
        if isinstance(author.affiliation, list)
        else [author.affiliation]
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
def cwl2ogcrecords(
    context: TranspilerContext, options: CWL2OGCAPIRecordsOptions
) -> None:
    """CWL to OGC API - Records Transpiler-Mate Plugin."""
    logger.info("Converting input CWL to OGC API - Records...")

    record: OGCRecord = OGCRecord(
        id=context.process_id if context.process_id else f"urn:uuid:{uuid.uuid4()}",
    )
    record.created = _to_datetime(context.metadata.date_created)
    record.updated = _to_datetime(datetime.now())
    record.title = context.metadata.name
    record.description = (
        context.metadata.description if context.metadata.description else None
    )
    record.language = __DEFAULT_LANGUAGE__
    record.resource_languages = [__DEFAULT_LANGUAGE__]

    record.license = ": ".join(
        [
            (
                str(license.identifier)
                if isinstance(license, CreativeWork)
                else str(license)
            )
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

    logger.success("Input CWL successfully converted to OGC API - Records!")

    try:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Serializing CodeMeta metadata to {options.output.absolute()}")

        with options.output.open("w") as output_stream:
            json.dump(
                record.to_dict(include_self_link=False),
                output_stream,
                indent=2,
                )

        logger.success(
            f"CodeMeta metadata successfully serialized to {options.output.absolute()}"
        )
    except Exception as e:
        raise PluginExecutionError(
            f"An error occurred when serializing to {options.output.absolute()}, see nested exception"
        ) from e
