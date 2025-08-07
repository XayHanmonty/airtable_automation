import json
import os
from pyairtable import Api
import config

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Table names
TABLE_APPLICANTS = "Applicants"
TABLE_PERSONAL = "Personal Details"
TABLE_WORK = "Work Experience"
TABLE_SALARY = "Salary Preferences"

api = Api(AIRTABLE_API_KEY)

# Reference each table
applicants_table = api.table(BASE_ID, TABLE_APPLICANTS)
personal_table = api.table(BASE_ID, TABLE_PERSONAL)
work_table = api.table(BASE_ID, TABLE_WORK)
salary_table = api.table(BASE_ID, TABLE_SALARY)

def decompress_and_upsert_all():
    all_applicants = applicants_table.all()
    for applicant_record in all_applicants:
        applicant_id = applicant_record['id']
        compressed_json_str = applicant_record.get('fields', {}).get('Compressed JSON')

        if not compressed_json_str:
            print(f"Skipping applicant {applicant_id} - No Compressed JSON found.")
            continue

        try:
            compressed_data = json.loads(compressed_json_str)
        except json.JSONDecodeError:
            print(f"Skipping applicant {applicant_id} - Invalid JSON format.")
            continue

        print(f"Processing applicant {applicant_id}...")

        # Upsert Personal Details
        personal_data = compressed_data.get('personal', {})
        if personal_data:
            existing_personal = personal_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
            personal_data_mapped = {
                "Full Name": personal_data.get("name"),
                "Email": personal_data.get("email"),
                "Location": personal_data.get("location"),
                "LinkedIn": personal_data.get("linkedin")
            }
            if existing_personal:
                personal_table.update(existing_personal[0]['id'], personal_data_mapped)
                print(f"  - Updated Personal Details for {applicant_id}")

        # Upsert Work Experience
        work_data_list = compressed_data.get('experience', [])
        existing_work_records = work_table.all()

        # Filter records in Python
        applicant_work_records = [rec for rec in existing_work_records if rec.get('fields', {}).get('Applicant ID', [''])[0] == applicant_id]

        # Create a dictionary for quick lookups of existing records
        existing_work_map = {}
        for rec in applicant_work_records:
            company = rec['fields'].get('Company', '')
            title = rec['fields'].get('Title', '')
            existing_work_map[(company, title)] = rec['id']

        for work_data in work_data_list:
            work_key = (work_data.get("company"), work_data.get("title"))
            work_data_mapped = {
                "Company": work_data.get("company"),
                "Title": work_data.get("title"),
                "Start Date": work_data.get("start"),
                "End Date": work_data.get("end"),
                "Technologies Used": work_data.get("technologies")
            }

            if work_key in existing_work_map:
                # Update existing record
                record_id = existing_work_map.pop(work_key)
                work_table.update(record_id, work_data_mapped)
                print(f"  - Updated work experience for {work_data.get('company')}")
            else:
                # Create new record
                work_data_mapped["Applicant ID"] = [applicant_id]
                work_table.create(work_data_mapped)
                print(f"  - Created new work experience for {work_data.get('company')}")

        # Delete any remaining records in the map (they were not in the JSON)
        for record_id in existing_work_map.values():
            work_table.delete(record_id)
            print(f"  - Deleted stale work experience record {record_id}")


        # Upsert Salary Preferences
        salary_data = compressed_data.get('salary', {})
        if salary_data:
            salary_data_mapped = {
                "Preferred Rate": salary_data.get("preferred_rate"),
                "Minimum Rate": salary_data.get("min_rate"),
                "Currency": salary_data.get("currency"),
                "Availability (hrs/wk)": salary_data.get("availability")
            }
            existing_salary = salary_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
            if existing_salary:
                salary_table.update(existing_salary[0]['id'], salary_data_mapped)
                print(f"  - Updated Salary Preferences for {applicant_id}")

if __name__ == "__main__":
    decompress_and_upsert_all()