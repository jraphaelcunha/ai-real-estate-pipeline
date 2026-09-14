from src.services.analyzer import RealEstateAnalyzer
from src.services.ingestor import JsonFileIngestor
from src.services.monday import MondayClient


def main():
    # 1. Initialize Services
    ingestor = JsonFileIngestor(file_path="data/raw_mock_data.json")
    analyzer = RealEstateAnalyzer()
    monday = MondayClient()
    
    # 2. Load Properties
    properties = ingestor.load_properties()
    
    if not properties:
        print("No properties loaded.")
        return

    # 3. Analyze All Properties
    print(f"Loaded {len(properties)} properties. Starting analysis...")
    
    for prop in properties:
        result = analyzer.analyze_property(prop)
        
        if result:
            print(f"Analyzed {prop.address}: Score {result.viability_score}/100 - Action: {result.recommended_action.value}")
            print(f"Summary: {result.summary}")
            
            # 4. Sync to Monday.com
            monday.create_item(prop, result)
        else:
            print(f"Failed to analyze {prop.address}")
            
        # Visual Separator
        print("-" * 50)

if __name__ == "__main__":
    main()
