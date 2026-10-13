# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/servertiming/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- `python scripts/fetch_upstream.py` downloads the web-platform-tests corpus into the
  ignored `tests/upstream/` folder (checked against `MANIFEST.json`); without it those
  tests skip. `SERVERTIMING_E2E=1 pytest tests/test_e2e_wheel.py` builds the wheel,
  installs it in a fresh virtual environment and drives the installed package.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
