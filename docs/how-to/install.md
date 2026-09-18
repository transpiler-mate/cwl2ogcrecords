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

# Install

Python 3.10 or later is required. The package depends on `transpiler-mate-api`,
Loguru, and PySTAC (`>1,<2`).

## Use the published package

```bash
python -m pip install cwl2ogcrecords
```

For command-line conversion, the `transpiler-mate` CLI must also be installed
in the same environment. This package registers a plugin entry point; it does
not install a standalone `cwl2ogcrecords` executable.

Verify plugin discovery:

```bash
transpiler-mate --help
transpiler-mate cwl2ogcrecords --help
```

If the command is missing, check that the CLI and plugin use the same Python
environment. Direct Python use only needs the package:

```python
from cwl2ogcrecords.ogc_record import OGCRecord
```

## Work from source

```bash
git clone https://github.com/Transpiler-Mate/cwl2ogcrecords
cd cwl2ogcrecords
python -m pip install -e .
```

## Preview documentation

From the repository root:

```bash
python -m pip install mkdocs 'mkdocstrings[python]' pymdown-extensions
python -m mkdocs serve -f mkdocs.yaml
```

To check the complete site without serving it:

```bash
python -m mkdocs build --strict -f mkdocs.yaml
```
