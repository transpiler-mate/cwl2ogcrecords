# Proposal

## Why

The repository has working record mappings but no OpenSpec capability baseline. Capturing the existing keyword and theme mapping provides a small, test-backed contract for reviewing future changes without changing runtime behavior.

## What Changes

- Document the previously recommended first capability: resolved software keywords to serialized OGC Record keywords and themes.
- Specify empty results, scalar and list inputs, scheme grouping and ordering, incomplete terms, optional concept labels, and omission of concept URLs.
- Link requirements and concrete scenarios to current implementation and tests.
- Preserve existing behavior, including empty arrays; identify unresolved conformance and coverage questions without deciding them.
- Create only the requested proposal and delta specification for review. No implementation, test, dependency, general documentation, or main-spec edits are included.

## Capabilities

### New Capabilities

- `keyword-theme-mapping`: Baseline the existing mapping from resolved `SoftwareApplication.keywords` to record `properties.keywords` and `properties.themes`. This capability is new to OpenSpec, not new runtime functionality.

### Modified Capabilities

None. There are no existing OpenSpec specifications.

## Impact

The behavior being documented resides in `src/cwl2ogcrecords/plugin.py`, specifically `_add_kw_themes` and `_theme_concept`. Evidence comes from `tests/test_plugin.py`: `test_plain_keywords`, `test_groups_terms_by_scheme`, `test_incomplete_terms_are_ignored`, `test_single_complete_term`, and `test_theme_labels_are_optional`. The metadata mapping section of `docs/reference/plugin.md` agrees with this baseline.

The contract starts with resolved metadata supplied by `transpiler-mate-api` and describes serialized fields when conversion succeeds. It does not specify CWL parsing, namespace expansion, host validation, source retrieval, other record mappings, or complete OGC/STAC schema conformance. Existing tests use constructed contexts and mocked source responses; they do not establish end-to-end CWL behavior.

## Unresolved Questions

- Should a future conformance change omit empty `themes` rather than serialize `[]`? The current tests require `[]`; this proposal preserves it and makes no schema-conformance claim.
- Should URL-valued keywords, duplicates, whitespace-only strings, empty strings inside lists, and equivalent scheme URL spellings receive dedicated characterization scenarios? The current implementation has observable behavior for these cases, but the selected tests do not directly establish those contracts; this baseline does not add normalization, filtering, or deduplication rules.
- Does the host consistently resolve real CWL metadata into the inputs described here? That integration question remains outside this plugin-level baseline.

These questions do not block documenting the selected existing scenarios. Resolving them must not silently broaden this change or introduce new behavior.

## Evidence and Review Boundaries

The requirements above baseline current output behavior. They do not require changes to implementation or tests. References below are supporting evidence, not constraints on internal implementation.

| Requirement | Implementation evidence | Existing test evidence in `tests/test_plugin.py` |
| --- | --- | --- |
| Empty arrays | `src/cwl2ogcrecords/plugin.py`, `_add_kw_themes` | `test_plain_keywords`, `test_incomplete_terms_are_ignored` |
| Text retention | `_add_kw_themes` | `test_plain_keywords`, `test_groups_terms_by_scheme` |
| Grouping and ordering | `_add_kw_themes` | `test_groups_terms_by_scheme`, `test_single_complete_term` |
| Incomplete terms | `_add_kw_themes` | `test_incomplete_terms_are_ignored` |
| Optional labels | `_theme_concept` | `test_groups_terms_by_scheme`, `test_theme_labels_are_optional` |
| No concept URL | `_theme_concept` | `test_groups_terms_by_scheme`, `test_theme_labels_are_optional` |

Source files: [implementation](../../../src/cwl2ogcrecords/plugin.py), [tests](../../../tests/test_plugin.py), and [documented mapping](../../../docs/reference/plugin.md#metadata-mapping).

The existing tests exercise conversion through the public plugin with constructed metadata and mocked source retrieval. The scalar-term and missing-label scenarios combine directly tested assertions with the same mapping logic; the tests do not separately assert every retained field in every scenario. Falsey checks for codes, schemes, and labels are visible in the implementation; current dedicated tests exercise `None`, rather than every possible falsey representation.

This baseline assumes an otherwise usable resolved context and successful conversion. It does not promise recovery from invalid host metadata or retrieval failures. It does not establish raw CWL parsing behavior, API-model validation rules, or complete OGC/STAC schema validity.
