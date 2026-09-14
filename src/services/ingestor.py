import json
from pathlib import Path

from pydantic import ValidationError

from src.domain.schemas import PropertyInput
from src.services.interfaces import DataIngestor
from src.utils.logger import get_logger

logger = get_logger("json_ingestor")

class JsonFileIngestor(DataIngestor):
    """
    Concrete implementation of DataIngestor for JSON files.
    """
    
    def __init__(self, file_path: str):
        # Use pathlib to resolve absolute path dynamically
        self.file_path = Path(file_path).resolve()
        
    def load_properties(self) -> list[PropertyInput]:
        """
        Loads properties from the configured JSON file.
        Includes fault tolerance to skip individual invalid items.
        """
        logger.info(f"Attempting to load properties from {self.file_path}")
        
        if not self.file_path.exists():
            logger.error(f"File not found: {self.file_path}")
            return []
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                logger.error(f"Invalid JSON format. Expected a list, got {type(data)}")
                return []
                
            properties = []
            
            for index, item in enumerate(data):
                try:
                    # Validate and convert individual item
                    prop = PropertyInput(**item)
                    properties.append(prop)
                except ValidationError as e:
                    logger.warning(f"Skipping invalid item at index {index}: {e}")
                except Exception as e:
                    logger.warning(f"Unexpected error processing item at index {index}: {e}")
            
            logger.info(f"Successfully loaded {len(properties)} properties from {self.file_path}")
            return properties
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON file: {e}")
            return []
        except Exception as e:
            logger.error(f"Critical error loading properties: {e}")
            return []
