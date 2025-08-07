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