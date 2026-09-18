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

# CWL to OGC API - Records

`cwl2ogcrecords` is a Transpiler-Mate plugin that turns resolved CWL software
metadata into an OGC API - Records GeoJSON Feature. It also provides an
`OGCRecord` Python model with PySTAC link, asset, and extension support.

## Get started

Install the plugin in the same environment as the Transpiler-Mate CLI:

```bash
python -m pip install cwl2ogcrecords
transpiler-mate cwl2ogcrecords --help
transpiler-mate cwl2ogcrecords --output build/record.json workflow.cwl
```

The conversion command expects a CWL source with software metadata. See the
[plugin reference](reference/plugin.md) for the fields consumed and current
input assumptions. The default output is `ogc-record.json`.

- [First steps](tutorials/first-steps.md): create and save a record in Python.
- [Install](how-to/install.md): prepare a CLI or development environment.
- [Use the CLI](how-to/use-cli.md): convert a CWL source to a JSON file.
- [Typed metadata](reference/metadata.md): construct languages, themes, formats,
  external identifiers, and contacts.
- [Record behavior](reference/ogc_record.md): serialization, extensions, and validation.
- [Architecture](explanation/architecture.md): understand the conversion boundaries.
