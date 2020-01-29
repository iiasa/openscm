.PHONY: black checks check-docs clean clean-notebooks coverage docs format test test-all
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

black: venv  ## apply black formatter to source and tests
	@status=$$(git status --porcelain openscm tests); \
	if test "x$${status}" = x; then \
		./venv/bin/black --exclude _version.py setup.py openscm tests; \
	else \
		echo Not trying any formatting. Working directory is dirty ... >&2; \
	fi;

checks: venv  ## run all the checks
	@echo "=== bandit ==="; ./venv/bin/bandit -c .bandit.yml -r openscm || echo "--- bandit failed ---" >&2; \
		echo "\n\n=== black ==="; ./venv/bin/black --check openscm tests setup.py --exclude openscm/_version.py || echo "--- black failed ---" >&2; \
		echo "\n\n=== flake8 ==="; ./venv/bin/flake8 openscm tests setup.py || echo "--- flake8 failed ---" >&2; \
		echo "\n\n=== isort ==="; ./venv/bin/isort --check-only --quiet --recursive openscm tests setup.py || echo "--- isort failed ---" >&2; \
		echo "\n\n=== mypy ==="; ./venv/bin/mypy openscm || echo "--- mypy failed ---" >&2; \
		echo "\n\n=== pydocstyle ==="; ./venv/bin/pydocstyle openscm || echo "--- pydocstyle failed ---" >&2; \
		echo "\n\n=== pylint ==="; ./venv/bin/pylint openscm || echo "--- pylint failed ---" >&2; \
		echo "\n\n=== notebook tests ==="; ./venv/bin/pytest notebooks -r a --nbval --sanitize tests/notebook-tests.cfg || echo "--- notebook tests failed ---" >&2; \
		echo "\n\n=== tests ==="; ./venv/bin/pytest tests -r a --cov=openscm --cov-report='' \
			&& ./venv/bin/coverage report --fail-under=100 || echo "--- tests failed ---" >&2; \
		echo "\n\n=== sphinx ==="; ./venv/bin/sphinx-build -M html docs docs/build -EW || echo "--- sphinx failed ---" >&2

check-docs: venv  ## check that the docs build successfully
	./venv/bin/sphinx-build -M html docs docs/build -En

clean:  ## remove the virtual environment
	@rm -rf venv

define clean_notebooks_code
	(.cells[] | select(has("execution_count")) | .execution_count) = 0 \
	| (.cells[] | select(has("outputs")) | .outputs[] | select(has("execution_count")) | .execution_count) = 0 \
	| .metadata = {"language_info": {"name": "python", "pygments_lexer": "ipython3"}} \
	| .cells[].metadata = {}
endef

clean-notebooks: venv  ## clean the notebooks of spurious changes to prepare for a PR
	echo "No notebooks at present"
# 	@tmp=$$(mktemp); \
# 	for notebook in notebooks/*.ipynb; do \
# 		jq --indent 1 '${clean_notebooks_code}' "$${notebook}" > "$${tmp}"; \
# 		cp "$${tmp}" "$${notebook}"; \
# 	done; \
# 	rm "$${tmp}"

coverage: venv  ## run all the tests and show code coverage
	./venv/bin/pytest tests -r a --cov=openscm --cov-report='' --durations=10
	./venv/bin/coverage html
	./venv/bin/coverage report --show-missing

docs: venv  ## build the docs
	./venv/bin/sphinx-build -M html docs docs/build

format: venv clean-notebooks  ## format the code and clean notebooks
	./venv/bin/isort --recursive openscm tests setup.py
	./venv/bin/black openscm tests setup.py --exclude openscm/_version.py

test: venv  ## run all the code tests
	./venv/bin/pytest -sx tests

test-notebooks: venv  ## run all notebook tests
	./venv/bin/pytest notebooks -r a --nbval --sanitize tests/notebook-tests.cfg

test-all: test test-notebooks  ## run the testsuite and the notebook tests

venv: setup.py  ## install a development virtual environment
	[ -d ./venv ] || python3 -m venv ./venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -e .[dev]
	touch venv
