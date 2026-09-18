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
| Complete `DefinedTerm` keywords | `themes`, grouped by `in_defined_term_set` |
| `software_help` entries with a URL | Links with `rel="help"` and the entry's name as title |

Dates become datetime strings; date-only values become midnight UTC, naive
datetimes are labeled UTC, and aware datetimes retain their offset. The plugin
currently obtains its update time with `datetime.now()` before applying this
conversion.

A theme concept uses `term_code` as `id`, `name` as `title`, `description`, and
the term-set URI as `url`. A defined term is included only when its scheme,
code, name, and description are all truthy. The plugin initializes `keywords`
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
