all: quality coverage

tests:
	coverage run `which django-admin.py` test --settings test_settings django_sirene

coverage: tests
	coverage report -m

quality:
	flake8
