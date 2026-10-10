<!--
Copyright 2026 Terradue

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# CWL and CLI to OGC Record crosswalk

This crosswalk describes `cwl2ogcrecords` **0.2.0**, including Application,
Version, Scientific Citation, and VCS v0.1.0 enrichment.

The host resolves the CWL document into `TranspilerContext` and
`SoftwareApplication` metadata before calling the plugin. The CWL column below
uses `s:` for `https://schema.org/`, declared in `$namespaces`. Prefix names
can differ; the expanded metadata names must match the host's model. The plugin
consumes the resolved metadata, rather than reading CWL keys directly.
CWL `label` and `doc` are not mapped directly by this plugin; provide the
corresponding software metadata.

Paths refer to serialized JSON. `[]` means an array entry, and
`links[rel=application]` means the link whose `rel` is `application`.
Namespaced keys such as `sci:doi` are literal JSON keys.

## CWL metadata and source

| CWL / source input | Resolved Python field | OGC Record output | Transformation or condition |
| --- | --- | --- | --- |
| Process fragment in `SOURCE`, such as `workflow.cwl#main` | `context.process_id` | `id`; `links[rel=application]["application:entrypoint"]` | The ID is copied when nonempty. Otherwise `id` is a generated `urn:uuid:…`; no entrypoint is emitted. |
| Positional `SOURCE` | `context.source` | `links[rel=application].href` | HTTP(S) sources only; `--application-url` overrides this value. Local paths and other schemes are not published as application links. |
| `s:name` | `metadata.name` | `properties.title` | Copied. |
| `s:description` | `metadata.description` | `properties.description` | Omitted when empty or absent. |
| `s:dateCreated` | `metadata.date_created` | `properties.created` | UTC datetime with whole-second precision. Date-only values become midnight UTC; naive datetimes are treated as UTC. |
| `s:license` | `metadata.license` | `properties.license` | A scalar or list; strings are retained, `CreativeWork` values use their identifiers. Multiple values are joined with `: `. |
| `s:softwareVersion` | `metadata.software_version` | `properties.version` | Whitespace is stripped; blank versions are omitted. |
| `s:identifier` containing a DOI | `metadata.identifier` | `properties["sci:doi"]`; `links[rel=cite-as].href` | Normalized to a bare DOI and a DOI resolver link. Generic identifiers are not mapped to these fields. |
| String `s:keywords` | `metadata.keywords` | `properties.keywords[]` | A scalar or list; string entries are copied. |
| Structured `s:keywords` (`DefinedTerm`) | `metadata.keywords` | `properties.themes[]` | Grouped by scheme; see the theme crosswalk below. |
| `s:author` | `metadata.author` | `properties.contacts[]` | One contact per person or author role; see the contact crosswalk below. |
| `s:softwareHelp.s:url` | `metadata.software_help[].url` | `links[rel=help].href` | A scalar or list of help objects; objects without a URL are skipped. |
| `s:softwareHelp.s:name` | `metadata.software_help[].name` | `links[rel=help].title` | Used on the corresponding help link. |

The plugin initializes `keywords` and `themes` to empty lists when no entries
qualify. It expects usable creation-date, license, author, and software-help
metadata; see [input boundaries](plugin.md#current-boundaries).

### Contacts

For a `Person`, the paths below are relative to `s:author`. For an `AuthorRole`,
use the nested person in `s:author.s:author` and the role's `s:roleName`.

| CWL metadata within the person or role | OGC Record contact field | Transformation |
| --- | --- | --- |
| Person `s:identifier` | `properties.contacts[].identifier` | Converted to a string. |
| Person `s:familyName`, `s:givenName` | `properties.contacts[].name` | Formatted as `familyName, givenName`. |
| Person `s:affiliation.s:name` | `properties.contacts[].organization` | Uses the first affiliation when a list is supplied. |
| Person `s:email` | `properties.contacts[].emails[].value` | One email entry per value. |
| Role `s:roleName` | `properties.contacts[].position` | Copied for an `AuthorRole`; plain people receive `N/A`. This does not populate contact `roles`. |

### Themes

These paths are relative to each `DefinedTerm` in `s:keywords`.

| CWL metadata | OGC Record theme field | Transformation |
| --- | --- | --- |
| `s:inDefinedTermSet` | `properties.themes[].scheme` | Scheme URL used to group terms. |
| `s:termCode` | `properties.themes[].concepts[].id` | Both scheme and term code must be nonempty to include the term. |
| `s:name` | `properties.themes[].concepts[].title` | Included when nonempty. |
| `s:description` | `properties.themes[].concepts[].description` | Included when nonempty. |

The scheme URI is not emitted as an individual concept URL.

## CLI and Python options

All enrichment options below are available in **0.2.0**. Optional scalar
settings default to `None`; `publication_dois` defaults to an empty list.
CLI names use hyphens, while Python option names use underscores.

| CLI option | Python option | OGC Record output or effect |
| --- | --- | --- |
| `--output` | `output` | Destination file, default `ogc-record.json`. Creates parent directories and overwrites the file. Does not set a record field or self link. |
| `--application-url` | `application_url` | HTTP(S) override for `links[rel=application].href`, including when `SOURCE` is local. |
| `--repository-url` | `repository_url` | `links[rel=vcs].href`, plus inferred VCS fields on that link and in `properties`. Accepts one string; see below. |
| `--manifest-url` | `manifest_url` | HTTP(S) `links[rel=manifest].href`. |
| `--application-input-url` | `application_input_url` | HTTP(S) `links[rel=application-input].href`. This links to example parameters; it does not copy their contents. |
| `--version-history-url` | `version_history_url` | HTTP(S) `links[rel=version-history].href`; declares the Version extension even when software version is blank. |
| `--workflow-citation` | `workflow_citation` | `properties["sci:citation"]`; whitespace is trimmed and blank values are rejected. Describes the workflow itself. |
| `--publication-dois` (repeatable) | `publication_dois` | `properties["sci:publications"][]` entries with `doi` and `citation: null`, plus `related` DOI links. Normalized duplicates are removed. |

DOIs accept bare names, `doi:` identifiers, and HTTP(S) `doi.org` or
`dx.doi.org` resolver URLs. Only the workflow DOI produces `cite-as`;
publication DOIs produce `related` links. DOI validation checks syntax, not
registration. There are no `workflow_doi`, `application_entrypoint`, or
`project_id` options.

### VCS inference from one repository URL

Each recognized Git repository produces `vcs:type="git"`. The following
additional fields are written to **both** `links[rel=vcs]` and `properties`.
The supplied URL is retained as the link target after trimming whitespace.

| URL form | Inferred field | Example |
| --- | --- | --- |
| Clone URL or repository landing page | No reference field | `git@github.com:team/workflow.git` |
| GitHub `/tree/…` or GitLab `/-/tree/…` | `vcs:branch` | `/tree/main` → `main` |
| GitHub `/blob/…` or GitLab `/-/blob/…` | `vcs:branch` from the first ref segment | `/blob/main/workflow.cwl` → `main` |
| GitHub `/releases/tag/…`; GitLab `/-/tags/…` or `/-/releases/…` | `vcs:tag` | `/releases/tag/v1.2.0` → `v1.2.0` |
| Explicit `refs/tags/…` tree reference | `vcs:tag` | `/tree/refs/tags/v1.2.0` → `v1.2.0` |
| GitHub `/commit/…` or GitLab `/-/commit/…` | `vcs:revision` | `/commit/abc1234` → `abc1234` |
| Full 40- or 64-character hexadecimal tree/blob ref | `vcs:revision` | Full commit hash retained unchanged. |

Inference is offline. Plain clone URLs cannot supply a default branch or current
revision, and ordinary tree/blob refs are treated as branches unless they have
an explicit tag form or full hash. Tree URLs must not include a subdirectory;
encode slashes within blob ref names as `%2F`. See
[VCS metadata](plugin.md#repository-and-vcs-metadata) for validation rules and
supported forms. Unrecognized but valid HTTP(S) landing pages produce only the
plain `vcs` link.

## Generated values and extension declarations

| Output | Source or condition |
| --- | --- |
| `type` | Always `Feature`. |
| `geometry` | Always `null`. |
| `properties.updated` | Conversion time, serialized in UTC. |
| `properties.language` | Fixed `{"code": "en-US", "name": "English (United States)"}`. |
| `properties.resourceLanguages` | A list containing that same language object. |
| `links[rel=application].type` | `application/cwl`, for both YAML and JSON CWL. |
| `links[rel=application]["application:container"]` | `Common Workflow Language`; describes the document format, not a Docker container. |
| `stac_extensions` — Application | Declared when an application link is emitted. |
| `stac_extensions` — Version | Declared for a nonblank software version or an explicit version-history URL. |
| `stac_extensions` — Scientific | Declared for a workflow DOI, citation, or publication metadata. |
| `stac_extensions` — VCS v0.1.0 | Declared when Git metadata is inferred from `repository_url`. |

These extension declarations do not populate OGC `conformsTo`. The converter
does not derive geometry, temporal extent, processing provenance, output
datasets, checksums, or Docker image versions from CWL inputs, outputs,
requirements, or workflow steps. It emits no STAC `datetime` or `stac_version`
and performs no complete output-schema validation before writing.

## Example CLI mapping

```bash
transpiler-mate cwl2ogcrecords \
  --output build/record.json \
  --application-url https://example.org/workflow.cwl \
  --repository-url https://github.com/team/workflow/releases/tag/v1.2.0 \
  --workflow-citation 'Example Team (2026). Example Workflow.' \
  --publication-dois 10.5678/example-paper \
  'workflow.cwl#main'
```

With the host-resolved process ID `main`, this sets the record ID and application
entrypoint to `main`. The application link uses the explicit public URL, the
repository link and record properties carry `vcs:type="git"` and
`vcs:tag="v1.2.0"`, and the citation and related paper populate the Scientific
fields. The software version still comes from `s:softwareVersion`; it is not
inferred from the repository tag. The DOI and URLs here are illustrative.
