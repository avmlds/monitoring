VENV = '.venv'
BIN = '${VENV}/bin'
PIP = '${BIN}/pip'
PYTHON = '${BIN}/python3.12'


all: venv install-src install-dev-tools ruff mypy coverage clean

check: venv install-dev-tools ruff mypy
format: ruff mypy
install: venv install-src
reinstall: reinstall-src
coverage: coverage-report html-coverage

.PHONY: venv
venv:
	python3.12 -m venv .venv
	'${PIP}' install --upgrade pip

.PHONY: install-dev-tools
install-dev-tools:
	'${PIP}' install ruff==0.3.5
	'${PIP}' install mypy==1.9.0
	'${PIP}' install pytest==8.1.1 pytest-asyncio==0.23.6
	'${PIP}' install coverage==7.4.3

.PHONY: install-src
install-src:
	'${PIP}' install ./src/

.PHONY: reinstall-src
reinstall-src:
	'${PIP}' install ./src/ --force-reinstall


.PHONY: ruff
ruff:
	'${BIN}/ruff' check src --fix
	'${BIN}/ruff' format src
	'${BIN}/ruff' check src/cli/monitor --fix
	'${BIN}/ruff' format src/cli/monitor

.PHONY: mypy
mypy:
	'${PYTHON}' -m mypy src/monitoring --config-file pyproject.toml

.PHONY: test
test:
	'${BIN}/pytest' -vv src/tests

.PHONY: coverage-report
coverage-report:
	'${PYTHON}' -m coverage run --source src -m pytest -vv src/tests/
	'${PYTHON}' -m coverage report --show-missing --omit=setup.py,src/tests/*

.PHONY: html-coverage
html-coverage:
	'${PYTHON}' -m coverage html  --skip-empty --skip-covered --omit=setup.py,src/tests/*

.PHONY: clean
clean:
	rm -rf .venv */*.egg-info .mypy_cache .ruff_cache src/build .pytest_cache htmlcov .coverage
