import json
import os
from pyairtable import Api
import config
from datetime import datetime

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Table names
TABLE_APPLICANTS = "Applicants"
TABLE_SHORTLIST = "Shortlisted Leads"

api = Api(AIRTABLE_API_KEY)

# Reference each table
applicants_table = api.table(BASE_ID, TABLE_APPLICANTS)
shortlist_table = api.table(BASE_ID, TABLE_SHORTLIST)

# --- Shortlisting Criteria ---
TIER_1_COMPANIES = ["google", "meta", "openai", "amazon", "apple", "microsoft", "netflix"]
ALLOWED_LOCATIONS = ["us", "ca", "uk", "de", "in"] # USA, Canada, UK, Germany, India

def check_shortlist_criteria(applicant_id, applicant_record_id, compressed_json):
    reason = []

    # Experience Criterion
    experience_met = False
    total_experience_years = 0
    for exp in compressed_json.get("experience", []):
        start_year = int(exp["start"].split("-")[0]) if exp.get("start") else 0
        end_year = int(exp["end"].split("-")[0]) if exp.get("end") else 0
        total_experience_years += (end_year - start_year)

        company = exp.get("company", "").lower()
        if any(tier1 in company for tier1 in TIER_1_COMPANIES):
            experience_met = True
            reason.append(f"Worked at Tier-1 company: {exp.get("company")}")
            break # Only one Tier-1 company needed
    
    if total_experience_years >= 4:
        experience_met = True
        reason.append(f"Total experience of {total_experience_years} years")

    if not experience_met:
        return False, "Experience criteria not met."

    # Compensation Criterion
    salary_data = compressed_json.get("salary", {})
    preferred_rate = salary_data.get("preferred_rate")
    min_rate = salary_data.get("min_rate")
    availability = salary_data.get("availability")

    compensation_met = False
    if preferred_rate and preferred_rate <= 100 and availability and availability >= 20:
        compensation_met = True
        reason.append(f"Preferred rate ${preferred_rate}/hr and availability {availability} hrs/wk")
    elif min_rate and min_rate <= 100 and availability and availability >= 20:
        compensation_met = True
        reason.append(f"Minimum rate ${min_rate}/hr and availability {availability} hrs/wk")

    if not compensation_met:
        return False, "Compensation criteria not met."

    # Location Criterion
    location = compressed_json.get("personal", {}).get("location", "").lower()
    location_met = any(loc in location for loc in ALLOWED_LOCATIONS)

    if location_met:
        reason.append(f"Located in allowed region: {location}")
    else:
        return False, "Location criteria not met."

    return True, "; ".join(reason)


if __name__ == "__main__":
    all_applicants = applicants_table.all()
    for applicant in all_applicants:
        applicant_id = applicant['fields'].get('Applicant ID')
        applicant_record_id = applicant['id']
        compressed_json_str = applicant['fields'].get('Compressed JSON')

        if not compressed_json_str:
            print(f"Skipping applicant {applicant_id} - No Compressed JSON found.")
            continue

        try:
            compressed_json = json.loads(compressed_json_str)
        except json.JSONDecodeError:
            print(f"Skipping applicant {applicant_id} - Invalid JSON format.")
            continue

        is_shortlisted, score_reason = check_shortlist_criteria(applicant_id, applicant_record_id, compressed_json)

        if is_shortlisted:
            print(f"Applicant {applicant_id} shortlisted! Reason: {score_reason}")
            
            # Update Shortlist Status in Applicants table
            applicants_table.update(applicant_record_id, {"Shortlist Status": "Shortlisted"})

            existing_shortlist_records = shortlist_table.all()
            existing_shortlist_for_applicant = [rec for rec in existing_shortlist_records if rec.get('fields', {}).get('Applicant', [''])[0] == applicant_record_id]

            if existing_shortlist_for_applicant:
                # Update existing record
                shortlist_record_id = existing_shortlist_for_applicant[0]['id']
                shortlist_table.update(shortlist_record_id, {
                    "Compressed JSON": json.dumps(compressed_json),
                    "Score Reason": score_reason
                })
                print(f"  - Updated Shortlisted Lead for {applicant_id}")
            else:
                # Create new record
                shortlist_table.create({
                    "Applicant": [applicant_record_id],
                    "Compressed JSON": json.dumps(compressed_json),
                    "Score Reason": score_reason
                })
                print(f"  - Created new Shortlisted Lead for {applicant_id}")
        else:
            print(f"Applicant {applicant_id} not shortlisted. Reason: {score_reason}")
            # Update Shortlist Status in Applicants table
            applicants_table.update(applicant_record_id, {"Shortlist Status": "Not Shortlisted"})
