.PHONY: install test app
install:
	pip install -r requirements.txt
test:
	python -m pytest -q
app:
	streamlit run app.py
