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

# Create your first record

This tutorial converts a CWL workflow through Transpiler-Mate and inspects the
resulting OGC API - Records GeoJSON file.

## Prepare the workflow

[Install the plugin](../how-to/install.md) in the same environment as the
Transpiler-Mate CLI. Use an existing CWL source with software metadata, named
`workflow.cwl` in the commands below. Review the
[metadata mapping and input assumptions](../reference/plugin.md#metadata-mapping),
including creation date, license, author affiliations and email addresses, and
software-help objects.

## Convert the source

```bash
transpiler-mate cwl2ogcrecords --output build/record.json workflow.cwl
```

The plugin creates the output directory if necessary and writes one record.
Running the command again overwrites the file.

## Inspect the result

```bash
python -m json.tool build/record.json
```

The JSON has top-level `type: "Feature"`, an identifier, `geometry: null`,
`properties`, and `links`. The title, description, dates, contacts, keywords,
and themes come from the resolved software metadata. No self link is emitted.

!!! warning "Available since 0.2.0"

    Version 0.2.0 adds workflow application links, software versions, scientific
    citations, and related publication DOIs. Earlier versions do not provide
    these enrichment features.

With version 0.2.0 or later, nonblank software version metadata becomes
`properties.version`. A DOI-valued software identifier becomes `sci:doi` with a
`cite-as` link. An HTTP(S) source produces an `application` link; a local source
needs an explicit public `application_url` to produce that link.

The [enrichment example](../reference/plugin.md#workflow-metadata-enrichment)
shows how to supply public resource URLs, workflow citation text, and related
publication DOIs through the plugin's Python options.

## Next steps

See the [CLI guide](../how-to/use-cli.md) for source conversion and the
[plugin reference](../reference/plugin.md) for all supported settings.
