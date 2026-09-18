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

import json
from copy import deepcopy
from datetime import datetime, timezone

import pystac
import pytest
from pystac.extensions.base import PropertiesExtension
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.timestamps import TimestampsExtension

from cwl2ogcrecords.ogc_record import OGCRecord


def test_timeless_record():
    r = OGCRecord("service", properties={"type": "service"})
    assert isinstance(r, pystac.Item)
    assert r.datetime is None
    assert r.to_dict() == {
        "type": "Feature",
        "id": "service",
        "geometry": None,
        "properties": {"type": "service"},
        "links": [],
    }
    with pytest.raises(ValueError, match="temporal|datetime"):
        r.to_stac_item()


@pytest.mark.parametrize("identifier", ["abc", 42])
@pytest.mark.parametrize("props", [None, {}, {"title": "Example", "new:field": [1]}])
def test_roundtrip(identifier, props):
    doc = {
        "type": "Feature",
        "id": identifier,
        "geometry": None,
        "properties": props,
        "time": {"interval": ["2020-01-01", ".."]},
        "conformsTo": ["https://example.org/profile"],
        "linkTemplates": [{"uriTemplate": "https://example.org/{id}", "rel": "item"}],
        "custom": {"nested": True},
        "links": [],
    }
    original = deepcopy(doc)
    r = OGCRecord.from_dict(doc)
    assert r.to_dict() == original
    assert doc == original
    assert r.id == str(identifier)
    assert r.clone().to_dict() == original


def test_existing_extensions_and_asset_ownership():
    r = OGCRecord("scene", properties={})
    EOExtension.ext(r, add_if_missing=True).cloud_cover = 12.5
    ProjectionExtension.ext(r, add_if_missing=True).code = "EPSG:4326"
    expiry = datetime(2030, 1, 1, tzinfo=timezone.utc)
    TimestampsExtension.ext(r, add_if_missing=True).expires = expiry
    a = pystac.Asset("https://example.org/result.tif")
    r.add_asset("result", a)
    TimestampsExtension.ext(a).expires = expiry
    assert a.owner is r
    assert EOExtension.ext(r).cloud_cover == 12.5
    assert ProjectionExtension.ext(r).code == "EPSG:4326"
    assert TimestampsExtension.ext(r).expires == expiry
    restored = OGCRecord.from_dict(r.to_dict())
    assert TimestampsExtension.ext(restored.assets["result"]).expires == expiry
    assert restored.assets["result"].owner is restored
    assert restored.stac_extensions == r.stac_extensions
    assert "conformsTo" not in r.to_dict()


def test_future_extension_without_registration():
    class FutureExtension(PropertiesExtension):
        def __init__(self, item):
            assert isinstance(item, pystac.Item)
            self.properties = item.properties

        @property
        def score(self):
            return self._get_property("future:score", int)

        @score.setter
        def score(self, value):
            self._set_property("future:score", value)

    r = OGCRecord("new")
    FutureExtension(r).score = 7
    assert OGCRecord.from_dict(r.to_dict()).properties["future:score"] == 7


def test_metadata_live_and_clone_independent():
    r = OGCRecord("metadata", properties={})
    r.record_metadata.title = "Demo"
    r.record_metadata.resource_languages = [{"code": "en"}]
    r.record_metadata.contacts = [{"name": "A"}]
    r.add_link(
        pystac.Link(
            "related", "https://example.org/data", extra_fields={"custom:flag": True}
        )
    )
    target = OGCRecord("target")
    r.add_link(pystac.Link("derived_from", target))
    c = r.clone()
    c.record_metadata.contacts[0]["name"] = "B"
    assert r.properties["contacts"][0]["name"] == "A"
    assert c.get_single_link("derived_from").target is target
    assert c.links[0].owner is c
    assert r.properties["resourceLanguages"] == [{"code": "en"}]
    r.record_metadata.title = None
    assert "title" not in r.properties


def test_io(tmp_path):
    r = OGCRecord(123, properties={"title": "Demo"})
    path = str(tmp_path / "record.json")
    r.set_self_href(path)
    r.save_object()
    restored = OGCRecord.from_file(path)
    assert isinstance(restored, OGCRecord)
    assert restored.record_id == 123
    assert restored.get_self_href() == path
    assert "stac_version" not in json.loads((tmp_path / "record.json").read_text())


def test_stac_export_and_no_mutation():
    r = OGCRecord(
        "scene",
        datetime=datetime(2025, 1, 1, tzinfo=timezone.utc),
        geometry={"type": "Point", "coordinates": [0, 0]},
        bbox=[0, 0, 0, 0],
    )
    before = deepcopy(r.properties)
    doc = r.to_stac_item().to_dict()
    assert doc["stac_version"]
    assert doc["properties"]["datetime"] == "2025-01-01T00:00:00Z"
    assert r.properties == before
    assert "stac_version" not in r.to_dict()


def test_validation_requires_explicit_ogc_validator():
    with pytest.raises(ValueError, match="OGC schema validator"):
        OGCRecord("test").validate()


@pytest.mark.parametrize(
    "doc",
    [
        {"type": "Feature", "id": True, "geometry": None, "properties": {}},
        {"type": "Feature", "id": "x", "properties": {}},
        {"type": "Feature", "id": "x", "geometry": None, "properties": []},
    ],
)
def test_reject_invalid_structure(doc):
    with pytest.raises(ValueError):
        OGCRecord.from_dict(doc)


def test_direct_metadata_serialization_and_shared_view():
    r = OGCRecord("elevation")
    r.title = "Elevation dataset"
    r.keywords = ["elevation", "DEM"]
    r.license = "CC-BY-4.0"
    r.type = "dataset"
    r.resource_languages = [{"code": "en"}]
    doc = r.to_dict()
    assert doc["type"] == "Feature"
    assert doc["properties"] == {
        "title": "Elevation dataset",
        "keywords": ["elevation", "DEM"],
        "license": "CC-BY-4.0",
        "type": "dataset",
        "resourceLanguages": [{"code": "en"}],
    }
    assert "title" not in doc
    assert r.record_metadata.title == r.title
    r.record_metadata.title = "Updated"
    assert r.title == "Updated"
    restored = OGCRecord.from_dict(r.to_dict())
    assert restored.title == "Updated"
    clone = restored.clone()
    clone.keywords.append("clone")
    assert restored.keywords == ["elevation", "DEM"]
    r.license = None
    assert "license" not in r.properties
    EOExtension.ext(r, add_if_missing=True).cloud_cover = 4
    assert EOExtension.ext(r).cloud_cover == 4
