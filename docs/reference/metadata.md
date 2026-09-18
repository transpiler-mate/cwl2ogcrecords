# Typed metadata

Import the models from `cwl2ogcrecords.ogc_record`. They are `TypedDict`
structures with the same key spelling as the serialized JSON. Constructors
return ordinary dictionaries; nested changes remain visible in record metadata.

| Record property | Item or value type | Required fields |
| --- | --- | --- |
| `language` | `Language` | `code` |
| `languages`, `resource_languages` | `list[Language]` | `code` per item |
| `themes` | `list[Theme]` | `scheme`, `concepts`; each `ThemeConcept` requires `id` |
| `external_ids` | `list[ExternalId]` | `value`; `scheme` is optional |
| `formats` | `list[Format]` | `name` or `mediaType`, or both |
| `contacts` | `list[Contact]` | `name` or `organization`, or both |

`Format` and `Contact` are union type aliases, not constructors. Use
`NamedFormat` / `MediaTypeFormat` and `NamedContact` / `OrganizationContact`.

## Languages and themes

`Language` optionally accepts `name`, `alternate`, and `dir`. The direction is
one of `ltr`, `rtl`, `ttb`, or `btt`. The schema default is `ltr`; constructing a
model does not insert it. `code` represents an RFC 5646 language tag; a supplied
`name` must be nonempty.

A `Theme` contains a scheme string and a nonempty list of `ThemeConcept` items.
Each concept has an `id` and optional `title`, `description`, and URI `url`.

## Identifiers and formats

```python
from cwl2ogcrecords.ogc_record import ExternalId, MediaTypeFormat, NamedFormat

identifier = ExternalId(value="example-123", scheme="https://example.org/ids")
format_by_name = NamedFormat(name="GeoJSON")
format_by_type = MediaTypeFormat(mediaType="application/geo+json", name="GeoJSON")
```

## Contacts

```python
from cwl2ogcrecords.ogc_record import (
    ContactAddress,
    ContactDetail,
    ContactLink,
    ContactLogo,
    NamedContact,
)

contact = NamedContact(
    name="Alex Example",
    organization="Example organization",
    emails=[ContactDetail(value="alex@example.org", roles=["work"])],
    phones=[ContactDetail(value="+390612345678", roles=["work"])],
    addresses=[ContactAddress(city="Rome", country="IT")],
    links=[ContactLink(href="https://example.org", type="text/html")],
    logo=ContactLogo(
        href="https://example.org/logo.png", type="image/png", rel="icon"
    ),
    roles=["publisher"],
)
```

Both contact variants optionally accept `identifier`, `position`, `logo`,
`phones`, `emails`, `addresses`, `links`, `hoursOfService`, `contactInstructions`,
and `roles`. `NamedContact` requires `name`; `OrganizationContact` requires
`organization`. Either can also supply the other field.

- `ContactDetail` reuses the required string `value` structure used by external
  identifiers, with optional `roles`. Phone values follow the schema's
  international-number pattern; email values use email format.
- `ContactAddress` has optional `deliveryPoint` (a list of address lines), `city`,
  `administrativeArea`, `postalCode`, `country`, and `roles`.
- `ContactLink` requires URI `href` and media `type`; `rel` is optional.
- `ContactLogo` also requires `rel="icon"`; its media type should describe an image.
- Links and logos share optional `hreflang`, `title`, integer `length`, string-list
  `profile`, and date-time strings `created` and `updated`. `hreflang` is a string,
  not a `Language` object.
- `Roles` is a list of strings; the schema requires at least one entry when present.

## Typing and validation

The types express field types, required keys, literal values, and alternatives.
They do not enforce URI/email formats, regular expressions, minimum lengths,
or other schema constraints at runtime. Missing required keys can still be
constructed at runtime; use a static type checker and, where needed, an
[explicit schema validator](ogc_record.md#validation-and-loading-boundaries).

`MetadataField.__get__` currently returns `Any`, so reading a record accessor
loses some static type information. These structures do not change the live
properties dictionary or add automatic validation on assignment. Assigning
`None` to an optional metadata accessor removes its property.
