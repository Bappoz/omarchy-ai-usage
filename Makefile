.PHONY: test lint validate check

test:
	python -m unittest discover -s tests -v

validate:
	omarchy plugin validate .

lint:
	ruff check helpers tests
	find src -name '*.qml' -print0 | xargs -0 -n1 qmllint

check: test lint validate
