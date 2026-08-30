.PHONY: setup data check db-up db-down load test notebook

setup:
	python -m pip install -e ".[analysis,dev]"

data:
	python -m ai_saas_analytics.generator --profile small

check:
	python -m ai_saas_analytics.data_quality --input-dir data/generated

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

load:
	python -m ai_saas_analytics.loader --input-dir data/generated

test:
	python -m pytest

notebook:
	python scripts/create_starter_notebook.py --input-dir data/generated
