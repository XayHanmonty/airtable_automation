import json
from pyairtable import Api
import os
import config
from datetime import datetime
from llm_enrichment import enrich_applicant_with_llm

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Table names
TABLE_APPLICANTS = "Applicants"
TABLE_PERSONAL = "Personal Details"
TABLE_WORK = "Work Experience"
TABLE_SALARY = "Salary Preferences"
TABLE_SHORTLIST = "Shortlisted Leads"

api = Api(AIRTABLE_API_KEY)

# Reference each table
applicants_table = api.table(BASE_ID, TABLE_APPLICANTS)
personal_table = api.table(BASE_ID, TABLE_PERSONAL)
work_table = api.table(BASE_ID, TABLE_WORK)
salary_table = api.table(BASE_ID, TABLE_SALARY)
shortlist_table = api.table(BASE_ID, TABLE_SHORTLIST)

def compress_applicant_data(applicant_id):
    # Get personal details
    personal_records = personal_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
    personal_data = {}
    if personal_records:
        record = personal_records[0]['fields']
        personal_data = {
            "name": record.get("Full Name", ""),
            "email": record.get("Email", ""),
            "location": record.get("Location", ""),
            "linkedin": record.get("LinkedIn", "")
        }

    # Get work experience 
    work_records = work_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
    work_data = []
    for record in work_records:
        fields = record['fields']
        work_data.append({
            "company": fields.get("Company", ""),
            "title": fields.get("Title", ""),
            "start": fields.get("Start Date", ""),
            "end": fields.get("End Date", ""),
            "technologies": fields.get("Technologies Used", "")
        })

    # Get salary preferences
    salary_records = salary_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
    salary_data = {}
    if salary_records:
        record = salary_records[0]['fields']
        salary_data = {
            "preferred_rate": record.get("Preferred Rate", ""),
            "min_rate": record.get("Minimum Rate", ""),
            "currency": record.get("Currency", ""),
            "availability": record.get("Availability (hrs/wk)", "")
        }

    # Build final JSON object
    compressed_json = {
        "personal": personal_data,
        "experience": work_data,
        "salary": salary_data
    }

    # Write JSON to Applicants table
    applicant_records = applicants_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
    if not applicant_records:
        print(f"No applicant found with ID: {applicant_id}")
        return

    applicant_record_id = applicant_records[0]['id']

    # Upload compressed JSON
    applicants_table.update(applicant_record_id, {
        "Compressed JSON": json.dumps(compressed_json)
    })

    print(f"Compressed JSON written for Applicant ID: {applicant_id}")
    print(json.dumps(compressed_json, indent=2))

    # Enrich with LLM
    enrich_applicant_with_llm(applicant_record_id)

if __name__ == "__main__":
    # accept as CLI input
    applicant_id = input("Enter Applicant ID: ").strip()
    compress_applicant_data(applicant_id)
