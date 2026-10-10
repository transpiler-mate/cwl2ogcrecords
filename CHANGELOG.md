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

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-10

### Added

- Enrich workflow records with Application links, software version, and optional scientific citations and publication DOIs.
- Add explicit public resource and citation options without inventing execution provenance.

### Fixed

- Retain theme concepts without optional labels and stop treating a vocabulary URI as an individual concept URL.

## [0.1.2] - 2026-10-07

* Custom _OGC API - Record_ replaced by the `pystac-ext-ogc-record` extension.

## [0.1.1] - 2026-09-27

### Changed

* Improve type annotations and internal code quality by addressing mypy, Ruff, and Bandit findings, without changing public APIs or runtime behavior.

## [0.1.0] - 2026-09-18

### Added

- Initial project release.

[Unreleased]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.2.0...HEAD
[0.2.0]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.1.2...0.2.0
[0.1.2]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/transpiler-mate/cwl2ogcrecords/releases/tag/0.1.0
