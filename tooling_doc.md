# Airtable Applicant Tracking System Documentation

This document outlines the setup and functionality of the Airtable-based applicant tracking system. The system is designed to manage applicant data efficiently, using a combination of linked tables and Python scripts to automate data compression, decompression, lead shortlisting, and LLM-based enrichment.

## Setup

To set up the project, follow these steps:

1.  **Clone the repository:**

    ```bash
    https://github.com/XayHanmonty/airtable_automation.git
    cd airtable_automation
    ```

2.  **Create a virtual environment and install dependencies:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure environment variables:**

    Create a `.env` file in the root directory of the project based on `.env.example`. This file should contain your Airtable API key, Base ID, and OpenAI API key:

    ```
    AIRTABLE_API_KEY='YOUR_AIRTABLE_API_KEY'
    AIRTABLE_BASE_ID='YOUR_AIRTABLE_BASE_ID'
    OPENAI_API_KEY='YOUR_OPENAI_API_KEY'
    ```

    Replace the placeholder values with your actual keys and IDs.

## Airtable Base

[Airtable Base Link](https://airtable.com/invite/l?inviteId=invVLPbIzhum36vnn&inviteToken=fd20523d9a51a9758adc6858de18a2c63442bea85adebffcb78150bd8c64b327&utm_medium=email&utm_source=product_team&utm_content=transactional-alerts)

[Alternative view link](https://airtable.com/appAiGHWTSJ95CZJG/shreKdgv5XE9k5gQl)

## Makefile Usage

The `Makefile` provides convenient commands to automate various tasks:

-   `make install-python`: Installs Python dependencies from `requirements.txt`.
-   `make airtable_connect`: Runs the `airtable_connect.py` script.
-   `make compress_automation`: Runs the `compress_json.py` script to compress applicant data.
-   `make decompress_automation`: Runs the `decompress_json.py` script to decompress applicant data.
-   `make shortlist`: Runs the `shortlist_leads.py` script to shortlist leads.
-   `make all`: Runs `compress_automation`, `decompress_automation`, and `shortlist` in sequence.

## 1. Airtable Schema Setup

Create a base with three linked tables plus two helper tables:

| Table Name | Key Fields | Notes |
| :--- | :--- | :--- |
| **Applicants (parent)** | `Applicant ID` (primary), `Compressed JSON`, `JSON Hash`, `Shortlist Status`, `LLM Summary`, `LLM Score`, `LLM Follow-Ups` | Stores one row per applicant and holds the compressed JSON + LLM outputs |
| **Personal Details** | `Full Name`, `Email`, `Location`, `LinkedIn`, (linked to `Applicant ID`) | One-to-one with the parent |
| **Work Experience** | `Company`, `Title`, `Start`, `End`, `Technologies`, (linked to `Applicant ID`) | One-to-many |
| **Salary Preferences** | `Preferred Rate`, `Minimum Rate`, `Currency`, `Availability (hrs/wk)`, (linked to `Applicant ID`) | One-to-one |
| **Shortlisted Leads** | `Applicant` (link to Applicants), `Compressed JSON`, `Score Reason`, `Created At` | Auto-populated when rules are met |

**Note:** All child tables are linked back to `Applicants` by `Applicant ID`.



## 2. User Input Flow

Airtable’s native forms are used to collect applicant data. To simulate a multi-table input flow, three separate forms are used:

- **Personal Details Form:** Collects basic applicant information.
- **Work Experience Form:** Collects details about the applicant’s work history.
- **Salary Preferences Form:** Collects information about the applicant’s salary expectations and availability.

Each form either pre-fills or prompts for the `Applicant ID` to ensure all submitted data is linked to the correct applicant record in the `Applicants` table. Applicants are required to submit all three forms to complete their profile.

## 3. JSON Compression Automation

This script gathers data from the three linked tables, builds a single JSON object, and writes it to the `Compressed JSON` field in the `Applicants` table.

**Action:** Write a Python local script (`compress_json.py`) that:
- Gathers data from the `Personal Details`, `Work Experience`, and `Salary Preferences` tables.
- Builds a single JSON object in the specified format:

```json
{
  "personal": { "name": "Jane Doe", "location": "NYC" },
  "experience": [
    { "company": "Google", "title": "SWE" },
    { "company": "Meta",  "title": "Engineer" }
  ],
  "salary": { "rate": 100, "currency": "USD", "availability": 25 }
}
```
- Writes the JSON object to the `Compressed JSON` field in the corresponding `Applicants` record.

### Script Snippet (`compress_json.py`)
```python
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
    all_applicants = applicants_table.all()
    for applicant in all_applicants:
        applicant_id = applicant['fields'].get('Applicant ID')
        if applicant_id:
            compress_applicant_data(applicant_id)
```

## 4. JSON Decompression Automation

This script reads the `Compressed JSON` from an `Applicants` record and uses it to update records in the child tables (`Personal Details`, `Work Experience`, `Salary Preferences`).

**Action:** Write a separate Python local script (`decompress_json.py`) that can:
- Read `Compressed JSON`.
- Upsert child-table records so they exactly reflect the JSON state.
- Update look-ups/links as needed.

### Script Snippet (`decompress_json.py`)
```python
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
        existing_work_map = { (rec['fields']['Company'], rec['fields']['Title']): rec['id'] for rec in applicant_work_records }

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
            else:
                # Create new record
                work_data_mapped["Applicant ID"] = [applicant_id]
                work_table.create(work_data_mapped)

        # Delete any remaining records in the map (they were not in the JSON)
        for record_id in existing_work_map.values():
            work_table.delete(record_id)

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
```

## 5. Lead Shortlist Automation

After compression, evaluate rules:

| Criterion | Rule |
| :--- | :--- |
| **Experience** | ≥ 4 years total OR worked at a Tier-1 company (Google, Meta, OpenAI, etc.) |
| **Compensation** | Preferred Rate ≤ $100 USD/hour AND Availability ≥ 20 hrs/week |
| **Location** | In US, Canada, UK, Germany, or India |

If all criteria are met, create a `Shortlisted Leads` record and copy `Compressed JSON`. Populate `Score Reason` with a human-readable explanation.

### Script Snippet (`shortlist_leads.py`)
```python
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
                    "Score Reason": score_reason,
                    "Created At": datetime.now().isoformat()
                })
                print(f"  - Updated Shortlisted Lead for {applicant_id}")
            else:
                # Create new record
                shortlist_table.create({
                    "Applicant": [applicant_record_id],
                    "Compressed JSON": json.dumps(compressed_json),
                    "Score Reason": score_reason,
                    "Created At": datetime.now().isoformat()
                })
                print(f"  - Created new Shortlisted Lead for {applicant_id}")
        else:
            print(f"Applicant {applicant_id} not shortlisted. Reason: {score_reason}")
            # Update Shortlist Status in Applicants table
            applicants_table.update(applicant_record_id, {"Shortlist Status": "Not Shortlisted"})
```
## 6. LLM Evaluation & Enrichment
### 6.1 Purpose
Use OpenAI to automate qualitative review and sanity checks.
### 6.2 Technical Requirements

| Aspect | Requirement |
| :--- | :--- |
| **Trigger** | After `Compressed JSON` is written OR updated |
| **Auth** | Read API key from an Airtable Secret or env variable (do not hard-code) |
| **Prompt** | Feed the full JSON and ask the LLM to: <br> • Summarize the applicant in ≤ 75 words <br> • Assign a quality score from 1-10 <br> • Flag any missing / contradictory fields <br> • Suggest up to three follow-up questions |
| **Outputs** | Write to `LLM Summary`, `LLM Score`, `LLM Follow-Ups` fields on `Applicants` |
| **Validation** | If the API call fails, log the error and retry up to 3× with exponential backoff |
| **Budget Guardrails** | Cap tokens per call and skip repeat calls unless input JSON has changed |
### 6.3 Sample Prompt (pseudo-code)
```
You are a recruiting analyst. Given this JSON applicant profile, do four things:
1. Provide a concise 75-word summary.
2. Rate overall candidate quality from 1-10 (higher is better).
3. List any data gaps or inconsistencies you notice.
4. Suggest up to three follow-up questions to clarify gaps.

Return exactly:
Summary: <text>
Score: <integer>
Issues: <comma-separated list or 'None'>
Follow-Ups: <bullet list>
```
### 6.4 Expected Results
| Field | Example Value |
| :--- | :--- |
| `LLM Summary` | “Full-stack SWE with 5 yrs experience at Google and Meta…” |
| `LLM Score` | 8 |
| `LLM Follow-Ups` | • “Can you confirm availability after next month?”<br>• “Have you led any production ML launches?” |

### Script Snippet (`llm_enrichment.py`)
```python
import json
import os
import hashlib
import time
from pyairtable import Api
import openai
import config

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# Table names
TABLE_APPLICANTS = "Applicants"

api = Api(AIRTABLE_API_KEY)
applicants_table = api.table(BASE_ID, TABLE_APPLICANTS)

def generate_llm_response(prompt, retries=3, backoff_factor=0.5):
    for i in range(retries):
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",  # Or gpt-4, depending on budget/needs
                messages=[
                    {"role": "system", "content": "You are a recruiting analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except openai.APIError as e:
            print(f"OpenAI API error: {e}")
            if i < retries - 1:
                sleep_time = backoff_factor * (2 ** i)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                print("Max retries reached. Failing LLM call.")
                return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

def enrich_applicant_with_llm(applicant_id):
    applicant_record = applicants_table.get(applicant_id)
    if not applicant_record:
        print(f"Applicant with ID {applicant_id} not found.")
        return

    compressed_json_str = applicant_record['fields'].get('Compressed JSON')
    if not compressed_json_str:
        print(f"No Compressed JSON found for applicant {applicant_id}.")
        return

    current_json_hash = hashlib.md5(compressed_json_str.encode('utf-8')).hexdigest()
    stored_json_hash = applicant_record['fields'].get('JSON Hash')

    if current_json_hash == stored_json_hash:
        print(f"Compressed JSON for {applicant_id} has not changed. Skipping LLM enrichment.")
        return

    prompt = f"""
    You are a recruiting analyst. Given this JSON applicant profile, do four things:
    1. Provide a concise 75-word summary.
    2. Rate overall candidate quality from 1-10 (higher is better).
    3. List any data gaps or inconsistencies you notice.
    4. Suggest up to three follow-up questions to clarify gaps.

    Return exactly:
    Summary: <text>
    Score: <integer>
    Issues: <comma-separated list or 'None'>
    Follow-Ups: <bullet list>

    Applicant JSON: {compressed_json_str}
    """

    llm_response = generate_llm_response(prompt)

    if llm_response:
        summary = ""
        score = None
        issues = ""
        follow_ups = ""

        # Parse LLM response
        lines = llm_response.split('\n')
        parsing_follow_ups = False
        for line in lines:
            if line.startswith("Summary:"):
                summary = line.replace("Summary:", "").strip()
                parsing_follow_ups = False
            elif line.startswith("Score:"):
                try:
                    score = int(line.replace("Score:", "").strip())
                except ValueError:
                    score = None
                parsing_follow_ups = False
            elif line.startswith("Issues:"):
                issues = line.replace("Issues:", "").strip()
                parsing_follow_ups = False
            elif line.startswith("Follow-Ups:"):
                follow_ups = line.replace("Follow-Ups:", "").strip()
                parsing_follow_ups = True
            elif parsing_follow_ups:
                follow_ups += "\n" + line.strip()

        # Update Airtable record
        applicants_table.update(applicant_id, {
            "LLM Summary": summary,
            "LLM Score": score,
            "LLM Follow-Ups": follow_ups,
            "JSON Hash": current_json_hash
        })
        print(f"LLM enrichment completed for applicant {applicant_id}.")
    else:
        print(f"LLM enrichment failed for applicant {applicant_id}.")

if __name__ == "__main__":
    # Example usage: enrich a specific applicant
    # Replace with actual applicant ID from your Airtable base
    applicant_id_to_enrich = input("Enter Applicant Record ID to enrich: ").strip()
    enrich_applicant_with_llm(applicant_id_to_enrich)

```