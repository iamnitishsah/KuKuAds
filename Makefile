.PHONY: install test run serve
install:
	pip install -r requirements.txt
test:
	python -m pytest -q
run:            ## make run SCRIPTS="path/to/screenplays"
	python run.py --scripts "$(SCRIPTS)"
serve:
	PYTHONPATH=src uvicorn promofinder.api.main:app --port 8000
