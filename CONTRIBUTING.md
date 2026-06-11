# Contributing

Thanks for your interest in improving Ledgerly. This document
explains the development workflow.

## Development setup

```bash
git clone https://github.com/<your-user>/ledgerly.git
cd ledgerly
make install        # creates venv and installs runtime deps
make dev            # installs dev tools and pre-commit hooks
make run            # starts uvicorn on :8000
```

On Windows without `make`, use the underlying commands directly:

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements-dev.txt
.\venv\Scripts\pre-commit install
.\venv\Scripts\uvicorn main:app --reload
```

## Running quality checks

```bash
make test           # pytest
make test-cov       # pytest with coverage report
make lint           # ruff check + format check
make format         # auto-fix lint and apply formatting
```

CI runs the same commands on every push and pull request.

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add /api/preview endpoint`
- `fix: prevent rounding drift on tax calculations`
- `refactor: split build_pdf into helpers`
- `docs: document Fly.io deployment`
- `test: cover quote without due date`
- `chore: bump ruff to 0.4.4`

## Pull requests

1. Fork and create a feature branch from `main`.
2. Add or update tests for any behavior change.
3. Make sure `make lint` and `make test` pass locally.
4. Update `CHANGELOG.md` under `[Unreleased]` if the change is user-facing.
5. Open a PR using the template; fill out every section.

## Code style

- Type hints on every public function.
- Prefer `Decimal` for any monetary value; never use `float`.
- Keep functions small. If a function exceeds ~40 lines, split it.
- Public modules document themselves with a short docstring at the top.

## Reporting bugs / suggesting features

Open an issue using the corresponding template. Provide reproduction steps
and the smallest possible payload that triggers the bug.
