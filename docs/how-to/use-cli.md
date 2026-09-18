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

# Convert a CWL source

Install the plugin in your Transpiler-Mate environment as described in
[Install](install.md). Check the command options:

```bash
transpiler-mate cwl2ogcrecords --help
```

## Write a record

```bash
transpiler-mate cwl2ogcrecords --output build/record.json workflow.cwl
```

`SOURCE` is the positional CWL source handled by Transpiler-Mate. The plugin
receives the resolved context and software metadata. It writes one JSON Feature,
creates missing parent directories, and overwrites the selected file if it
already exists. Without `--output`, the destination is `ogc-record.json` in the
current directory.

Inspect the result:

```bash
python -m json.tool build/record.json
```

The result contains `id`, `type`, `geometry`, `properties`, and `links`. Metadata
such as title, language, themes, and contacts appears inside `properties`.
The plugin excludes self links when writing the file.

## Prepare metadata

Review the [mapping and input assumptions](../reference/plugin.md) before
conversion. In particular, the current implementation expects creation date,
author contact details and affiliations, license information, and software-help
objects. Incomplete author or help metadata can fail during conversion.

The host CLI also exposes authentication options for source access. Use its
`--help` output for the options available in your installed version.
