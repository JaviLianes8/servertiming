# timingheader guide

The behaviour of every public name in detail. Each Python block below runs as a test: a
comment line after a `print` holds what it prints.

## Reading a header: `parse`

`parse(header, *, strict=False)` takes one field value (a `str`) or an iterable of them,
headers first and trailers after, and returns a list of `Metric`. Several values are
joined with `", "` before they are read, as the Fetch standard does. A value that is not
a `str` raises `TypeError`; decode header bytes as ISO-8859-1 first.

**Default: what browsers read, as the web-platform-tests corpus pins it down.** It
never raises on text. It follows the corpus and the rules in the prose of the W3C spec;
where the step-by-step algorithm of the spec's Editor's Draft disagrees with the corpus,
the corpus wins (see [the Editor's Draft algorithm](#the-editors-draft-algorithm)).

- A metric name is a token (RFC 9110 5.6.2). An entry that does not start with one
  (`[x]`, `"q"`, an empty list element) is skipped up to the next comma.
- Characters after a name or a value, up to the next `;` or `,`, are ignored; a quoted
  string inside them is skipped whole, so a comma inside it does not end the metric.
- Parameter names compare without regard to ASCII case and are stored in lower case.
- The first occurrence of a parameter wins, even when it is empty or invalid.
- A value is a token or a quoted string; a quoted string that never closes reads as
  empty.
- `dur` is read with the HTML rules for floating-point numbers (below); `desc` is kept as
  read. Any other parameter is kept, in order, in `Metric.params`.
- Values are checked as plain `str` text: a `str` subclass is read, and written by
  `build`, as its real characters, whatever its own iteration or formatting shows.

```python
from timingheader import parse

for metric in parse('db junk;DUR=12ms;dur=99;desc="a, b" x, [x], cdn;hit=1;dur=-'):
    print(metric.name, metric.dur, metric.desc, metric.params)
# db 12.0 a, b ()
# cdn None None (('hit', '1'),)
```

**`strict=True`: the grammar, with the sender rules.** Each field value must match
`#server-timing-metric` of the W3C spec exactly, with RFC 9110 tokens, quoted strings
and optional whitespace. On top of the grammar: no empty list element (RFC 9110 5.6.1.1),
no parameter given twice (names compared without case), and `dur` a valid floating-point
number that a double can hold (`1e400` is refused). Spaces and tabs around the whole
value are allowed. An empty value is a list with no elements. The first error raises
`ServerTimingError` with `field` (the index of the value) and `position` (the index of
the first offending character in it). When it passes, the result equals the default
reading.

```python
from timingheader import ServerTimingError, parse

for value in ["a;dur=1;DUR=2", "a,,b", 'a;desc="open', "a;dur=1e400"]:
    try:
        parse(["ok", value], strict=True)
    except ServerTimingError as error:
        print(error.field, error.position, error.message)
# 1 8 parameter 'dur' is repeated at position 8 (found 'D')
# 1 2 empty list element at position 2 (found ',')
# 1 7 unterminated quoted string at position 7 (found '"')
# 1 6 dur is not a valid floating-point number at position 6 (found '1')
```

## Durations

`dur` follows the HTML "rules for parsing floating-point number values": leading ASCII
whitespace is skipped, a leading `+` is ignored, `.5` and `1.` are numbers, anything
after the number is ignored, the result is the nearest double, `-0` reads as `0`, and a
value too large for a double is an error. An error, or no `dur` at all, gives `None`;
`Metric.duration` turns that into the `0` a browser shows.

```python
from timingheader import parse

print([parse(f"a;dur={text}")[0].dur for text in ["12ms", "+5", ".5", "1.5.2", "-0", "1e400", "x"]])
# [12.0, 5.0, 0.5, 1.5, 0.0, None, None]
```

## Building a header: `build` and `str(metric)`

`build(metrics, *, precision=None)` joins metrics with `", "`; `str(metric)` writes one.
Each metric is written as `name;dur=...;desc=...` followed by its other parameters in
order. A value that is a token is written bare, anything else as a quoted string with
`"` and `\` escaped. Durations are written in the shortest form that reads back as the
same double (`100`, `0.1`, `1e-05`); `precision` (an int from 0 to 20) rounds them to
that many decimal places. Whatever `build` writes, strict `parse` reads back as the same
metrics.

`build` raises `ServerTimingError` for a value it cannot write safely: a name or
parameter name that is not a token, a description or parameter value holding a
character no quoted string can carry (controls other than tab, DEL, anything above
U+00FF), a duration that is not finite, a parameter named `dur` or `desc` (they belong in
the fields), a parameter given twice, a `precision` out of range. It raises `TypeError`
for an argument of the wrong type: a single `Metric` or a `str` instead of an iterable, an
item that is not a `Metric`, a part that is not a `str`, a duration that is not an `int`
or a `float` (a `bool` included), a parameter that is not a `(name, value)` pair.

```python
from timingheader import Metric, ServerTimingError, build

print(build([Metric("cdn", 0.1, 'say "hi"', (("Pop", "MAD 1"),))], precision=3))
# cdn;dur=0.1;desc="say \"hi\"";pop="MAD 1"
for bad in [Metric("db", desc="caf☃"), Metric("db", params=(("dur", "1"),))]:
    try:
        build([bad])
    except ServerTimingError as error:
        print(error)
# description holds '☃' at index 3, which no HTTP field value can carry
# parameter 'dur' belongs in Metric.dur or Metric.desc
```

## The `Metric` value

A frozen dataclass with `name`, `dur`, `desc` and `params`. Construction checks nothing,
because `parse` must be able to return what a browser keeps; `build` checks. It does
normalise: an `int` duration is stored as a `float`, parameter names are lowered in
ASCII only, and a list of parameters becomes a tuple, so a metric equals what `parse`
reads back from its serialization and stays hashable. `duration` and `description` give
the browser view; `param(name)` looks a parameter up without regard to case and raises
`TypeError` for a name that is not a `str`.

## Recording: `Timing`, `Measure` and `Timer`

`Timing(clock=time.perf_counter)` collects metrics. `clock` returns seconds; durations
are recorded in milliseconds. Every method checks the name and description at the call
(`ServerTimingError` or `TypeError`, as `build` would), so nothing invalid is ever
recorded. Recording is safe from several threads; `metrics` returns a copy in the order
the metrics finished, and `header(precision=None)` builds them.

- `add(name, dur=None, desc=None)` records a metric with a known duration.
- `measure(name, desc=None)` returns a `Measure`. As a context manager it times the
  block and records even when the block raises; one `Measure` may be entered again,
  nested, or from several threads and asyncio tasks at once, and each entry records its
  own metric. As a decorator it times every call of a plain function, or every run of an
  `async` function up to its return. A generator function or an object that is not
  callable raises `TypeError`. A block must end in the thread or asyncio task that
  entered it: an exit with no matching entry there raises `RuntimeError`. Running blocks
  are held in one context variable shared by every `Measure`, so a long-lived thread does
  not grow with the number of requests it serves.
- `start(name, desc=None)` returns a `Timer`; `stop()` records it and returns the metric,
  and a second `stop()` raises `RuntimeError`. `running` says whether it is still going.
- A clock reading that makes a duration infinite or NaN raises `ServerTimingError` where
  the block, the call or the timer ends, and nothing is recorded for it, so the other
  metrics still build.
- `Measure(timing, name, desc)` and `Timer(timing, name, desc, start)` can be built
  directly; they check `timing`, the name and the description as the methods do, and
  `start` must be an `int` or a `float` from the timing's clock.

```python
import asyncio
import itertools

from timingheader import Timing

ticks = itertools.count(0.0, 0.004)
timing = Timing(clock=lambda: next(ticks))
step = timing.measure("step")
with step, step:
    pass


@timing.measure("fetch")
async def fetch() -> int:
    await asyncio.sleep(0)
    return 200


print(asyncio.run(fetch()), timing.header())
# 200 step;dur=4, step;dur=12, fetch;dur=4
```

## Errors

`ServerTimingError` is a `ValueError` with `message`, `position` and `field`; the last two
are `None` unless the error comes from strict parsing. It pickles with all three. Every
message, of this error and of the `TypeError`s above, quotes at most a short excerpt of
the offending value, so a huge or hostile input never comes back whole.

## Command line

`timingheader [--json] [VALUE ...]` prints the metrics of the values (a table, or JSON with
`name`, `dur`, `desc` and `params`), then checks each value in strict mode and prints one
line per invalid value on stderr. Exit status: 0 when every value is valid, 1 when one is
not, 2 when there is no value; blank arguments are dropped, and an invalid value is
numbered by its place on the command line. With no argument it reads stdin as
ISO-8859-1: bare values one per line, or, when a line looks like a status line or a
header (`HTTP/...`, `Name:`), only the `Server-Timing` fields, folded continuation lines
included. A status line starts a new response, and only the fields of the last response
are used (`curl -sIL` prints every redirect), as a browser exposes only the final
response. `--json` escapes every character outside ASCII (`"caf\u00e9"`), so the output
stays valid JSON on any console. A reader that closes the output early (`| head`) ends
the output quietly; the exit status still says whether the values are valid.

## Browsers

Real engines were driven over HTTP on 2026-10-20 (`tests/test_browsers.py`): Google
Chrome 155, Firefox 158 and the WebKit build of Playwright 1.64. On 3,000 generated
headers that follow the grammar, each engine exposed exactly what `parse` gives, and
Chrome and Firefox read the whole web-platform-tests corpus as `parse` does. On malformed
text they differ from one another; `parse` follows the web-platform-tests corpus and
the HTML number rules:

| Value | `parse` | Chrome | WebKit | Firefox |
| --- | --- | --- | --- | --- |
| `a,,b` | `a`, `b` | `a` | `a` | `a`, `b` |
| `[x], b` | `b` | nothing | nothing | `b` |
| `a;=1, b` | `a`, `b` | `a` | `a` | `a`, `b` |
| `a;;dur=1` | `a` 1 | `a` 0 | `a` 0 | `a` 1 |
| `a=1, b` | `a`, `b` | `a`, `b` | `a` | `a`, `b` |
| `a;dur=12ms` | 12 | 0 | 12 | 0 |
| `a;dur=1e309` | 0 | infinity | infinity | 0 |
| `a;dur=-0` | 0 | -0 | -0 | -0 |

Also: WebKit exposes only the last of several `Server-Timing` fields in one response and
misreads two corpus cases (`metric==   ""foo;dur=123.4` and `metric1==   ""foo,metric2`),
and Firefox decodes characters U+0080 to U+00FF in a value as UTF-8 (so `café` shows a
replacement character) where the others, and `parse`, read them as ISO-8859-1.

## The Editor's Draft algorithm

The W3C Editor's Draft (`index.bs` at commit 573ee35, read on 2026-10-20) defines "parse a
server-timing header field", run on each element after Fetch splits the value on commas
outside quotes. It differs from the web-platform-tests corpus, and so from `parse`, on
malformed values (35 of the 85 corpus cases):

- The name is all the text up to the first `;`, not a token: `a=1, b` gives the names
  `a=1` and `b`, and `[x], b` gives `[x]` and `b`. `parse` gives `a`, `b` and `b`.
- Parameter names are compared with their case: `a;Dur=5` has no `dur`, so its duration
  is 0. `parse` gives 5.
- An unquoted value runs to the next `;` and keeps its spaces: `cache;desc=d1 d2` gives
  `d1 d2`. `parse` gives `d1`.
- An empty parameter before `dur` turns it into a parameter named `;dur`: `a;;dur=1` has
  duration 0 (Chrome and WebKit agree). `parse` gives 1, as Firefox does.

Where they conflict, `parse` follows the corpus, which the browsers were measured to share
on every value that follows the grammar.
