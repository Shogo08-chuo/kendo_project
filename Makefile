.PHONY: check test run setup-db

check:
	python3 -m py_compile app.py kendo_ai.py upload.py setup_db.py kendo_analyzer/*.py

test:
	python3 -m unittest discover -s tests

run:
	streamlit run app.py

setup-db:
	python3 setup_db.py
