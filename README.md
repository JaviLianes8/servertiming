# timingheader

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Build, parse and validate the HTTP `Server-Timing` header, with timing helpers for
recording metrics during a request.

The `Server-Timing` header carries server-side metrics (`db;dur=53, cache;desc="Cache
Read"`) that browsers show in their developer tools and expose to scripts. Writing it by
string concatenation is easy to get wrong: a description with a quote breaks the header,
one with a line break splits the response. Reading it back is harder still: the header
has a grammar, a browser parsing algorithm and number rules of its own. `timingheader`
does both, plus a strict check for what you are about to send.

## Install

```
pip install timingheader
```

Python 3.10 or newer, no dependencies.

## Usage

Build a header value from metrics. Durations are milliseconds by convention:

```python
from timingheader import Metric, build

header = build(
    [
        Metric("db", dur=53, desc="primary"),
        Metric("cache", dur=0.75, desc="Cache Read"),
        Metric("cdn", params=(("hit", "1"),)),
    ]
)
print(header)
# db;dur=53;desc=primary, cache;dur=0.75;desc="Cache Read", cdn;hit=1
```

The builder never writes a header that could split the response. A name must be a token,
and a description holding CR, LF or another control character raises `ServerTimingError`
(a `ValueError`); an argument of the wrong type raises `TypeError`. Characters U+0080 to
U+00FF are allowed inside quotes, as RFC 9110 permits, and reach the client correctly
only when your framework encodes headers as ISO-8859-1 (WSGI and ASGI do); keep
descriptions to ASCII if you are unsure. Parameter names are case-insensitive and are
stored and written in lower case:

```python
from timingheader import Metric, ServerTimingError, build

try:
    build([Metric("db", desc="ok\r\nSet-Cookie: session=stolen")])
except ServerTimingError as error:
    print(error)
# description holds '\r' at index 2, which no HTTP field value can carry
print(build([Metric("db", dur=12.3456)], precision=1))
# db;dur=12.3
```

Parse a header value the way the W3C specification says a browser must. Malformed text
never raises (only a value that is not a `str` does): the parser keeps every metric it
can and skips what the spec says to ignore. `dur` and `desc` are `None` when absent;
`duration` and `description` give the values a browser shows (`0` and `""`):

```python
from timingheader import parse

metrics = parse('db;dur=53;desc="primary", cache;desc=d1 d2, miss;dur=fast')
print([(m.name, m.dur, m.desc) for m in metrics])
# [('db', 53.0, 'primary'), ('cache', None, 'd1'), ('miss', None, None)]
print(metrics[2].duration, repr(metrics[2].description))
# 0.0 ''
```

A response can carry several `Server-Timing` fields, including trailers sent after the
body. Pass them together, headers first, and they are read as one list:

```python
from timingheader import parse

fields = ["miss, db;dur=53", 'cache;desc="Cache Read";dur=23.2', "total;dur=123.4"]
print([m.name for m in parse(fields)])
# ['miss', 'db', 'cache', 'total']
```

Check a header before sending it with `strict=True`. Each field must follow the grammar
exactly with the sender rules: no empty list elements (`a,,b`), a parameter only once,
and `dur` a valid number. The error carries the field index and the position of the
first offending character:

```python
from timingheader import ServerTimingError, parse

try:
    parse("db;dur=53;desc=d1 d2", strict=True)
except ServerTimingError as error:
    print(error.field, error.position)
    print(error)
# 0 18
# expected ',' or ';' at position 18 (found 'd')
```

Record metrics while handling a request, then emit the header. `measure` times a block or
every call of a decorated function, plain or `async` (an `async` function is timed until
it returns, not just until the coroutine is created). `start` returns a timer for work
spread over callbacks. The clock is `time.perf_counter`, which is monotonic, and can be
replaced for tests:

```python
import itertools

from timingheader import Timing

ticks = itertools.count(0.0, 0.25)  # a fake clock that advances 250 ms per reading
timing = Timing(clock=lambda: next(ticks))
timing.add("cache", desc="miss")
with timing.measure("db", desc="query"):
    pass


@timing.measure("render")
def render() -> str:
    return "<html>"


render()
timer = timing.start("upload")
timer.stop()
print(timing.header())
# cache;desc=miss, db;dur=250;desc=query, render;dur=250, upload;dur=250
```

Names and descriptions are checked when recorded, so a bad one fails where it is written,
not when the response goes out. Recording is safe from several threads.

## Command line

`timingheader` shows the metrics in one or more values and exits with 1 when a value
breaks the grammar (2 when there is no value). With no arguments it reads stdin, one value
per line. When stdin holds response headers it uses only the `Server-Timing` fields
(folded continuation lines included) and ignores the rest, so a response without the
header exits with 2. `python -m timingheader` does the same:

```
$ curl -sI https://example.com/ | timingheader
$ timingheader 'db;dur=53, cache;desc="Cache Read";dur=23.2'
name    dur  desc
db       53
cache  23.2  'Cache Read'
$ timingheader --json 'db;desc=d1 d2'
```

## API

| Name | What it does |
| --- | --- |
| `build(metrics, *, precision=None)` | Serialize metrics into one header value, refusing unsafe input. |
| `parse(header, *, strict=False)` | Read one field value or several (headers then trailers) into metrics. |
| `Metric(name, dur=None, desc=None, params=())` | One metric. `duration`, `description`, `param(name)`, `str()`. |
| `Timing(clock=time.perf_counter)` | Collector: `add`, `measure`, `start`, `metrics`, `header(precision=None)`. |
| `Measure` | Returned by `Timing.measure`: a context manager and a decorator. |
| `Timer` | Returned by `Timing.start`: `stop()` records the metric, `running`. |
| `ServerTimingError` | `ValueError` with `position` and `field` for strict parsing errors. |

The [guide](https://github.com/JaviLianes8/timingheader/blob/main/GUIDE.md) describes every
rule in detail; the [changelog](https://github.com/JaviLianes8/timingheader/blob/main/CHANGELOG.md)
lists what changed.

## Standards and browsers

- [W3C Server Timing](https://w3c.github.io/server-timing/): the header grammar, the
  first occurrence of a parameter wins, characters after a name or a value up to the next
  `;` or `,` are ignored, `dur` and `desc` with their defaults.
- [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) 5.6: tokens, quoted strings, optional
  whitespace, and the list rule (the lenient parser skips empty elements as a recipient
  must; strict mode rejects them as a sender must not write them).
- [HTML](https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#rules-for-parsing-floating-point-number-values):
  `dur` is read with the rules for parsing floating-point number values, so `12ms` reads
  as 12, `+5` as 5 and `1e400` as no duration. Strict mode asks for a valid floating-point
  number that a double can hold.
- [Fetch](https://fetch.spec.whatwg.org/): repeated fields are joined with `, ` before
  parsing.

The lenient parser passes the 85 cases of the web-platform-tests corpus. Real browsers
were checked too, by sending the headers to them over HTTP: Chrome 155, Firefox 158 and
WebKit expose exactly what `parse` gives for thousands of generated headers that follow
the grammar, and Chrome and Firefox for the whole corpus. On malformed text the browsers
disagree with one another and with the spec (Chrome and WebKit stop at an empty list
element, Chrome and Firefox read `12ms` as no duration); `parse` follows the spec there.
The [guide](https://github.com/JaviLianes8/timingheader/blob/main/GUIDE.md#browsers)
lists every difference measured.

## Why

The Python packages for this header write it and nothing else, and each is tied to one
web framework: `flask-server-timing` (last release 2018), `django-server-timing` and
`aioservertiming` (aiohttp). None of them parses a header, and none escapes a quote in a
description, so a description with a `"` produces a broken header. The project named
`server-timing` on PyPI is an empty 0.0.1 package from 2018. `timingheader` is
standalone, typed and has no dependencies: it builds a safe header, reads one back as the
specification says, validates it, and offers a small collector.

## Development

`python scripts/fetch_upstream.py` downloads the web-platform-tests corpus and the
specifications listed in `tests/upstream/MANIFEST.json` (they are not part of the
repository; their tests skip without them). `scripts/check.ps1` runs format, lint, types
and tests. `TIMINGHEADER_E2E=1` also builds the wheel and tests the installed package and
command; `TIMINGHEADER_BROWSERS=1` (with `pip install playwright`) checks the parser
against real browsers.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/timingheader/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
