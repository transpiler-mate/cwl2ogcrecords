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

### Added

- Restore `application_url` and the generated `--application-url` option as an optional HTTP(S) execution endpoint, emitted as a separate `application` link with media type `application/json` and `application:container="HTTP"`. Keep the `context.source` link with media type `application/cwl`, its CWL metadata, and its file metadata; publication time still comes from the source. Omit the execution link when the option is unset. Consumers can distinguish the two links by relation and media type.

## [0.3.0] - 2026-11-02

### Added

- Populate record `published` from a valid `Last-Modified` response header, normalized to UTC, as an approximation based on source modification time. Omit it when the header is missing or invalid.

- Add `file:size` and a SHA-256 multihash in `file:checksum` to application links by fetching the context source again through the resolver's private `_session`, reusing its authentication and transport adapters. Metadata describes the second response; `file:local_path` is not inferred.
- Stream the second response with a 30-second request timeout, close the response while preserving the shared session, and raise `PluginExecutionError` when retrieval fails or the resolver has no session.
- Add tests for chunked and empty responses, checksum and size values, session reuse, response cleanup, retrieval failures, and missing resolver sessions.

### Changed

- Map authors, contributors, and publishers to contacts with resource `roles`, including explicit maintainer and custom roles. Stop using role names or `N/A` as organizational `position`; omit unavailable identifiers and contact details.
- Replace manually assembled Application extension metadata with `pystac-ext-application`, adding container, entrypoint, and CWL language metadata to record properties and application links.
- Use `context.source` as the sole application link URL source without filtering its scheme.
- The `application_url/--application-url` option is mapped to a `application:container: HTTP` and `media_type: application/json` link.

## [0.2.0] - 2026-10-10

### Added

- Add VCS v0.1.0 metadata with `pystac-ext-vcs` and `giturlparse`, reusing the single `repository_url` string for Git remotes, branches, tags, and revisions on links and record properties.
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

[Unreleased]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.3.0...HEAD
[0.3.0]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.1.2...0.2.0
[0.1.2]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/transpiler-mate/cwl2ogcrecords/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/transpiler-mate/cwl2ogcrecords/releases/tag/0.1.0
