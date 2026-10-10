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
| `context.process_id` | `id`; otherwise a generated `urn:uuid:…` |
| `date_created` | `properties.created` as an ISO datetime string |
| Conversion time | `properties.updated` |
| `name` | `properties.title` |
| Truthy `description` | `properties.description`; otherwise omitted |
| Fixed English language | `language` and `resourceLanguages`, using `en-US` and `English (United States)` |
| `license` | String values or `CreativeWork.identifier`, joined with `: ` |
| `author` | `contacts`, one entry per `Person` or `AuthorRole` |
| String `keywords` | `keywords` |
| `DefinedTerm` keywords with a scheme and code | `themes`, grouped by `in_defined_term_set` |
| `software_help` entries with a URL | Links with `rel="help"` and the entry's name as title |

Dates become datetime strings; date-only values become midnight UTC, naive
datetimes are labeled UTC, and aware datetimes retain their offset. The plugin
currently obtains its update time with `datetime.now()` before applying this
conversion.

A theme concept uses `term_code` as `id`, with optional `name` as `title` and
optional `description`. A defined term is included when its scheme and code
are truthy. The scheme URI is not reused as a concept URL. The plugin initializes `keywords`
and `themes` to empty lists even when no entries qualify.

Contacts use the author's identifier, `family_name, given_name`, first
affiliation's name, and email address(es). `AuthorRole.role_name` becomes
`position`; a plain `Person` gets `position="N/A"`. The role is not copied into
contact `roles`.

## Current boundaries

The plugin expects a usable creation date, authors with at least one affiliation
and email information, license information, and software-help objects. It does
not supply fallbacks for all missing metadata. A help object without a URL is
skipped; a missing help object is not handled equivalently.

The plugin leaves geometry null and does not populate resource type, formats,
external identifiers, temporal extent, or conformance declarations. Those can
be supplied when using `OGCRecord` directly. No schema validation is performed
before writing. In particular, an empty `themes` list may need to be omitted
before validating against the OGC schema's minimum length constraint.

Output is indented JSON without a self link. File-writing failures are wrapped
in `PluginExecutionError`; earlier conversion errors are outside that wrapper.


## Workflow metadata enrichment

The plugin describes a reusable workflow definition. It does not infer execution
provenance, processing timestamps, output datasets, or Docker image versions.

| Source | Output |
| --- | --- |
| HTTP(S) `context.source`, or `application_url` override | `application` link with media type `application/cwl` and `application:container="Common Workflow Language"` |
| `application_entrypoint`, otherwise `context.process_id` | `application:entrypoint` on that link, when nonempty |
| Nonempty `metadata.software_version` | `properties.version` through PySTAC's Version extension |
| DOI-valued `metadata.identifier`, or `workflow_doi` override | `properties["sci:doi"]` and a `cite-as` DOI resolver link |
| `workflow_citation` | `properties["sci:citation"]`, for the workflow itself |
| `publication_dois` | `properties["sci:publications"]` and `related` links for papers describing the workflow |

No URL is guessed from a repository or release tag. Local `file:` sources and
other non-HTTP(S) sources are not emitted as application links; provide
`application_url` to publish a downloadable CWL. The generic `application/cwl`
media type supports YAML and JSON without guessing the encoding from a URL.
Entrypoints must identify the process in the linked document; supply an override
if a published package uses a different entrypoint. The application container
field describes CWL's document format, not a Docker container.

Additional optional plugin settings:

| Option | Default | Meaning |
| --- | --- | --- |
| `application_url` | `None` | Public HTTP(S) CWL URL overriding the context source |
| `application_entrypoint` | `None` | Nonblank entrypoint overriding the context process ID |
| `repository_url` | `None` | HTTP(S) source repository, linked with `vcs` |
| `manifest_url` | `None` | HTTP(S) CodeMeta/dependency manifest, linked with `manifest` |
| `application_input_url` | `None` | HTTP(S) example parameter file, linked with `application-input` |
| `version_history_url` | `None` | HTTP(S) release history, linked with `version-history` |
| `workflow_doi` | `None` | DOI of this workflow release, overriding its metadata identifier |
| `workflow_citation` | `None` | Nonblank recommended human-readable workflow citation |
| `publication_dois` | `[]` | DOI list for related scientific papers; normalized duplicates are removed |

DOIs accept bare names, `doi:` identifiers, and HTTP(S) `doi.org` or
`dx.doi.org` resolver URLs. Serialized DOI properties contain bare names.
Explicit malformed DOI options raise a Pydantic validation error; generic
metadata identifiers that are not DOIs are simply not used for `sci:doi`.
Validation checks syntax, not whether a DOI is registered. Resolver URLs with
query strings or fragments are rejected. Supply the bare DOI if necessary.
A related paper's DOI is never promoted to the workflow DOI. The current
SoftwareApplication API has no typed citation field, so this increment uses
explicit options instead of interpreting arbitrary extra fields as citations.

Example using the plugin API with an existing resolved context:

```python
from cwl2ogcrecords.plugin import CWL2OGCAPIRecordsOptions, cwl2ogcrecords

options = CWL2OGCAPIRecordsOptions.model_validate({
    "output": "workflow-record.json",
    "application_url": "https://example.org/releases/1.2.0/workflow.cwl",
    "application_entrypoint": "main",
    "repository_url": "https://github.com/example/workflow",
    "manifest_url": "https://example.org/releases/1.2.0/codemeta.json",
    "version_history_url": "https://example.org/changelog",
    "workflow_doi": "10.1234/example-workflow",
    "workflow_citation": "Example Team (2026). Example Workflow, version 1.2.0.",
    "publication_dois": ["10.5678/example-paper"],
})
cwl2ogcrecords.execute(context, options)
```

The example DOI values are illustrative. Use identifiers registered for your
actual workflow and papers.

### Extension and validation boundaries

The plugin uses the installed PySTAC Scientific and Version accessors. Application
v0.1.0 is a proposal; its Link fields are populated directly because the current
project dependency has no Application accessor. This requires no new extension
implementation to use the patch.

Extension identifiers are added to the foreign `stac_extensions` member only
when the corresponding extension content is emitted. Application is declared
when an application link carries its namespaced fields; standalone `vcs` or
`manifest` relation links do not require an extension declaration. Version is
also declared when a version-history link is explicitly supplied. Scientific
is declared only when DOI, citation, or publication metadata is present.

These declarations are not OGC `conformsTo` claims. The result remains an OGC
Record with null geometry and without an invented STAC version or datetime.
Serialization tests do not imply full STAC Item or OGC schema conformance;
validate the Record and applicable extension constraints with a configured
validator, as described in [the adapter reference](ogc_record.md).

OSC project associations and File Info checksums are not part of this increment.
They need explicit project context or access to the exact distributed package.

Specifications:

- [Application](https://github.com/stac-extensions/application)
- [Versioning Indicators](https://github.com/stac-extensions/version)
- [Scientific Citation](https://github.com/stac-extensions/scientific)
