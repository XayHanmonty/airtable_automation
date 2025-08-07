.PHONY: all install-python airtable_connect compress_automation decompress_automation shortlist

install-python:
	pip3 install -r requirements.txt

airtable_connect:
	python3 airtable_connect.py

all:
	$(MAKE) compress_automation
	$(MAKE) decompress_automation
	$(MAKE) shortlist

compress_automation:
	python3 compress_json.py

decompress_automation:
	python3 decompress_json.py

shortlist:
	python3 shortlist_leads.py