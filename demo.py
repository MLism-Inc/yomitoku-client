import json
from yomitoku_client.parsers import parse_pydantic_model

target = "notebooks/input.json"

with open(target, "r", encoding="utf-8") as f:
    sample_json = json.load(f)

data = parse_pydantic_model(sample_json)
print(data.to_csv(output_path="sample.csv", page_index=[0], mode="combine"))

data.visualize(
    image_path="notebooks/image.pdf",
    page_index=None,
    mode="ocr",
    output_directory="output_images",
)
