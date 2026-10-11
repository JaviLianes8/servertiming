# servertiming

Build and parse the HTTP Server-Timing header, with a tiny collector for durations.

## Install

```
pip install servertiming
```

## Usage

Build a header value from metrics:

```python
from servertiming import Metric, build

build([
    Metric("app", dur=5.0, desc="application"),
    Metric("db", dur=12.3, desc="database query"),
])
# 'app;dur=5;desc=application, db;dur=12.3;desc="database query"'
```

Parse a header value back into metrics, tolerating malformed input:

```python
from servertiming import parse

parse('db;dur=12.3;desc="database query", cache')
# [Metric(name='db', dur=12.3, desc='database query'), Metric(name='cache', dur=None, desc=None)]
```

Collect metrics as work happens, then emit the header. The clock is injectable, so this
is easy to test:

```python
from servertiming import Timing

timing = Timing()
timing.add("app", desc="handler")
with timing.measure("db", desc="query"):
    run_query()

response_headers["Server-Timing"] = timing.header()
```

Durations are expressed in milliseconds, matching the header convention. `measure`
records the elapsed time of the block even if it raises.

## Why

The Server-Timing header surfaces server-side performance metrics in browser devtools,
but the Python options are framework-bound and write-only: `flask-server-timing`,
`django-server-timing` and `aioservertiming` each tie you to one web framework and none
of them parse. `server-timing-profiler` has not seen a release since 2018. This library
is standalone, typed and has zero dependencies: it builds a header, parses one back, and
offers a small collector, with nothing to pull in.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
