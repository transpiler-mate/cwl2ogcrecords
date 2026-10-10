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

# Architecture

## Conversion flow

The Transpiler-Mate host resolves the CWL source and provides software metadata
in a `TranspilerContext`. The plugin maps that metadata to an OGC API - Records
GeoJSON Feature and writes it to the configured output path. It does not serve
an OGC API endpoint or publish the record to a catalog.

`plugin.py` owns metadata mapping, plugin options, enrichment, and file output.
Record serialization and metadata structures come from the external
`pystac-ext-ogc-record` dependency. This package no longer embeds its own
record implementation.

The [plugin reference](../reference/plugin.md) documents conversion assumptions
and the fields consumed from the resolved context.

## Workflow enrichment

!!! warning "Available since 0.2.0"

    Application links, version metadata, scientific citations, and related
    publication DOIs are available in `cwl2ogcrecords` 0.2.0 and later.

Application links point to an HTTP(S) CWL source or an explicitly supplied
public URL. The process ID identifies the entrypoint. Repository, manifest,
example inputs, and version-history URLs are included only when supplied.

Version metadata comes from the software version. Scientific metadata separates
the workflow's DOI and recommended citation from papers describing it. The
workflow DOI receives a `cite-as` link; paper DOIs receive `related` links.
Normalized duplicate paper DOIs are removed before serialization.

The plugin uses PySTAC's Scientific and Version accessors. It writes publication
entries separately because PySTAC's publications setter would also add
`cite-as` links for papers. Application link fields are populated directly.
Extension identifiers appear in `stac_extensions` only when relevant metadata
is emitted; they are not OGC `conformsTo` declarations.

## Output boundaries

The record describes a reusable workflow definition. The plugin does not infer
execution provenance, processing timestamps, output datasets, or Docker image
versions. Geometry remains null, and no STAC version or datetime is invented.

Plugin options are validated before conversion. The serialized record is not
validated against the complete OGC or extension schemas; downstream consumers
must perform any schema validation they require. File-writing failures are
wrapped in `PluginExecutionError`, while earlier conversion errors propagate.
