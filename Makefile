.PHONY: install test run app selftest
install:
	pip install -r requirements.txt
test:
	python -m pytest -q
selftest:       ## offline check of the pipeline code, no LLM or key needed
	python run.py --selftest
run:            ## make run SCRIPTS="path/to/screenplays"
	python run.py --scripts "$(SCRIPTS)"
app:
	streamlit run app.py
