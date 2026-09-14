import json

import requests

from src.config import settings
from src.domain.schemas import PropertyAnalysis, PropertyInput
from src.utils.geocoder import get_coordinates
from src.utils.logger import get_logger


class MondayClient:
    def __init__(self):
        self.api_key = settings.MONDAY_API_KEY
        self.api_url = "https://api.monday.com/v2"
        self.logger = get_logger("monday_client")

    def create_item(self, prop: PropertyInput, analysis: PropertyAnalysis, board_id: int = 18396329631) -> bool:
        """
        Creates an item on the Monday board with the analysis results.
        If no API key is present, it logs the mutation (Dry Run).
        """
        
        # 1. Escape values to avoid breaking GraphQL string
        # Simple JSON dumps ensures strings are properly escaped
        def escape_gql(val):
            return json.dumps(val)

        # 2. Prepare Column Values (JSON String)
        # Using JSON dump for the entire column_values object is safer and cleaner
        # Maps keys to placeholders for now. Will be updated with real IDs after discovery.
        
        # Map ActionEnum to Monday Status Labels (Case Sensitive)
        status_map = {
            "BUY": "Buy",
            "PASS": "Pass",
            "INVESTIGATE": "AI Reviewing" 
        }
        monday_status = status_map.get(analysis.recommended_action.value, "New")

        gql_column_values = json.dumps({
            "numeric_mkzsm1z3": str(prop.price),       # Asking Price
            "numeric_mkzshdqc": str(analysis.arv),     # Calculated ARV
            "numeric_mkzsa9d": str(analysis.renovation_cost), # Est. Reno Cost
            "numeric_mkzs5evh": analysis.viability_score, # Viability Score
            "color_mkzs8dn0": monday_status,           # AI Decision - Buy/Pass
            "long_text_mkzsthq0": analysis.summary,    # Executive Summary
            "link_mkzsdbc0": {"url": str(prop.link), "text": "Zillow Listing"}, # Zillow Listing
            "location_mkzsssmr": get_coordinates(prop.address) # Location (Lat/Lng/Address)
        }).replace('"', '\\"') # Escape quotes for inclusion in the mutation string

        mutation = f"""
        mutation {{
            create_item (
                board_id: {board_id},
                item_name: {escape_gql(prop.address)},
                column_values: "{gql_column_values}"
            ) {{
                id
            }}
        }}
        """

        # Step 2: Execution Guard (The Switch)
        if not self.api_key:
            self.logger.warning("MONDAY_API_KEY not found. DRY RUN - Payload prepared but not sent.")
            self.logger.info(f"GraphQL Mutation:\n{mutation}")
            return True

        # Else (Live Mode)
        headers = {
            "Authorization": self.api_key,
            "API-Version": "2023-10",
            "Content-Type": "application/json"
        }
        
        data = {'query': mutation}
        
        try:
            response = requests.post(self.api_url, json=data, headers=headers)
            response.raise_for_status()
            
            response_json = response.json()
            if "errors" in response_json:
                self.logger.error(f"Monday API returned errors: {response_json['errors']}")
                return False
                
            self.logger.info(f"Item created on board {board_id}. ID: {response_json['data']['create_item']['id']}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create item on Monday: {e}")
            return False
