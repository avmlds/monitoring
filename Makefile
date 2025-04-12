all: devel ruff mypy coverage clean

check: devel ruff mypy
format: ruff mypy
coverage: coverage-report html-coverage

.PHONY: devel
devel:
	uv sync -p3.12 --all-extras

.PHONY: ruff
ruff:
	uv run ruff check --fix
	uv run ruff format

.PHONY: mypy
mypy:
	uv run mypy monitoring

.PHONY: test
test:
	uv run pytest -vv tests

.PHONY: coverage-report
coverage-report:
	uv run python -m coverage run --source monitoring -m pytest -vv tests/
	uv run python -m coverage report --show-missing --omit=setup.py,tests/*

.PHONY: html-coverage
html-coverage:
	uv run python -m coverage html --skip-empty --skip-covered --omit=setup.py,tests/*

.PHONY: clean
clean:
	rm -rf .venv */*.egg-info .mypy_cache .ruff_cache build .pytest_cache htmlcov .coverage uv.lock
