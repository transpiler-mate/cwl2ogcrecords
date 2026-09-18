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

# Create your first record

This tutorial creates a record directly in Python, adds typed metadata, and
writes a GeoJSON file. Install the package first:

```bash
python -m pip install cwl2ogcrecords
```

## Describe a resource

Save the following as `create_record.py`:

```python
from cwl2ogcrecords.ogc_record import (
    ContactDetail,
    Language,
    NamedFormat,
    OGCRecord,
    OrganizationContact,
    Theme,
    ThemeConcept,
)

record = OGCRecord(id="example-workflow")
record.type = "software"
record.title = "Example workflow"
record.description = "A workflow for processing elevation data."
record.language = Language(code="en", name="English")
record.keywords = ["elevation"]
record.themes = [
    Theme(
        scheme="https://example.org/topics",
        concepts=[ThemeConcept(id="elevation", title="Elevation")],
    )
]
record.formats = [NamedFormat(name="CWL", mediaType="application/cwl+yaml")]
record.contacts = [
    OrganizationContact(
        organization="Example team",
        emails=[ContactDetail(value="team@example.org", roles=["work"])],
    )
]
record.license = "Apache-2.0"

record.set_self_href("record.json")
record.save_object()

restored = OGCRecord.from_file("record.json")
assert restored.title == "Example workflow"
assert restored.to_dict()["type"] == "Feature"
print(restored.to_dict()["properties"]["language"])
```

Run it:

```bash
python create_record.py
```

The script writes `record.json` and prints `{'code': 'en', 'name': 'English'}`.
The output has a top-level GeoJSON `type` of `Feature`; `record.type` is stored
as `properties.type`. Geometry is `null`, and no date is required or invented.
`save_object()` includes the self link set by `set_self_href()`.

The metadata constructors produce ordinary dictionaries. Their type annotations
help static checking; they do not validate values at runtime.

## Next steps

Use the [CLI guide](../how-to/use-cli.md) to convert an existing CWL source, or
consult [typed metadata](../reference/metadata.md) for the remaining fields.
