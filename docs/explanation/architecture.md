<!--
Copyright 2026 Transpiler-Mate

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

# Architecture

## Conversion flow

The Transpiler-Mate host resolves the CWL source and provides software metadata
in a `TranspilerContext`. The plugin maps that metadata to an `OGCRecord`, then
serializes a single GeoJSON Feature to the configured output path. It does not
serve an OGC API endpoint or publish the record to a catalog.

`plugin.py` owns the metadata mapping, defaults, and file output. `ogc_record.py`
owns the record representation, typed metadata dictionaries, and PySTAC adapter.
The [plugin reference](../reference/plugin.md) describes conversion-specific
assumptions; these are separate from the more permissive Python record model.

## Why reuse PySTAC?

`OGCRecord` subclasses `pystac.Item` to reuse links, assets, and Item-oriented
extension APIs. Its default serialization is an OGC Record Feature. It initializes
`STACObject` directly to avoid requiring a STAC datetime for every record.
This dependency on PySTAC internals requires review when upgrading PySTAC.

OGC temporal extent and STAC datetime fields remain independent. Explicit
`to_stac_item()` export requires a real datetime or start/end interval; it does
not invent dates. See [record behavior](../reference/ogc_record.md).

## Why typed dictionaries?

The record keeps metadata in a live properties dictionary. Typed dictionaries
provide named structures without changing JSON serialization or introducing
conversion wrappers. Shared structures are reused, including contact link
fields and required identifier values. Union aliases express the schema's
name-or-media-type and name-or-organization alternatives.

Static typing and schema validation remain separate. The package preserves
unknown metadata and exposes an explicit validator hook; it does not claim
that every constructed dictionary satisfies the complete OGC schema.
