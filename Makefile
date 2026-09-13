PYTHON ?= .venv/bin/python

.PHONY: check test run migrate seed
check:
	$(PYTHON) scripts/compile_messages.py
	$(PYTHON) manage.py check
	$(PYTHON) manage.py makemigrations --check --dry-run
test:
	$(PYTHON) manage.py test
run:
	$(PYTHON) scripts/compile_messages.py
	$(PYTHON) manage.py runserver
migrate:
	mkdir -p data/db
	$(PYTHON) manage.py migrate
seed:
	@echo 'Seed: (none)'
