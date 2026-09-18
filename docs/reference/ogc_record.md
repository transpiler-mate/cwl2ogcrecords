# OGC API - Records: PySTAC Item subclass

An OGC API Records GeoJSON model with PySTAC Item identity, link/asset APIs,
and access to existing Item-oriented extension factories.


## Example

```python
from cwl2ogcrecords.ogc_record import OGCRecord, OrganizationContact
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
import pystac

record = OGCRecord(
    id='elevation-record',
    geometry=None,
    properties={'type': 'dataset'},
    time={'interval': ['2020-01-01', '..']},
)
record.title = 'Elevation dataset'
record.description = 'An example catalog record'
record.keywords = ['elevation']
record.contacts = [OrganizationContact(organization='Example organization')]
record.properties['my-extension:quality'] = 'reviewed'

ProjectionExtension.ext(record, add_if_missing=True).code = 'EPSG:4326'
# EO fields are appropriate only when the described resource has EO semantics.
EOExtension.ext(record, add_if_missing=True).cloud_cover = 5.0
record.add_asset('data', pystac.Asset('https://example.org/elevation.tif'))
record.add_link(pystac.Link('license', 'https://example.org/license'))

payload = record.to_dict()  # OGC representation; no invented stac_version/date
restored = OGCRecord.from_dict(payload)
assert EOExtension.ext(restored).cloud_cover == 5.0

record.set_self_href('/tmp/record.json')
record.save_object()
restored = OGCRecord.from_file('/tmp/record.json')
```

See [typed metadata](metadata.md) for all nested models and construction examples.

## Contract and defaults

Source schemas:

- https://schemas.opengis.net/ogcapi/records/part1/1.0/openapi/schemas/recordGeoJSON.yaml
- https://schemas.opengis.net/ogcapi/records/part1/1.0/openapi/schemas/recordCommonProperties.yaml
- https://schemas.opengis.net/ogcapi/records/part1/1.0/openapi/schemas/time.yaml

The root schema requires `id`, `type`, `geometry`, and `properties`. It does not
supply application defaults for title, contacts, dates, or other metadata. This
implementation emits `type: Feature`, defaults geometry to null, and requires
an identifier. Omitting properties produces null; pass `{}` for an empty object.
Internally properties is always a dictionary so extension accessors work; a
parsed null is preserved on export until properties are populated. Links default
to an empty list. No title, date, or conformance claim is fabricated.

`OGCRecord` provides direct live accessors for all fields currently listed by
recordCommonProperties: created, updated, type, title, description, keywords,
themes, language, languages, resourceLanguages, externalIds, formats, contacts,
license, and rights. Python names use underscores for compound names. The older `record_metadata`
view remains available and accesses the same dictionary. `record.type` maps to
`properties.type`; the top-level GeoJSON type stays `Feature`. Dates
remain JSON strings; nested values remain dictionaries/lists. Optional accessor
assignment of None removes a property. Unknown properties are retained.

`time`, `conforms_to`, and `link_templates` map to their OGC top-level fields.
Reading the two list accessors creates an empty list if missing, allowing append.
To preserve an explicitly null time, set `record.time = None`; to omit it, remove
`record.extra_fields['time']`. `from_dict` preserves missing versus null time.

OGC integer identifiers survive export through `record_id`; the inherited `id`
is their string form for PySTAC utilities. Changing `id` changes the exported
identifier (to a string). Inputs with boolean identifiers are rejected.

## Extension compatibility

The class really inherits Item: `isinstance(record, pystac.Item)` is true. It
retains properties, assets, asset ownership, links, collection_id, datetime,
stac_extensions, common_metadata and the inherited extension accessor. No fixed
extension allowlist is used. Existing and future Item-oriented factories can
therefore accept it, subject to their own requirements.

This is not a guarantee for every extension. Extensions may require valid
geometry, an actual temporal extent, assets, or other STAC-specific semantics.
An extension may also change its implementation or serialize internally. Review
new extensions against your Records and pin/test PySTAC upgrades.

Extension declarations remain in `stac_extensions`, and assets remain in
`assets`, as foreign members in the OGC representation. They are never silently
removed or renamed to `conformsTo`. Keep conformance identifiers separate and
only declare conformance you actually implement. Unknown top-level fields are
preserved through `extra_fields` (managed fields cannot be supplied there).

## Temporal model and serialization

`to_dict()` and `to_record_dict()` serialize the OGC representation; inherited
`save_object()` and `__geo_interface__` therefore use that representation too.
`from_dict()` accepts Records without STAC version or STAC datetime. Its migrate
argument is accepted for PySTAC signature compatibility but does not invoke STAC
migrations. It always copies input metadata; preserve_dict=False is only a hint.

The constructor initializes STACObject directly, then initializes Item's required
attributes. It intentionally does not call Item.__init__, avoiding the mandatory
STAC datetime/interval check without synthetic dates. This is the principal
maintenance seam and the reason for the PySTAC version constraint.

OGC `time` is independent of STAC `datetime` / start_datetime / end_datetime.
Date-only and open OGC intervals cannot be losslessly converted automatically.
Explicit STAC datetime constructor arguments are preserved in properties. Do not
assume that changing OGC time will update STAC time, or vice versa.

`to_stac_item()` creates a separate ordinary Item only when genuine STAC datetime
or start/end values exist. It preserves Record foreign fields and extensions.
It does not guarantee full STAC validity: geometry/bbox and extension constraints
still need validation via the returned Item's validate().

## Validation and loading boundaries

This initial implementation performs basic structural recognition, not complete
validation of geometry, nested metadata, times or extension schemas. The supplied
OGC schemas use OpenAPI 3.0 constructs such as nullable and external references;
do not feed them blindly to a Draft 2020-12 JSON Schema validator. In particular,
the object/oneOf branches in the published root schema deserve review with your
chosen validator because their alternatives can overlap.

`record.validate(validator=...)` accepts an explicitly configured validator with
a `validate(document)` method. Resolve the OGC schema references and dialect
before supplying it. Calling validate() without one raises an actionable error
instead of incorrectly running STAC validation. The returned schema URI identifies
the intended contract; configuring the validator correctly is the caller's duty.
No complete OGC or extension-schema validation is claimed by the tests.

Use `OGCRecord.from_file` and `OGCRecord.from_dict`. Global `pystac.read_file`,
automatic link resolution, STAC catalog traversal, and pystac-client do not
register this class automatically. Root/parent/collection traversal still assumes
STAC catalogs. Generic GeoJSON and STAC Features overlap structurally; the
matches_object_type method is not a unique Record discriminator.
