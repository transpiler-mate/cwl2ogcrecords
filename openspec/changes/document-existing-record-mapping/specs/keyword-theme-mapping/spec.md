# Spec Delta

## Purpose

Describe how resolved software keywords become keyword strings and grouped theme concepts in an OGC Record. This captures existing behavior for successful conversions, without defining CWL parsing or claiming complete output-schema conformance.

## ADDED Requirements

### Requirement: Empty keyword and theme results remain arrays

The plugin SHALL serialize `properties.keywords` and `properties.themes` as empty arrays when no entries qualify for their respective outputs. An absent keyword value, an empty scalar string, or an empty list SHALL produce two empty arrays.

#### Scenario: No keyword value
- **WHEN** conversion succeeds with resolved `keywords` equal to `None`
- **THEN** `properties.keywords` is `[]`
- **AND** `properties.themes` is `[]`

#### Scenario: Empty scalar string
- **WHEN** conversion succeeds with resolved `keywords` equal to `""`
- **THEN** `properties.keywords` is `[]`
- **AND** `properties.themes` is `[]`

#### Scenario: Empty keyword list
- **WHEN** conversion succeeds with resolved `keywords` equal to `[]`
- **THEN** `properties.keywords` is `[]`
- **AND** `properties.themes` is `[]`

### Requirement: Text keywords are retained

The plugin SHALL copy nonempty scalar text keywords into a one-element keyword array and retain text entries from keyword lists in source order. Text entries SHALL NOT create themes.

#### Scenario: One text keyword
- **WHEN** conversion succeeds with resolved `keywords` equal to `"elevation"`
- **THEN** `properties.keywords` is `["elevation"]`
- **AND** `properties.themes` is `[]`

#### Scenario: Multiple text keywords
- **WHEN** conversion succeeds with resolved `keywords` equal to `["elevation", "terrain"]`
- **THEN** `properties.keywords` is `["elevation", "terrain"]`
- **AND** `properties.themes` is `[]`

### Requirement: Complete terms form ordered themes

The plugin SHALL map a scalar defined term or defined terms in a keyword list into themes when both the scheme and term code are truthy. Terms SHALL be grouped by their resolved scheme, with themes in first-seen scheme order and concepts in source order within each theme. A term SHALL use its code as the concept `id` and SHALL NOT also become a text keyword.

#### Scenario: One complete term
- **WHEN** conversion succeeds with one resolved term whose scheme is `https://example.org/themes` and code is `elevation`
- **THEN** `properties.keywords` is `[]`
- **AND** `properties.themes` contains one theme with scheme `https://example.org/themes` and one concept whose `id` is `elevation`

#### Scenario: Mixed text and terms across schemes
- **GIVEN** the resolved keyword list contains, in order, text `terrain`, term `elevation` in `https://example.org/themes`, term `water` in `https://example.org/other`, and term `slope` in `https://example.org/themes`
- **WHEN** conversion succeeds
- **THEN** `properties.keywords` is `["terrain"]`
- **AND** the theme schemes are `["https://example.org/themes", "https://example.org/other"]` in that order
- **AND** the first theme's concept IDs are `["elevation", "slope"]` in that order
- **AND** the second theme's concept IDs are `["water"]`

### Requirement: Incomplete terms are omitted

The plugin SHALL omit a defined term from both keyword and theme outputs if its scheme or term code is not truthy. It SHALL NOT substitute the term's name or description for a missing code or scheme.

#### Scenario: Term has no scheme
- **WHEN** conversion succeeds with one resolved term whose code is `elevation` and whose scheme is `None`
- **THEN** `properties.keywords` is `[]`
- **AND** `properties.themes` is `[]`

#### Scenario: Term has no code
- **WHEN** conversion succeeds with one resolved term whose scheme is `https://example.org/themes` and whose code is `None`
- **THEN** `properties.keywords` is `[]`
- **AND** `properties.themes` is `[]`

### Requirement: Concept labels are optional

The plugin SHALL copy a qualifying term's truthy name into concept `title` and truthy description into concept `description`. Missing labels SHALL be omitted independently, without discarding the concept.

#### Scenario: Both labels supplied
- **WHEN** conversion succeeds with a qualifying term whose code is `elevation`, name is `Elevation`, and description is `About elevation`
- **THEN** the concept contains `id: "elevation"`, `title: "Elevation"`, and `description: "About elevation"`

#### Scenario: Name absent
- **WHEN** conversion succeeds with a qualifying term whose code is `elevation`, name is `None`, and description is `About elevation`
- **THEN** the concept retains `id: "elevation"` and `description: "About elevation"`
- **AND** the concept has no `title` member

#### Scenario: Description absent
- **WHEN** conversion succeeds with a qualifying term whose code is `elevation`, name is `Elevation`, and description is `None`
- **THEN** the concept retains `id: "elevation"` and `title: "Elevation"`
- **AND** the concept has no `description` member

### Requirement: Vocabulary schemes are not concept URLs

The plugin SHALL emit the vocabulary URI as the theme's `scheme` and SHALL NOT reuse it as a concept `url`.

#### Scenario: Vocabulary URI belongs to the theme
- **WHEN** conversion succeeds with a qualifying term whose scheme is `https://example.org/themes` and code is `elevation`
- **THEN** the containing theme has `scheme: "https://example.org/themes"`
- **AND** the concept has `id: "elevation"` and no `url` member

