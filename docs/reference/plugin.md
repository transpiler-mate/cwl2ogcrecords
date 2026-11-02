# Plugin reference

The `transpiler_mate.plugins` entry-point group registers `cwl2ogcrecords` as
`cwl2ogcrecords.plugin:cwl2ogcrecords`. The host supplies a `TranspilerContext`;
the plugin returns `None` and writes a JSON file.

## Options

| Option | Python type | Default | Behavior |
| --- | --- | --- | --- |
| `output` / `--output` | `pathlib.Path` | `ogc-record.json` | Destination JSON file; parent directories are created and existing files are overwritten. |

`CWL2OGCAPIRecordsOptions` rejects unknown options. There is no `project_id`
option in the current implementation.

## Metadata mapping

| Context or software metadata | Record output |
| --- | --- |
| `application_url` | Optional second `application` link with media type `application/json` and `application:container="HTTP"` |
| `context.process_id` | `id`; otherwise a generated `urn:uuid:…` |
| `date_created` | `properties.created` as an ISO datetime string |
| Conversion time | `properties.updated` |
| `name` | `properties.title` |
| Truthy `description` | `properties.description`; otherwise omitted |
| Fixed English language | `language` and `resourceLanguages`, using `en-US` and `English (United States)` |
| `license` | String values or `CreativeWork.identifier`, joined with `: ` |
| `author`, `contributor`, `publisher` | `contacts`, with resource responsibilities in `roles` |
| String `keywords` | `keywords` |
| `DefinedTerm` keywords with a scheme and code | `themes`, grouped by `in_defined_term_set` |
| `software_help` entries with a URL | Links with `rel="help"` and the entry's name as title |

Dates are serialized as UTC datetime strings with whole-second precision.
Date-only values become midnight UTC, naive datetimes are treated as UTC,
and aware datetimes are converted to UTC. The update time is the current UTC time.

!!! warning "Available since 0.2.0"

    Theme concepts no longer require a name or description, and a vocabulary's
    scheme URI is no longer emitted as the individual concept URL.

A theme concept uses `term_code` as `id`, with optional `name` as `title` and
optional `description`. A defined term is included when its scheme and code
are truthy. The scheme URI is not reused as a concept URL. The plugin initializes `keywords`
and `themes` to empty lists even when no entries qualify.

Contacts are emitted in author, contributor, then publisher order. People use
`family_name, given_name`, their first affiliation when available, identifier,
and email address(es). The publisher uses its organization name and any supplied
identifier or email addresses. Missing identifiers and emails are omitted.

Each contact receives the source responsibility (`author`, `contributor`, or
`publisher`) in `roles`. `AuthorRole.role_name` and `ContributorRole.role_name`
add explicit responsibilities, including `maintainer`. Common role names are
trimmed and normalized to lowercase; other nonblank labels are preserved after
trimming. Duplicate role values within a contact are omitted. Contacts from
separate source entries remain separate.

Resource responsibilities never populate `position`. The current input model
has no organizational-position field, so `position` is omitted rather than
inferred or filled with `N/A`.

## Current boundaries

The plugin expects a usable creation date, authors with valid person
and email information, license information, and software-help objects. It does
not supply fallbacks for all missing metadata. A help object without a URL is
skipped; a missing help object is not handled equivalently.

The plugin leaves geometry null and does not populate resource type, formats,
external identifiers, temporal extent, or conformance declarations. Those can
be added by downstream consumers. No schema validation is performed before
writing. In particular, an empty `themes` list may need to be omitted
before validating against the OGC schema's minimum length constraint.

Output is indented JSON without a self link. File-writing failures are wrapped
in `PluginExecutionError`; earlier conversion errors are outside that wrapper.


## Workflow metadata enrichment

!!! warning "Available since 0.2.0"

    The automatic mappings and enrichment options in this section require
    `cwl2ogcrecords` 0.2.0 or later.

The plugin describes a reusable workflow definition. It does not infer execution
provenance, processing timestamps, output datasets, or Docker image versions.

| Source | Output |
| --- | --- |
| `context.source` | `application` link with media type `application/cwl` and `application:container="Common Workflow Language"` |
| `application_url` | Optional second `application` link with media type `application/json` and `application:container="HTTP"` |
| `context.process_id` | `application:entrypoint` on that link, when nonempty |
| Nonempty `metadata.software_version` | `properties.version` through PySTAC's Version extension |
| DOI-valued `metadata.identifier` | `properties["sci:doi"]` and a `cite-as` DOI resolver link |
| `workflow_citation` | `properties["sci:citation"]`, for the workflow itself |
| `publication_dois` | `properties["sci:publications"]` and `related` links for papers describing the workflow |

No URL is guessed from a repository or release tag. The context source
always supplies the CWL application link, without filtering its scheme. Set
`application_url` to add a separate HTTP(S) execution link with media type
`application/json` and `application:container="HTTP"`. It identifies the endpoint
that executes the CWL; the plugin records the URL without invoking it. When the
option is omitted or `None`, no execution link is added. Consumers should select
application links by both `rel` and `type`, rather than assuming `rel` is unique.

The generic `application/cwl` media type supports YAML and JSON without guessing the encoding from a URL.
The context process ID must identify the process in the linked document; no
entrypoint override option is provided. The CWL source link's container
field describes CWL's document format, not a Docker container.

The CWL source link also includes `file:size` and a SHA-256 multihash in
`file:checksum`. The plugin fetches the source a second time through the runtime
resolver's private `_session`, reusing its authentication and transport adapters.
It streams the response with a 30-second request timeout and leaves the shared
session open. Retrieval failures or a resolver without `_session` raise
`PluginExecutionError`. These fields describe the second response, which may
differ from the originally parsed input if the source changed. No
`file:local_path` is inferred. File metadata and `published` describe only
`context.source`. The JSON execution link does not receive CWL source metadata.

When the response supplies a valid `Last-Modified` header, the plugin uses it
as a fallback for record `published` through the Timestamps extension, normalized
to UTC. This is a source-modification approximation, not a verified first
publication time for the metadata record. Missing or invalid headers leave
`published` and the Timestamps extension absent; the `Date` header is not used.

Additional optional plugin settings:

| Option | Default | Meaning |
| --- | --- | --- |
| `application_url` | `None` | HTTP(S) execution URL; adds a separate `application` link with media type `application/json` and container `HTTP` |
| `repository_url` | `None` | Repository URL or Git remote string; adds a `vcs` link and VCS v0.1.0 metadata |
| `manifest_url` | `None` | HTTP(S) CodeMeta/dependency manifest, linked with `manifest` |
| `application_input_url` | `None` | HTTP(S) example parameter file, linked with `application-input` |
| `version_history_url` | `None` | HTTP(S) release history, linked with `version-history` |
| `workflow_citation` | `None` | Nonblank recommended human-readable workflow citation |
| `publication_dois` | `[]` | DOI list for related scientific papers; normalized duplicates are removed |

DOIs accept bare names, `doi:` identifiers, and HTTP(S) `doi.org` or
`dx.doi.org` resolver URLs. Serialized DOI properties contain bare names.
Malformed publication DOI options raise a Pydantic validation error; generic
metadata identifiers that are not DOIs are simply not used for `sci:doi`.
Validation checks syntax, not whether a DOI is registered. Resolver URLs with
query strings or fragments are rejected. Supply the bare DOI if necessary.
A related paper's DOI is never promoted to the workflow DOI. Only the workflow
gets a `cite-as` link; papers get `related` links. Normalized duplicate paper
DOIs produce one publication entry and one related link. DOI resolver links
are URL-encoded. Publication entries currently include `citation: null` because
no paper-specific citation text is supplied.

Supply the workflow DOI through `context.metadata.identifier` and the entrypoint
through `context.process_id`; `workflow_doi` and `application_entrypoint` are not
supported options. Workflow citation text comes from `workflow_citation`.

Example using the plugin API with an existing resolved context:

```python
from cwl2ogcrecords.plugin import CWL2OGCAPIRecordsOptions, cwl2ogcrecords

context.metadata.identifier = "10.1234/example-workflow"
options = CWL2OGCAPIRecordsOptions.model_validate({
    "output": "workflow-record.json",
    "application_url": "https://example.org/processes/workflow/execution",
    "repository_url": "https://github.com/example/workflow",
    "manifest_url": "https://example.org/releases/1.2.0/codemeta.json",
    "application_input_url": "https://example.org/releases/1.2.0/inputs.yml",
    "version_history_url": "https://example.org/changelog",
    "workflow_citation": "Example Team (2026). Example Workflow, version 1.2.0.",
    "publication_dois": ["10.5678/example-paper"],
})
cwl2ogcrecords.execute(context, options)
```

The example DOI values are illustrative. Use identifiers registered for your
actual workflow and papers.

### Extension and validation boundaries

The plugin uses the installed PySTAC Scientific and Version accessors. Application
v0.1.0 link fields are populated directly; record serialization is provided by
the `pystac-ext-ogc-record` dependency.

Extension identifiers are added to the foreign `stac_extensions` member only
when the corresponding extension content is emitted. Application is declared
when an application link carries its namespaced fields; `manifest` relation links do not require an extension declaration. VCS is
declared when a repository link carries VCS fields. Version is
also declared when a version-history link is explicitly supplied. Scientific
is declared only when DOI, citation, or publication metadata is present.

These declarations are not OGC `conformsTo` claims. The result remains an OGC
Record with null geometry and without an invented STAC version or datetime.
Serialization tests do not imply full STAC Item or OGC schema conformance;
validate the Record and applicable extension constraints with a configured
validator appropriate to the schema dialect and external references.

OSC project associations and File Info checksums are not part of this increment.
They need explicit project context or access to the exact distributed package.

Specifications:

- [Application](https://github.com/stac-extensions/application)
- [Versioning Indicators](https://github.com/stac-extensions/version)
- [Scientific Citation](https://github.com/stac-extensions/scientific)

## Repository and VCS metadata

!!! warning "Available since 0.2.0"

    Pass a single `repository_url` string to add VCS metadata. No separate
    branch, revision, or tag options are needed.

The plugin uses `giturlparse` and `pystac-ext-vcs` to implement the tagged
[VCS v0.1.0 specification](https://github.com/stac-extensions/vcs/tree/v0.1.0).
It retains the supplied URL on one `rel="vcs"` link and adds `vcs:type="git"`
plus any inferred reference fields to both the link and record properties.
It declares `https://stac-extensions.github.io/vcs/v0.1.0/schema.json` once in
`stac_extensions`. Exact revisions use `vcs:revision`, as defined in v0.1.0.

| Example `repository_url` | Additional inferred fields |
| --- | --- |
| `https://github.com/team/workflow` | None |
| `git@github.com:team/workflow.git` | None |
| `ssh://git@gitlab.com/team/workflow.git` | None |
| `https://github.com/team/workflow/tree/main` | `vcs:branch="main"` |
| `https://gitlab.com/team/workflow/-/tree/feature/topic` | `vcs:branch="feature/topic"` |
| `https://github.com/team/workflow/blob/main/workflow.cwl` | `vcs:branch="main"` |
| `https://github.com/team/workflow/releases/tag/v1.2.0` | `vcs:tag="v1.2.0"` |
| `https://gitlab.com/team/workflow/-/tags/v1.2.0` | `vcs:tag="v1.2.0"` |
| `https://github.com/team/workflow/commit/abc1234` | `vcs:revision="abc1234"` |

GitLab `/-/releases/` and `/-/commit/` URLs also work, including self-hosted
GitLab and nested groups. Tree/blob references containing a full 40- or
64-character hexadecimal hash produce `vcs:revision`. Explicit `refs/tags/`
tree references produce `vcs:tag`; `refs/heads/` is removed from branch names.

Parsing is offline: it does not clone repositories, resolve default branches,
verify refs, or derive tags from the workflow software version. An ordinary
tree/blob ref is treated as a branch; the URL alone cannot distinguish a branch
from a tag with the same name. Use a release/tag URL or explicit `refs/tags/`
tree URL to identify a tag. Tree URLs must point to the ref itself, without a
subdirectory. Blob URLs use the first segment after `blob` as the ref;
percent-encode slashes within ref names, for example `feature%2Ftopic`.

Leading and trailing whitespace is stripped. Local paths, malformed remotes,
embedded HTTP credentials, query strings, and fragments are rejected during
option validation. Existing public HTTP(S) landing-page URLs remain accepted;
if `giturlparse` cannot identify a repository, only the plain link is emitted.
Omitting `repository_url` emits no VCS link, properties, or schema declaration.
