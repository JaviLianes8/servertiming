# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-19

The public API is now stable: the seven names in `timingheader.__all__`, their
signatures, defaults and error types follow Semantic Versioning from this release on.
This is the first release on PyPI.

### Stable

- Parsing: `parse` reads one or several field values (headers then trailers) the way
  browsers do and never raises on malformed text; `strict=True` checks each value
  against the grammar with the sender rules.
- Building: `build` and `str(metric)` never write a value that could split or corrupt the
  response header.
- `Metric`, the frozen value both sides use.
- Recording: `Timing` with `add`, `measure` (block or decorator, plain or `async`),
  `start`, `metrics` and `header`; `Measure` and `Timer`.
- Errors: `ServerTimingError` (a `ValueError`) for a value that cannot be written or
  breaks the grammar, with `field` and `position` from strict parsing; `TypeError` for an
  argument of the wrong type.
- The `timingheader` command and `python -m timingheader`.

### Changed

- The distribution, the import package and the command are named `timingheader`; the
  project was developed as `servertiming`, a name PyPI does not accept.
- `build`, `str(metric)` and `Timing` raise `TypeError` (they raised
  `ServerTimingError`) for an argument of the wrong type: a single `Metric` or a `str`
  instead of an iterable, an item that is not a `Metric`, a name, description or
  parameter that is not a `str`, a duration that is not an `int` or a `float` (a `bool`
  included), a parameter that is not a `(name, value)` pair, a `precision` that is not an
  `int`.
- `precision` accepts 0 to 20; a larger value raises `ServerTimingError` (a huge one
  raised a bare `ValueError` from the string formatter).
- `Metric.param` raises `TypeError` for a name that is not a `str` (it raised
  `AttributeError`).
- Parameter names are lowered in ASCII only: a name holding the Kelvin sign is no longer
  turned into `k` and written as if it were a token; `build` refuses it.
- `Metric` stores a list of parameters as a tuple, so the metric stays hashable.
- `Timing.measure` refuses a generator function with `TypeError` (calling one only
  creates the generator, so the time recorded was meaningless) and an object that is not
  callable; `Timing` refuses a `clock` that is not callable.
- Error messages quote at most a short excerpt of the value: a 100,000 character name no
  longer comes back whole, and an `int` duration too large for a float no longer raises a
  bare `ValueError` from `repr`.
- The public classes report `timingheader` as their module, so reprs and pickles never
  name a private module.
- The command reads response headers with many folded lines in linear time.

### Added

- Every public name has a docstring with a runnable example.

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
- `Metric` stores parameter names in lower case and an `int` duration as a `float`, so a
  metric equals what `parse` reads back from its serialization.

### Added

- `parse(header, strict=True)` checks values against the grammar with the sender rules
  (no empty list elements, no repeated parameter) and raises `ServerTimingError` with
  `field` and `position`.
- `parse` accepts several field values (headers then trailers).
- `Metric.params`, `Metric.param()`, `Metric.duration`, `Metric.description` and
  `str(metric)`.
- `build(..., precision=n)` and `Timing.header(precision=n)` round durations.
- `Timing.measure` decorates plain and `async` functions; `Timing.start` returns a `Timer`.
- The `timingheader` command shows and checks values from arguments or response headers.

## [0.1.0]

- First release: `build` and `parse` for the Server-Timing header, a `Metric` value
  type, and a `Timing` collector with a `measure` context manager.
