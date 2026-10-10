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

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from pydantic import AnyUrl, ValidationError
from transpiler_mate.api import (
    AuthorRole,
    CreativeWork,
    DefinedTerm,
    Person,
    PluginExecutionError,
    SoftwareApplication,
    TranspilerContext,
    TranspilerContextResolver,
)

from cwl2ogcrecords.plugin import CWL2OGCAPIRecordsOptions, cwl2ogcrecords


@pytest.fixture
def metadata() -> SoftwareApplication:
    return SoftwareApplication.model_validate(
        {
            "name": "Elevation workflow",
            "description": "Compute terrain elevation.",
            "dateCreated": "2026-01-02",
            "license": "https://spdx.org/licenses/Apache-2.0",
            "softwareVersion": "1.0.0",
            "identifier": "10.1234/workflow",
            "softwareHelp": {"name": "User guide", "url": "https://example.org/guide"},
            "publisher": {"name": "Example Institute"},
            "author": {
                "givenName": "Ada",
                "familyName": "Lovelace",
                "identifier": "https://example.org/ada",
                "email": "ada@example.org",
                "affiliation": {"name": "Example Institute"},
            },
        }
    )


@pytest.fixture
def context(metadata: SoftwareApplication) -> TranspilerContext:
    return TranspilerContext(
        source=AnyUrl("https://example.org/workflow.cwl"),
        process_id="elevation",
        metadata=metadata,
        document={},
        resolver=Mock(spec=TranspilerContextResolver),
    )


def _execute(context: TranspilerContext, output: Path) -> dict[str, object]:
    """Execute the public plugin and read the serialized JSON object."""
    cwl2ogcrecords.execute(context, CWL2OGCAPIRecordsOptions(output=output))
    document: object = json.loads(output.read_text())
    assert isinstance(document, dict)
    return document


def _properties(context: TranspilerContext, tmp_path: Path) -> dict[str, object]:
    properties = _execute(context, tmp_path / "record.json")["properties"]
    assert isinstance(properties, dict)
    return properties


def test_registration_and_default_options() -> None:
    assert cwl2ogcrecords.name == "cwl2ogcrecords"
    assert cwl2ogcrecords.options_model is CWL2OGCAPIRecordsOptions
    assert CWL2OGCAPIRecordsOptions.model_validate({}).output == Path("ogc-record.json")
    assert CWL2OGCAPIRecordsOptions.model_validate({"output": "custom.json"}).output == Path(
        "custom.json"
    )


@pytest.mark.parametrize("options", [{"unknown": True}, {"output": None}, {"output": 42}])
def test_invalid_options_are_rejected(options: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CWL2OGCAPIRecordsOptions.model_validate(options)


def test_serializes_metadata_and_creates_parent_directories(
    context: TranspilerContext, tmp_path: Path
) -> None:
    before = context.metadata.model_dump()
    # Serialized timestamps have whole-second precision.
    started = datetime.now(timezone.utc).replace(microsecond=0)
    document = _execute(context, tmp_path / "nested" / "output" / "record.json")
    finished = datetime.now(timezone.utc)
    assert document["type"] == "Feature"
    assert document["id"] == "elevation"
    assert document["geometry"] is None
    assert "stac_version" not in document
    properties = document["properties"]
    assert isinstance(properties, dict)
    assert properties["title"] == "Elevation workflow"
    assert properties["description"] == "Compute terrain elevation."
    assert properties["created"] == "2026-01-02T00:00:00Z"
    updated = properties["updated"]
    assert isinstance(updated, str)
    # Python 3.10 requires an explicit UTC offset instead of the Z suffix.
    assert started <= datetime.fromisoformat(updated.replace("Z", "+00:00")) <= finished
    assert properties["language"] == {"code": "en-US", "name": "English (United States)"}
    assert properties["resourceLanguages"] == [properties["language"]]
    assert properties["license"] == "https://spdx.org/licenses/Apache-2.0"
    assert properties["contacts"] == [
        {
            "identifier": "https://example.org/ada",
            "name": "Lovelace, Ada",
            "organization": "Example Institute",
            "position": "N/A",
            "emails": [{"value": "ada@example.org"}],
        }
    ]
    links = document["links"]
    assert isinstance(links, list)
    assert [link for link in links if link["rel"] == "help"] == [
        {"rel": "help", "href": "https://example.org/guide", "title": "User guide"}
    ]
    assert context.metadata.model_dump() == before


@pytest.mark.parametrize("process_id", [None, ""])
def test_generates_unique_uuid_when_process_id_is_missing(
    context: TranspilerContext, tmp_path: Path, process_id: str | None
) -> None:
    context = context.model_copy(update={"process_id": process_id})
    first = _execute(context, tmp_path / "first.json")["id"]
    second = _execute(context, tmp_path / "second.json")["id"]
    assert isinstance(first, str)
    assert isinstance(second, str)
    assert first.startswith("urn:uuid:")
    assert second.startswith("urn:uuid:")
    expected_version = 4
    assert UUID(first).version == UUID(second).version == expected_version
    assert first != second


@pytest.mark.parametrize(
    ("created", "expected"),
    [
        (date(2026, 1, 2), "2026-01-02T00:00:00Z"),
        (datetime(2026, 1, 2, 3, 4, 5), "2026-01-02T03:04:05Z"),
        (
            datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=2))),
            "2026-01-02T01:04:05Z",
        ),
    ],
)
def test_creation_date_normalization(
    context: TranspilerContext, tmp_path: Path, created: date | datetime, expected: str
) -> None:
    context.metadata.date_created = created
    assert _properties(context, tmp_path)["created"] == expected


def test_empty_description_is_omitted(context: TranspilerContext, tmp_path: Path) -> None:
    context.metadata.description = ""
    assert "description" not in _properties(context, tmp_path)


@pytest.mark.parametrize("multiple", [False, True])
def test_creative_work_licenses(context: TranspilerContext, tmp_path: Path, multiple: bool) -> None:
    license_work = CreativeWork(identifier="Apache-2.0")
    context.metadata.license = (
        [license_work, AnyUrl("https://example.org/license")] if multiple else license_work
    )
    expected = "Apache-2.0: https://example.org/license" if multiple else "Apache-2.0"
    assert _properties(context, tmp_path)["license"] == expected


def test_author_roles_multiple_emails_and_affiliations(
    context: TranspilerContext, tmp_path: Path
) -> None:
    author = context.metadata.author
    assert isinstance(author, Person)
    coauthor = Person.model_validate(
        {
            "givenName": "Grace",
            "familyName": "Hopper",
            "identifier": "grace",
            "email": ["grace@example.org", "hopper@example.org"],
            "affiliation": [{"name": "First Institute"}, {"name": "Second Institute"}],
        }
    )
    role = AuthorRole.model_validate({"roleName": "Maintainer", "author": coauthor})
    context.metadata.author = [author, role]
    contacts = _properties(context, tmp_path)["contacts"]
    assert isinstance(contacts, list)
    assert [contact["name"] for contact in contacts] == ["Lovelace, Ada", "Hopper, Grace"]
    assert contacts[1] == {
        "identifier": "grace",
        "name": "Hopper, Grace",
        "organization": "First Institute",
        "position": "Maintainer",
        "emails": [{"value": "grace@example.org"}, {"value": "hopper@example.org"}],
    }


@pytest.mark.parametrize("keywords", [None, "", [], "elevation", ["elevation", "terrain"]])
def test_plain_keywords(
    context: TranspilerContext, tmp_path: Path, keywords: str | list[str] | None
) -> None:
    context.metadata.keywords = list(keywords) if isinstance(keywords, list) else keywords
    properties = _properties(context, tmp_path)
    expected = [keywords] if isinstance(keywords, str) and keywords else keywords or []
    assert properties["keywords"] == expected
    assert properties["themes"] == []


def _term(code: str, scheme: str = "https://example.org/themes") -> DefinedTerm:
    return DefinedTerm.model_validate(
        {
            "termCode": code,
            "name": code.title(),
            "description": f"About {code}",
            "inDefinedTermSet": scheme,
        }
    )


def test_groups_terms_by_scheme(context: TranspilerContext, tmp_path: Path) -> None:
    context.metadata.keywords = [
        "terrain",
        _term("elevation"),
        _term("water", "https://example.org/other"),
        _term("slope"),
    ]
    properties = _properties(context, tmp_path)
    assert properties["keywords"] == ["terrain"]
    assert properties["themes"] == [
        {
            "scheme": "https://example.org/themes",
            "concepts": [
                {
                    "id": "elevation",
                    "title": "Elevation",
                    "description": "About elevation",
                },
                {
                    "id": "slope",
                    "title": "Slope",
                    "description": "About slope",
                },
            ],
        },
        {
            "scheme": "https://example.org/other",
            "concepts": [
                {
                    "id": "water",
                    "title": "Water",
                    "description": "About water",
                }
            ],
        },
    ]


@pytest.mark.parametrize("missing", ["term_code", "in_defined_term_set"])
def test_incomplete_terms_are_ignored(
    context: TranspilerContext, tmp_path: Path, missing: str
) -> None:
    context.metadata.keywords = _term("elevation").model_copy(update={missing: None})
    properties = _properties(context, tmp_path)
    assert properties["themes"] == []
    assert properties["keywords"] == []


def test_single_complete_term(context: TranspilerContext, tmp_path: Path) -> None:
    context.metadata.keywords = _term("elevation")
    themes = _properties(context, tmp_path)["themes"]
    assert isinstance(themes, list)
    assert [theme["scheme"] for theme in themes] == ["https://example.org/themes"]
    assert [concept["id"] for concept in themes[0]["concepts"]] == ["elevation"]


def test_help_links_skip_missing_urls(context: TranspilerContext, tmp_path: Path) -> None:
    context.metadata.software_help = [
        CreativeWork(name="Offline manual"),
        CreativeWork(url=AnyUrl("https://example.org/help")),
        CreativeWork(name="FAQ", url=AnyUrl("https://example.org/faq")),
    ]
    document = _execute(context, tmp_path / "record.json")
    links = document["links"]
    assert isinstance(links, list)
    assert [link for link in links if link["rel"] == "help"] == [
        {"rel": "help", "href": "https://example.org/help"},
        {"rel": "help", "href": "https://example.org/faq", "title": "FAQ"},
    ]


@pytest.mark.parametrize("operation", ["mkdir", "open", "serialize"])
def test_output_failures_preserve_cause_and_destination(
    context: TranspilerContext, tmp_path: Path, operation: str
) -> None:
    output = tmp_path / "record.json"
    failure = OSError("Output unavailable")
    target = (
        "cwl2ogcrecords.plugin.json.dump"
        if operation == "serialize"
        else f"pathlib.Path.{operation}"
    )
    with patch(target, side_effect=failure), pytest.raises(PluginExecutionError) as caught:
        cwl2ogcrecords.execute(context, CWL2OGCAPIRecordsOptions(output=output))
    assert caught.value.__cause__ is failure
    assert str(output.absolute()) in str(caught.value)


def test_application_and_version_metadata(context: TranspilerContext, tmp_path: Path) -> None:
    context.metadata.identifier = None
    document = _execute(context, tmp_path / "record.json")
    properties = document["properties"]
    assert isinstance(properties, dict)
    assert properties["version"] == "1.0.0"
    links = document["links"]
    assert isinstance(links, list)
    assert next(link for link in links if link["rel"] == "application") == {
        "rel": "application",
        "href": "https://example.org/workflow.cwl",
        "type": "application/cwl",
        "application:container": "Common Workflow Language",
        "application:entrypoint": "elevation",
    }
    extensions = document["stac_extensions"]
    assert isinstance(extensions, list)
    assert "https://stac-extensions.github.io/application/v0.1.0/schema.json" in extensions
    assert "https://stac-extensions.github.io/version/v1.2.0/schema.json" in extensions
    assert "conformsTo" not in document
    assert "datetime" not in properties
    assert not any(key.startswith(("sci:", "processing:")) for key in properties)


@pytest.mark.parametrize("source", ["file:///tmp/workflow.cwl", "urn:example:workflow"])
def test_local_sources_are_not_published(
    context: TranspilerContext, tmp_path: Path, source: str
) -> None:
    context = context.model_copy(update={"source": AnyUrl(source)})
    document = _execute(context, tmp_path / "record.json")
    assert source not in json.dumps(document)
    extensions = document["stac_extensions"]
    assert isinstance(extensions, list)
    assert "https://stac-extensions.github.io/application/v0.1.0/schema.json" not in extensions


def test_explicit_resource_links_override_source(
    context: TranspilerContext, tmp_path: Path
) -> None:
    output = tmp_path / "record.json"
    context = context.model_copy(update={"source": AnyUrl("file:///tmp/workflow.cwl")})
    options = CWL2OGCAPIRecordsOptions.model_validate(
        {
            "output": output,
            "application_url": "https://example.org/release.cwl",
            "repository_url": "https://example.org/repository",
            "manifest_url": "https://example.org/codemeta.json",
            "application_input_url": "https://example.org/inputs.yml",
            "version_history_url": "https://example.org/changelog",
        }
    )
    cwl2ogcrecords.execute(context, options)
    document = json.loads(output.read_text())
    links = {link["rel"]: link for link in document["links"]}
    assert links["application"]["href"] == "https://example.org/release.cwl"
    assert links["application"]["application:entrypoint"] == "elevation"
    assert links["vcs"]["href"] == "https://example.org/repository"
    assert links["manifest"]["href"] == "https://example.org/codemeta.json"
    assert links["application-input"]["href"] == "https://example.org/inputs.yml"
    assert links["version-history"]["href"] == "https://example.org/changelog"


@pytest.mark.parametrize(
    "identifier",
    [
        "10.1234/workflow.v1",
        "doi:10.1234/workflow.v1",
        "https://doi.org/10.1234/workflow.v1",
        "http://dx.doi.org/10.1234/workflow.v1",
    ],
)
def test_workflow_doi_from_metadata(
    context: TranspilerContext, tmp_path: Path, identifier: str
) -> None:
    context.metadata.identifier = identifier
    document = _execute(context, tmp_path / "record.json")
    properties = document["properties"]
    assert isinstance(properties, dict)
    assert properties["sci:doi"] == "10.1234/workflow.v1"
    links = document["links"]
    assert isinstance(links, list)
    assert {"rel": "cite-as", "href": "https://doi.org/10.1234/workflow.v1"} in links


@pytest.mark.parametrize(
    "identifier", [None, "workflow-123", "https://example.org/workflow", "10.invalid/value"]
)
def test_generic_identifiers_do_not_become_dois(
    context: TranspilerContext, tmp_path: Path, identifier: str | None
) -> None:
    context.metadata.identifier = identifier
    document = _execute(context, tmp_path / "record.json")
    properties = document["properties"]
    assert isinstance(properties, dict)
    assert not any(key.startswith("sci:") for key in properties)
    extensions = document["stac_extensions"]
    assert isinstance(extensions, list)
    assert not any("/scientific/" in extension for extension in extensions)


@pytest.mark.parametrize("identifier", ["10.1234/old-workflow", "10.5678/paper", None])
@pytest.mark.parametrize("citation", [None, "Lovelace (2026). Elevation workflow, version 1.0.0."])
def test_workflow_citation_and_papers_remain_distinct(
    context: TranspilerContext, tmp_path: Path, identifier: str | None, citation: str | None
) -> None:
    context.metadata.identifier = identifier
    output = tmp_path / "record.json"
    options = CWL2OGCAPIRecordsOptions.model_validate(
        {
            "output": output,
            "workflow_citation": citation,
            "publication_dois": ["10.5678/paper", "https://doi.org/10.5678/paper"],
        }
    )
    cwl2ogcrecords.execute(context, options)
    document = json.loads(output.read_text())
    assert document["properties"].get("sci:doi") == identifier
    assert document["properties"].get("sci:citation") == citation
    assert document["properties"]["sci:publications"] == [
        {"doi": "10.5678/paper", "citation": None}
    ]
    expected_citation_links = [f"https://doi.org/{identifier}"] if identifier else []
    assert [
        link["href"] for link in document["links"] if link["rel"] == "cite-as"
    ] == expected_citation_links
    assert [link for link in document["links"] if link["rel"] == "related"] == [
        {"rel": "related", "href": "https://doi.org/10.5678/paper"}
    ]


def test_workflow_citation_without_doi(context: TranspilerContext, tmp_path: Path) -> None:
    context.metadata.identifier = "workflow-123"
    output = tmp_path / "record.json"
    citation = "Lovelace (2026). Elevation workflow."
    cwl2ogcrecords.execute(
        context, CWL2OGCAPIRecordsOptions(output=output, workflow_citation=citation)
    )
    document = json.loads(output.read_text())
    assert document["properties"]["sci:citation"] == citation
    assert "sci:doi" not in document["properties"]
    assert "sci:publications" not in document["properties"]
    assert not any(link["rel"] in {"cite-as", "related"} for link in document["links"])


def test_publication_doi_links_are_url_encoded(context: TranspilerContext, tmp_path: Path) -> None:
    context.metadata.identifier = None
    output = tmp_path / "record.json"
    cwl2ogcrecords.execute(
        context,
        CWL2OGCAPIRecordsOptions(output=output, publication_dois=["10.5678/paper#section"]),
    )
    document = json.loads(output.read_text())
    assert document["properties"]["sci:publications"] == [
        {"doi": "10.5678/paper#section", "citation": None}
    ]
    assert [link for link in document["links"] if link["rel"] == "related"] == [
        {"rel": "related", "href": "https://doi.org/10.5678/paper%23section"}
    ]


@pytest.mark.parametrize(
    "options",
    [
        {"workflow_doi": "not-a-doi"},
        {"workflow_doi": "https://example.org/10.1234/workflow"},
        {"workflow_doi": "https://doi.org/10.1234/workflow?download=1"},
        {"publication_dois": ["10.1234/white space"]},
        {"application_url": "file:///tmp/workflow.cwl"},
        {"workflow_citation": " "},
        {"application_entrypoint": " "},
    ],
)
def test_invalid_enrichment_options(options: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CWL2OGCAPIRecordsOptions.model_validate(options)


@pytest.mark.parametrize("missing", ["name", "description"])
def test_theme_labels_are_optional(
    context: TranspilerContext, tmp_path: Path, missing: str
) -> None:
    context.metadata.keywords = _term("elevation").model_copy(update={missing: None})
    themes = _properties(context, tmp_path)["themes"]
    assert isinstance(themes, list)
    concept = themes[0]["concepts"][0]
    assert concept["id"] == "elevation"
    assert ("title" if missing == "name" else "description") not in concept
    assert "url" not in concept  # The vocabulary URL is not the individual concept URL.


def test_empty_version_and_absent_entrypoint_are_omitted(
    context: TranspilerContext, tmp_path: Path
) -> None:
    context.metadata.software_version = " "
    context = context.model_copy(update={"process_id": None})
    document = _execute(context, tmp_path / "record.json")
    properties = document["properties"]
    assert isinstance(properties, dict)
    assert "version" not in properties
    links = document["links"]
    assert isinstance(links, list)
    application = next(link for link in links if link["rel"] == "application")
    assert "application:entrypoint" not in application
