.PHONY= all clean
all: setup-poetry run-tests run-formatters

setup-poetry: check-poetry
	@poetry update

run-tests:
	sh ./scripts/run-tests.sh

run-formatters:
	@poetry run black ./ --line-length 120
	@poetry run isort ./

check-poetry:
	@command -v poetry &> /dev/null 2>&1 || exit

clean:
	find . -path "*/*.pyc"  -delete
