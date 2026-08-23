## Description

What changed and why. Link issue if any.

## Type

- [ ] Data fix (`data/csv/`)
- [ ] Tooling (`scripts/`)
- [ ] Docs (`README`, `schema.md`, `docs/`)

## Testing done

- [ ] `python scripts/build.py`
- [ ] `python scripts/build.py --check`
- [ ] `python -m pytest tests/test_route.py -q`
- [ ] `python scripts/bsd.py --halte THE_BREEZE` / `--scenario`

## Checklist

- [ ] `data/json` not hand-edited (derived)
- [ ] `ruff check` + `black --check` + `mypy` green (see `pyproject.toml`)
- [ ] `pre-commit run --all-files` green
- [ ] `publish --check` green if `dist` touched
