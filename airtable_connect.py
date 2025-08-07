from pyairtable import Api
import os
import config  

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

api = Api(AIRTABLE_API_KEY)
base = api.base(BASE_ID)

try:
    # Get the schema of the entire base
    base_schema = base.schema()
    
    print(f"Schemas for all tables in base '{BASE_ID}':")
    for table_schema in base_schema.tables:
        print(f"\n--- Table: {table_schema.name} (ID: {table_schema.id}) ---")
        print(f"Primary Field ID: {table_schema.primary_field_id}")
        print("Fields:")
        for field in table_schema.fields:
            print(f"  - {field.name} (ID: {field.id}, Type: {field.type})")
        print("Views:")
        for view in table_schema.views:
            print(f"  - {view.name} (ID: {view.id}, Type: {view.type})")

except Exception as e:
    print(f"Failed to retrieve schemas for base '{BASE_ID}': {e}")