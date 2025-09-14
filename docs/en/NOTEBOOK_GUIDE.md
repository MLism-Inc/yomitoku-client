# Notebook Usage Guide

## Overview

This guide explains how to use the two main notebooks in this repository to get OCR results from Yomitoku Pro and process them with Yomitoku Client.

## Workflow Overview

```
Document → Yomitoku Pro → OCR Results → Yomitoku Client → Processed Output
    ↓           ↓              ↓              ↓              ↓
  PDF/Image  SageMaker    JSON Format    Format Convert   CSV/HTML/PDF
```

## Step 1: Getting OCR Results (`yomitoku-pro-document-analyzer.ipynb`)

This notebook shows how to deploy and use Yomitoku Pro to get OCR results from your documents.

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **SageMaker FullAccess** permissions for your AWS user/role
3. **Yomitoku Pro subscription** from AWS Marketplace

### Deployment Options

#### Option A: Using CloudFormation (Recommended)

1. **Subscribe to Yomitoku Pro** from AWS Marketplace
2. **Launch CloudFormation stack** from the product page
3. **Configure parameters**:
   - Stack name: `yomitoku-pro-stack`
   - Instance type: `ml.g4dn.xlarge` (recommended)
   - Number of instances: `1`
4. **Wait for deployment** (usually 10-15 minutes)
5. **Get endpoint name** from CloudFormation outputs

#### Option B: Using SageMaker Console

1. **Create Model**:
   - Go to AWS Marketplace → Your subscribed product → Configure
   - Select "SageMaker Console" as launch method
   - Set model name (e.g., `my-yomitoku-model`)
   - Configure IAM role with SageMaker permissions

2. **Create Endpoint**:
   - Open your model page → Create endpoint
   - Set endpoint name (e.g., `my-yomitoku-endpoint`)
   - Choose instance type: `ml.g4dn.xlarge` or `ml.g5.xlarge`
   - Set number of instances: `1`

### Running OCR Analysis

```python
import boto3
import json
import base64

# Initialize SageMaker client
sagemaker_client = boto3.client('sagemaker-runtime')

# Prepare your document (PDF or image)
with open('your_document.pdf', 'rb') as f:
    document_data = base64.b64encode(f.read()).decode('utf-8')

# Create request payload
payload = {
    "inputs": document_data,
    "parameters": {
        "max_length": 1024,
        "temperature": 0.1
    }
}

# Send request to Yomitoku Pro endpoint
response = sagemaker_client.invoke_endpoint(
    EndpointName='your-endpoint-name',
    ContentType='application/json',
    Body=json.dumps(payload)
)

# Parse response
result = json.loads(response['Body'].read().decode('utf-8'))

# Save results for next step
with open('sagemaker_output.json', 'w') as f:
    json.dump(result, f, indent=2)
```

### Expected Output Format

The Yomitoku Pro output will be in this format:

```json
{
  "result": [
    {
      "paragraphs": [
        {
          "contents": "Sample text content",
          "box": [x1, y1, x2, y2],
          "order": 1,
          "role": "paragraph"
        }
      ],
      "tables": [
        {
          "cells": [...],
          "box": [x1, y1, x2, y2],
          "order": 2,
          "n_row": 2,
          "n_col": 2
        }
      ],
      "figures": [...],
      "words": [...],
      "preprocess": {...}
    }
  ]
}
```

## Step 2: Processing Results (`yomitoku-client-example.ipynb`)

This notebook demonstrates how to process the OCR results from Yomitoku Pro using Yomitoku Client.

### Basic Setup

```python
from yomitoku_client import YomitokuClient
from yomitoku_client.parsers.sagemaker_parser import SageMakerParser
import json

# Initialize client and parser
client = YomitokuClient()
parser = SageMakerParser()

# Load OCR results from Yomitoku Pro
with open('sagemaker_output.json', 'r') as f:
    sagemaker_output = json.load(f)

# Parse the results
parsed_data = parser.parse_dict(sagemaker_output)
```

### Format Conversion Examples

#### 1. Convert to CSV

```python
# Convert to CSV format
csv_result = client.convert_to_format(parsed_data, 'csv')

# Save to file
with open('output.csv', 'w', encoding='utf-8') as f:
    f.write(csv_result)

print("CSV conversion completed!")
```

#### 2. Convert to HTML

```python
# Convert to HTML format
html_result = client.convert_to_format(parsed_data, 'html')

# Save to file
with open('output.html', 'w', encoding='utf-8') as f:
    f.write(html_result)

print("HTML conversion completed!")
```

#### 3. Convert to Markdown

```python
# Convert to Markdown format
markdown_result = client.convert_to_format(parsed_data, 'markdown')

# Save to file
with open('output.md', 'w', encoding='utf-8') as f:
    f.write(markdown_result)

print("Markdown conversion completed!")
```

#### 4. Convert to JSON

```python
# Convert to structured JSON
json_result = client.convert_to_format(parsed_data, 'json')

# Save to file
with open('processed_output.json', 'w', encoding='utf-8') as f:
    f.write(json_result)

print("JSON conversion completed!")
```

### Advanced Visualization

```python
from yomitoku_client.visualizers import DocumentVisualizer
import cv2
import numpy as np

# Load your original image
image = cv2.imread('your_document.png')

# Initialize visualizer
doc_viz = DocumentVisualizer()

# 1. Basic layout visualization
layout_img = doc_viz.visualize((image, parsed_data[0]), type='layout_detail')
cv2.imwrite('layout_visualization.png', layout_img)

# 2. Reading order visualization
reading_order_img = doc_viz.visualize((image, parsed_data[0]), type='reading_order')
cv2.imwrite('reading_order.png', reading_order_img)

# 3. Element relationships
rel_img = doc_viz.visualize_element_relationships(
    image, parsed_data[0], 
    show_overlaps=True, 
    show_distances=True
)
cv2.imwrite('element_relationships.png', rel_img)

# 4. Element hierarchy
hierarchy_img = doc_viz.visualize_element_hierarchy(
    image, parsed_data[0], 
    show_containment=True
)
cv2.imwrite('element_hierarchy.png', hierarchy_img)

# 5. Confidence scores
confidence_img = doc_viz.visualize_confidence_scores(
    image, parsed_data[0], 
    show_ocr_confidence=True
)
cv2.imwrite('confidence_scores.png', confidence_img)
```

### Searchable PDF Generation

```python
from yomitoku_client.pdf_generator import SearchablePDFGenerator

# Initialize PDF generator
pdf_generator = SearchablePDFGenerator()

# Create searchable PDF
pdf_generator.create_searchable_pdf(
    images=[image],  # List of images
    ocr_results=parsed_data,  # OCR results
    output_path='searchable_output.pdf'
)

print("Searchable PDF created!")
```

### Utility Functions

```python
from yomitoku_client.utils import (
    calc_overlap_ratio, calc_distance, is_contained,
    escape_markdown_special_chars, table_to_csv
)

# Example: Calculate overlap between two elements
element1_box = [100, 100, 200, 200]
element2_box = [150, 150, 250, 250]

overlap_ratio, intersection = calc_overlap_ratio(element1_box, element2_box)
print(f"Overlap ratio: {overlap_ratio:.2f}")

# Example: Process table data
if parsed_data[0].tables:
    table = parsed_data[0].tables[0]
    csv_string = table_to_csv(table)
    print("Table as CSV:")
    print(csv_string)
```

### Complete Workflow Example

```python
# Complete workflow from document to processed output
def process_document_with_yomitoku(document_path, endpoint_name):
    """
    Complete workflow: Document → Yomitoku Pro → Yomitoku Client → Output
    """
    
    # Step 1: Get OCR results from Yomitoku Pro
    print("Step 1: Getting OCR results from Yomitoku Pro...")
    ocr_results = get_ocr_from_yomitoku_pro(document_path, endpoint_name)
    
    # Step 2: Process with Yomitoku Client
    print("Step 2: Processing with Yomitoku Client...")
    client = YomitokuClient()
    parsed_data = client.parse_dict(ocr_results)
    
    # Step 3: Convert to multiple formats
    print("Step 3: Converting to multiple formats...")
    formats = ['csv', 'html', 'markdown', 'json']
    for format_type in formats:
        result = client.convert_to_format(parsed_data, format_type)
        with open(f'output.{format_type}', 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"✓ {format_type.upper()} conversion completed")
    
    # Step 4: Create visualizations
    print("Step 4: Creating visualizations...")
    create_visualizations(document_path, parsed_data)
    
    # Step 5: Generate searchable PDF
    print("Step 5: Generating searchable PDF...")
    generate_searchable_pdf(document_path, parsed_data)
    
    print("✓ Complete workflow finished!")

# Run the workflow
process_document_with_yomitoku('your_document.pdf', 'your-endpoint-name')
```

### Troubleshooting

#### Common Issues

1. **Endpoint not found**: Check if your SageMaker endpoint is in "InService" status
2. **Permission errors**: Ensure your AWS credentials have SageMaker FullAccess
3. **Import errors**: Make sure yomitoku-client is properly installed
4. **Memory issues**: Use smaller instance types or process documents in batches

#### Getting Help

- Check the notebook outputs for detailed error messages
- Review AWS CloudWatch logs for SageMaker endpoint issues
- Ensure all dependencies are installed correctly
