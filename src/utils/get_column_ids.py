import os
import sys

import requests

# Ensure src module is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.monday import MondayClient


def get_column_ids():
    client = MondayClient()
    
    if not client.api_key:
        print("Error: MONDAY_API_KEY not found in environment variables.")
        return

    board_id = 18396329631
    query = f"""
    query {{
        boards (ids: {board_id}) {{
            columns {{
                id
                title
            }}
        }}
    }}
    """

    headers = {
        "Authorization": client.api_key,
        "API-Version": "2023-10",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(client.api_url, json={'query': query}, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if "errors" in data:
            print(f"Error querying Monday.com: {data['errors']}")
            return

        if not data.get("data") or not data["data"].get("boards"):
             print("No board found or empty response.")
             return

        columns = data["data"]["boards"][0]["columns"]
        
        print(f"\n{'='*40}")
        print(f"COLUMN MAPPING FOR BOARD ID: {board_id}")
        print(f"{'='*40}\n")
        print(f"{'COLUMN ID':<20} | {'COLUMN TITLE'}")
        print("-" * 40)
        
        for col in columns:
            print(f"{col['id']:<20} | {col['title']}")
            
        print("\n" + "="*40)
        print("INSTRUCTIONS: Update src/services/monday.py with these IDs.")

    except Exception as e:
        print(f"Failed to fetch columns: {e}")

if __name__ == "__main__":
    get_column_ids()
