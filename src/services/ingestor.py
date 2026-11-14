import json
from pathlib import Path

from pydantic import ValidationError

from src.domain.schemas import PropertyInput
from src.services.interfaces import DataIngestor
from src.utils.logger import get_logger

logger = get_logger("json_ingestor")


class JsonFileIngestor(DataIngestor):
    """Concrete implementation of DataIngestor for structured deal package JSON feeds."""

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path).resolve()

    def load_properties(self) -> list[PropertyInput]:
        """
        Load properties from the configured JSON file.
        Includes fault tolerance to isolate and skip malformed records.
        """
        logger.info("Attempting to load properties from %s", self.file_path)

        if not self.file_path.exists():
            logger.error("File not found: %s", self.file_path)
            return []

        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.error("Invalid JSON format. Expected a list, got %s", type(data))
                return []

            properties: list[PropertyInput] = []

            for index, item in enumerate(data):
                try:
                    prop = PropertyInput(**item)
                    properties.append(prop)
                except ValidationError as exc:
                    logger.warning("Skipping invalid item at index %d: %s", index, exc)
                except Exception as exc:
                    logger.warning(
                        "Unexpected error processing item at index %d: %s", index, exc
                    )

            logger.info(
                "Successfully loaded %d properties from %s",
                len(properties),
                self.file_path,
            )
            return properties

        except json.JSONDecodeError as exc:
            logger.error("Failed to decode JSON file: %s", exc)
            return []
        except Exception as exc:
            logger.error("Critical error loading properties: %s", exc)
            return []
