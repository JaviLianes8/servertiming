# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Changed

- `parse` reads values the way browsers do and passes the web-platform-tests corpus: a
  metric name must be a token, characters after a name or a value up to the next `;` or
  `,` are ignored, parameter names are case-insensitive, the first occurrence of a
  parameter wins, `dur` may be quoted, and an unterminated quoted string reads as empty.
- `dur` is read with the HTML rules for floating-point numbers (`12ms` is 12, `inf` is no
  duration).
- `parse` keeps extension parameters in `Metric.params` instead of dropping them.
- `build` raises `ServerTimingError` (a `ValueError`) for a description or parameter value
  holding CR, LF or another character no HTTP field can carry, closing a header injection.
- `Timing` checks names and descriptions when a metric is recorded, not when the header
  is rendered.

### Added

- `parse(value, strict=True)` checks values against the grammar and raises
  `ServerTimingError` with `field` and `position`.
- `parse` accepts several field values (headers then trailers).
- `Metric.params`, `Metric.param()`, `Metric.duration`, `Metric.description` and
  `str(metric)`.
- `build(..., precision=n)` and `Timing.header(precision=n)` round durations.
- `Timing.measure` decorates plain and `async` functions; `Timing.start` returns a `Timer`.
- The `servertiming` command shows and checks values from arguments or response headers.

## [0.1.0]

- First release: `build` and `parse` for the Server-Timing header, a `Metric` value
  type, and a `Timing` collector with a `measure` context manager.
