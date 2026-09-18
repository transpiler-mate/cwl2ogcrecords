# Copyright 2026 Transpiler-Mate
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OGC API Records adapter for PySTAC 1.x.x; see README for boundaries."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeAlias, TypedDict, TypeVar

import pystac
from pystac.utils import datetime_to_str, str_to_datetime

T = TypeVar("T")


if TYPE_CHECKING:
    from datetime import datetime as Datetime


class _RequiredLanguage(TypedDict):
    code: str


class Language(_RequiredLanguage, total=False):
    """Language metadata as defined by the OGC Records language.yaml schema.

    ``code`` is a required RFC 5646 language tag. Optional ``name`` is the
    untranslated language name and must be nonempty when supplied;
    ``alternate`` names the language in another language, usually English.
    ``dir`` defaults to ``ltr`` in the schema when omitted.

    This structure provides static typing, not runtime schema validation.
    """

    name: str
    alternate: str
    dir: Literal["ltr", "rtl", "ttb", "btt"]


class _RequiredThemeConcept(TypedDict):
    id: str


class ThemeConcept(_RequiredThemeConcept, total=False):
    """A theme concept with a required identifier and optional descriptions.

    ``url``, when supplied, must be a URI.
    """

    title: str
    description: str
    url: str


class Theme(TypedDict):
    """Theme metadata as defined by the OGC Records theme.yaml schema.

    Both fields are required. ``concepts`` must contain at least one concept;
    ``scheme`` identifies the knowledge organization system, preferably by a
    resolvable URI. This structure provides static typing, not runtime schema
    validation.
    """

    concepts: list[ThemeConcept]
    scheme: str


class _RequiredFormatName(TypedDict):
    name: str


class NamedFormat(_RequiredFormatName, total=False):
    """A format identified by name, optionally including its media type."""

    mediaType: str


class _RequiredFormatMediaType(TypedDict):
    mediaType: str


class MediaTypeFormat(_RequiredFormatMediaType, total=False):
    """A format identified by media type, optionally including its name."""

    name: str


# OGC format.yaml requires name or mediaType (or both). The union expresses
# this constraint for static typing without runtime schema validation.
Format: TypeAlias = NamedFormat | MediaTypeFormat


class _RequiredExternalId(TypedDict):
    value: str


class ExternalId(_RequiredExternalId, total=False):
    """An external identifier with a required value and optional scheme.

    ``scheme`` references the authority or knowledge organization system
    from which the identifier was obtained, preferably by a resolvable URI.
    This structure provides static typing, not runtime schema validation.
    """

    scheme: str


# roles.yaml requires at least one entry; length is not checked at runtime.
Roles: TypeAlias = list[str]


class ContactDetail(_RequiredExternalId, total=False):
    """A phone number or email address with optional roles.

    Reuses the required string value structure. Phone values must match
    ``^\\+[1-9]{1}[0-9]{3,14}$``; email values must use email format.
    """

    roles: Roles


class ContactAddress(TypedDict, total=False):
    """A contact's physical address; all fields are optional."""

    deliveryPoint: list[str]
    city: str
    administrativeArea: str
    postalCode: str
    country: str
    roles: Roles


class _RequiredContactLink(TypedDict):
    href: str
    type: str


class _ContactLinkFields(_RequiredContactLink, total=False):
    """Shared contact link fields from linkBase.yaml and link.yaml.

    ``href`` must be a URI; ``created`` and ``updated`` use date-time strings.
    """

    hreflang: str
    title: str
    length: int
    profile: list[str]
    created: str
    updated: str


class ContactLink(_ContactLinkFields, total=False):
    """An online contact link with required href and media type."""

    rel: str


class ContactLogo(_ContactLinkFields):
    """A contact logo with required href, media type, and icon relation.

    The media type should be an image media type.
    """

    rel: Literal["icon"]


class _ContactFields(TypedDict, total=False):
    identifier: str
    position: str
    logo: ContactLogo
    phones: list[ContactDetail]
    emails: list[ContactDetail]
    addresses: list[ContactAddress]
    links: list[ContactLink]
    hoursOfService: str
    contactInstructions: str
    roles: Roles


class _RequiredContactName(_ContactFields):
    name: str


class NamedContact(_RequiredContactName, total=False):
    """A contact identified by name, optionally including an organization."""

    organization: str


class _RequiredContactOrganization(_ContactFields):
    organization: str


class OrganizationContact(_RequiredContactOrganization, total=False):
    """A contact identified by organization, optionally including a name."""

    name: str


# contact.yaml requires name or organization (or both). As with Format,
# the union provides static typing, not runtime schema validation.
Contact: TypeAlias = NamedContact | OrganizationContact


class MetadataField(Generic[T]):
    """A live, optional accessor into the record properties dictionary."""

    def __init__(self, key: str):
        self.key = key

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        if instance is None:
            return self
        return instance.properties.get(self.key)

    def __set__(self, instance: Any, value: T | None) -> None:
        if value is None:
            instance.properties.pop(self.key, None)
        else:
            instance.properties[self.key] = value


class RecordMetadataMixin:
    """Direct recordCommonProperties accessors; dates use their JSON string form.

    Nested structures remain open dictionaries, allowing future extensions.
    These accessors do not perform JSON Schema validation.
    """

    created = MetadataField[str]("created")
    updated = MetadataField[str]("updated")
    type = MetadataField[str]("type")
    title = MetadataField[str]("title")
    description = MetadataField[str]("description")
    keywords = MetadataField[list[str]]("keywords")
    themes = MetadataField[list[Theme]]("themes")
    language = MetadataField[Language]("language")
    languages = MetadataField[list[Language]]("languages")
    resource_languages = MetadataField[list[Language]]("resourceLanguages")
    external_ids = MetadataField[list[ExternalId]]("externalIds")
    formats = MetadataField[list[Format]]("formats")
    contacts = MetadataField[list[Contact]]("contacts")
    license = MetadataField[str]("license")
    rights = MetadataField[str]("rights")


class RecordCommonProperties(RecordMetadataMixin):
    """Backward-compatible metadata view sharing the record properties."""

    def __init__(self, record: OGCRecord):
        self.record = record

    @property
    def properties(self) -> dict[str, Any]:
        return self.record.properties

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.properties)


class OGCRecord(RecordMetadataMixin, pystac.Item):
    """Item-compatible Record, with OGC serialization as the default.

    Initializes STACObject directly to avoid Item's mandatory temporal extent.
    This compatibility seam must be reviewed for future PySTAC releases.
    `time` and STAC datetime fields are independent: no implicit conversion.
    """

    SCHEMA_URI = (
        "https://schemas.opengis.net/ogcapi/records/part1/1.0/"
        "openapi/schemas/recordGeoJSON.yaml"
    )
    _RESERVED = {
        "id",
        "type",
        "geometry",
        "properties",
        "links",
        "assets",
        "bbox",
        "collection",
        "stac_extensions",
    }

    def __init__(  # noqa: C901
        self,
        id: str | int,
        geometry: dict[str, Any] | None = None,
        bbox: list[float] | None = None,
        datetime: Datetime | None = None,
        properties: dict[str, Any] | None = None,
        start_datetime: Datetime | None = None,
        end_datetime: Datetime | None = None,
        stac_extensions: list[str] | None = None,
        href: str | None = None,
        collection: str | pystac.Collection | None = None,
        extra_fields: dict[str, Any] | None = None,
        assets: dict[str, pystac.Asset] | None = None,
        *,
        time: dict[str, Any] | None = None,
        conforms_to: list[str] | None = None,
        link_templates: list[dict[str, Any]] | None = None,
    ):
        if isinstance(id, bool) or not isinstance(id, (str, int)):
            raise TypeError("Record id must be a string or integer")
        pystac.STACObject.__init__(self, list(stac_extensions or []))
        self._record_id = id
        self.id = str(id)  # PySTAC path/layout utilities require a string.
        self.geometry = deepcopy(geometry)
        self.bbox = deepcopy(bbox)
        self._null_properties = properties is None
        self.properties = deepcopy(properties) if properties is not None else {}
        self.extra_fields = deepcopy(extra_fields) if extra_fields else {}
        if self._RESERVED.intersection(self.extra_fields):
            raise ValueError("extra_fields must not override managed fields")
        self.assets = {}
        self.collection_id = None
        self._stac_io = None
        self.datetime = datetime
        if datetime is not None:
            self.properties["datetime"] = datetime_to_str(datetime)
        elif self.properties.get("datetime") is not None:
            self.datetime = str_to_datetime(self.properties["datetime"])
        if start_datetime is not None:
            self.properties["start_datetime"] = datetime_to_str(start_datetime)
        if end_datetime is not None:
            self.properties["end_datetime"] = datetime_to_str(end_datetime)
        if time is not None:
            self.time = deepcopy(time)
        if conforms_to is not None:
            self.conforms_to = list(conforms_to)
        if link_templates is not None:
            self.link_templates = deepcopy(link_templates)
        if isinstance(collection, pystac.Collection):
            self.set_collection(collection)
        elif collection is not None:
            self.collection_id = collection
        for key, asset in (assets or {}).items():
            self.add_asset(key, asset)
        if href is not None:
            self.set_self_href(href)

    @property
    def record_id(self) -> str | int:
        return self._record_id if str(self._record_id) == self.id else self.id

    @property
    def record_metadata(self) -> RecordCommonProperties:
        return RecordCommonProperties(self)

    @property
    def time(self) -> dict[str, Any] | None:
        return self.extra_fields.get("time")

    @time.setter
    def time(self, value: dict[str, Any] | None) -> None:
        self.extra_fields["time"] = value

    @property
    def conforms_to(self) -> list[str]:
        return self.extra_fields.setdefault("conformsTo", [])

    @conforms_to.setter
    def conforms_to(self, value: list[str]) -> None:
        self.extra_fields["conformsTo"] = value

    @property
    def link_templates(self) -> list[dict[str, Any]]:
        return self.extra_fields.setdefault("linkTemplates", [])

    @link_templates.setter
    def link_templates(self, value: list[dict[str, Any]]) -> None:
        self.extra_fields["linkTemplates"] = value

    def to_dict(
        self, include_self_link: bool = True, transform_hrefs: bool = True
    ) -> dict[str, Any]:
        props = deepcopy(self.properties)
        if self.datetime is not None:
            props["datetime"] = datetime_to_str(self.datetime)
        doc = deepcopy(self.extra_fields)
        doc.update(
            type="Feature",
            id=self.record_id,
            geometry=deepcopy(self.geometry),
            properties=None if self._null_properties and not props else props,
            links=[
                link.to_dict(transform_href=transform_hrefs)
                for link in self.links
                if include_self_link or link.rel != pystac.RelType.SELF
            ],
        )
        if self.bbox is not None:
            doc["bbox"] = list(self.bbox)
        # Preserve extension declarations/assets as GeoJSON foreign members.
        # Never substitute conformsTo for stac_extensions.
        if self.stac_extensions:
            doc["stac_extensions"] = list(self.stac_extensions)
        if self.assets:
            doc["assets"] = {
                key: deepcopy(asset.to_dict()) for key, asset in self.assets.items()
            }
        if self.collection_id is not None:
            doc["collection"] = self.collection_id
        return doc

    def to_record_dict(
        self, include_self_link: bool = True, transform_hrefs: bool = True
    ) -> dict[str, Any]:
        return self.to_dict(include_self_link, transform_hrefs)

    @classmethod
    def matches_object_type(cls, d: dict[str, Any]) -> bool:
        # Structural recognition only; GeoJSON/STAC overlap prevents unique dispatch.
        return (
            d.get("type") == "Feature"
            and all(key in d for key in ("id", "geometry", "properties"))
            and isinstance(d["id"], (str, int))
            and not isinstance(d["id"], bool)
            and (d["properties"] is None or isinstance(d["properties"], dict))
        )

    @classmethod
    def from_dict(
        cls,
        d: dict[str, Any],
        href: str | None = None,
        root: pystac.Catalog | None = None,
        migrate: bool = True,
        preserve_dict: bool = True,
    ) -> OGCRecord:
        """Read Records; migrate is accepted for compatibility but never applied.

        Always copies document metadata, even when preserve_dict=False.
        """
        if not cls.matches_object_type(d):
            raise ValueError(
                "Expected a Record GeoJSON Feature with id, geometry, properties"
            )
        obj = cls(
            id=d["id"],
            geometry=d["geometry"],
            properties=d["properties"],
            bbox=d.get("bbox"),
            collection=d.get("collection"),
            stac_extensions=d.get("stac_extensions"),
            extra_fields={k: v for k, v in d.items() if k not in cls._RESERVED},
            assets={
                k: pystac.Asset.from_dict(deepcopy(v))
                for k, v in d.get("assets", {}).items()
            },
        )
        for link in d.get("links", []):
            if href is None or link.get("rel") != "self":
                obj.add_link(pystac.Link.from_dict(deepcopy(link)))
        if href is not None:
            obj.set_self_href(href)
        if root is not None:
            obj.set_root(root)
        return obj

    def clone(self) -> OGCRecord:
        doc = self.to_dict(transform_hrefs=False)
        doc["links"] = []
        result = type(self).from_dict(doc)
        for link in self.links:
            result.add_link(link.clone())
        result._stac_io = self._stac_io
        return result

    def to_stac_item(self) -> pystac.Item:
        """Explicit export; requires a genuine STAC temporal extent.

        Constructing an Item does not replace full STAC schema validation.
        """
        if self.datetime is None and not all(
            self.properties.get(k) is not None
            for k in ("start_datetime", "end_datetime")
        ):
            raise ValueError(
                "STAC export requires datetime or start_datetime/end_datetime"
            )
        extra = deepcopy(self.extra_fields)
        extra.pop("stac_version", None)
        item = pystac.Item(
            id=self.id,
            geometry=deepcopy(self.geometry),
            bbox=deepcopy(self.bbox),
            datetime=self.datetime,
            properties=deepcopy(self.properties),
            stac_extensions=list(self.stac_extensions),
            collection=self.collection_id,
            extra_fields=extra,
            assets={k: v.clone() for k, v in self.assets.items()},
        )
        for link in self.links:
            item.add_link(link.clone())
        return item

    def validate(self, validator: Any = None) -> list[Any]:
        """Validate the OGC document with an explicitly supplied validator.

        Supply an object exposing validate(document), configured for the OGC
        OpenAPI 3.0 schema and its references. No implicit STAC validation.
        """
        if validator is None:
            raise ValueError(
                "Supply an OGC schema validator; for STAC use "
                "record.to_stac_item().validate()"
            )
        validator.validate(self.to_dict(transform_hrefs=False))
        return [self.SCHEMA_URI]

    def __repr__(self) -> str:
        return f"<OGCRecord id={self.record_id!r}>"
