install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

test:
	pytest -q

demo:
	python scripts/demo_rate_limit.py

lint:
	python -m compileall app tests scripts
