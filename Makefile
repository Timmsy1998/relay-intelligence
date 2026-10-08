.PHONY: up down seed test lint evaluate
up:
	docker compose up -d --build --wait
down:
	docker compose down
seed:
	docker compose exec api python scripts/seed.py
test:
	.venv/bin/pytest -q
	cd frontend && npm test
lint:
	.venv/bin/ruff check backend scripts
	.venv/bin/ruff format --check backend scripts
	cd frontend && npm run format:check
evaluate:
	.venv/bin/python scripts/evaluate.py
