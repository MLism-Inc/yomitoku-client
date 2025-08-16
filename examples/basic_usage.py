"""
Basic usage example for Yomitoku Client
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.yomitoku_client.client import YomitokuClient


def main():
    """Basic usage example"""
    
    # Initialize client
    client = YomitokuClient()
    
    # Parse SageMaker output
    data = client.parse_file('test_sample.json')
    print(f"Parsed document with {len(data.paragraphs)} paragraphs and {len(data.tables)} tables")
    
    # Convert to different formats
    print("\n=== CSV Format ===")
    csv_result = client.convert_to_format(data, 'csv')
    print(csv_result)
    
    print("\n=== Markdown Format ===")
    md_result = client.convert_to_format(data, 'markdown')
    print(md_result)
    
    print("\n=== JSON Format ===")
    json_result = client.convert_to_format(data, 'json')
    print(json_result[:500] + "...")
    
    # Save to files
    client.convert_to_format(data, 'csv', 'output.csv')
    client.convert_to_format(data, 'markdown', 'output.md')
    client.convert_to_format(data, 'json', 'output.json')
    
    print("\nFiles saved: output.csv, output.md, output.json")


if __name__ == '__main__':
    main()
