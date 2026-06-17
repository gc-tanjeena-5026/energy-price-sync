import requests
import os

API_KEY = "gAAAAABp1wAXakpN28axAC05xKfoIrFrVb9-NJlZPs5SPRCdwLQp8SVcUhTxyKE7dKIshDLWXFfPoDnRigNBFW_hC54T-v9jjxJXs_YOA2kUcraQBi4MT2uO3OPP-47Wu5MFEwOJp1P1"
PROJECT_KEY = "8Y-AM8ETtstpE8hl2OeVUwlgPiVzktZ5PWQeETlItpg="
DATASET_ID = "a92d827c-26ab-4e15-beed-f09dc35ec050"

current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "kankyo_data.csv")

url = f"https://api.recommender.gigalogy.com/v1/gpt/datasets_ts/{DATASET_ID}/file"

headers = {
    "project-key": PROJECT_KEY,
    "api-key": API_KEY
}

print(f"Uploading kankyo_data.csv...")

with open(csv_path, "rb") as f:
    response = requests.put(
        url,
        headers=headers,
        files={"dataset_file": ("kankyo_data.csv", f, "text/csv")}
    )

print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")
