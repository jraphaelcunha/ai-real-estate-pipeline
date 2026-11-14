"""Monday.com Enterprise Work OS GraphQL integration with GIS broker dispatch."""

import json

import requests

from src.config import settings
from src.domain.schemas import PropertyAnalysis, PropertyInput
from src.utils.geocoder import assign_nearest_broker, get_coordinates
from src.utils.logger import get_logger


class MondayClient:
    """Dispatches underwritten deals and GIS broker routing payloads to Monday.com via GraphQL."""

    def __init__(self) -> None:
        self.api_key = settings.MONDAY_API_KEY
        self.api_url = "https://api.monday.com/v2"
        self.logger = get_logger("monday_client")

    def create_item(
        self,
        prop: PropertyInput,
        analysis: PropertyAnalysis,
        board_id: int | None = None,
    ) -> bool:
        """
        Create an item on the Monday.com Acquisitions Board with financial metrics,
        GIS coordinates, nearest-broker assignment, and conflict flags.
        Executes in dry-run logging mode when MONDAY_API_KEY is unset.
        """
        resolved_board_id = board_id if board_id is not None else settings.MONDAY_BOARD_ID
        coords = get_coordinates(prop.address)
        broker_summary = "Unassigned (Pending Geocoding)"
        if coords and isinstance(coords.get("lat"), float) and isinstance(coords.get("lng"), float):
            broker_name, distance_km = assign_nearest_broker(coords["lat"], coords["lng"])
            analysis.assigned_broker = broker_name
            broker_summary = f"{broker_name} ({distance_km:.1f} km from asset)"

        status_map = {
            "BUY": "Buy",
            "PASS": "Pass",  # nosec B105 - Monday.com status label, not a password
            "INVESTIGATE": "AI Reviewing",
        }
        monday_status = status_map.get(analysis.recommended_action.value, "New")

        recon_note = ""
        if analysis.reconciliation and not analysis.reconciliation.is_consistent:
            recon_note = " | CONFLICT ALERT: " + "; ".join(analysis.reconciliation.audit_notes)

        executive_notes = f"{analysis.summary} | Broker: {broker_summary}{recon_note}"

        gql_column_values = json.dumps(
            {
                "numeric_mkzsm1z3": str(prop.price),
                "numeric_mkzshdqc": str(analysis.arv),
                "numeric_mkzsa9d": str(analysis.renovation_cost),
                "numeric_mkzs5evh": analysis.viability_score,
                "color_mkzs8dn0": monday_status,
                "long_text_mkzsthq0": executive_notes,
                "link_mkzsdbc0": {"url": str(prop.link), "text": f"Deal Source ({prop.property_id})"},
                "location_mkzsssmr": coords,
            }
        ).replace('"', '\\"')

        mutation = f"""
        mutation {{
            create_item (
                board_id: {resolved_board_id},
                item_name: {json.dumps(prop.address)},
                column_values: "{gql_column_values}"
            ) {{
                id
            }}
        }}
        """

        if not self.api_key:
            self.logger.warning(
                "MONDAY_API_KEY not found. DRY RUN - Payload prepared for %s (%s).",
                prop.property_id,
                broker_summary,
            )
            self.logger.info("GraphQL Mutation:\n%s", mutation)
            return True

        headers = {
            "Authorization": self.api_key,
            "API-Version": "2023-10",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.api_url,
                json={"query": mutation},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            response_json = response.json()
            if "errors" in response_json:
                self.logger.error("Monday API returned errors: %s", response_json["errors"])
                return False

            created_id = response_json["data"]["create_item"]["id"]
            self.logger.info(
                "Item created on board %s. ID: %s | Assigned Broker: %s",
                resolved_board_id,
                created_id,
                broker_summary,
            )
            return True

        except requests.exceptions.RequestException as exc:
            self.logger.error("Failed to create item on Monday.com: %s", exc)
            return False
