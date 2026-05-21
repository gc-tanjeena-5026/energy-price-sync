import os
import io
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta


def get_jepx_data():
    # Using a high-reliability edge proxy mirror to safely route the JEPX file extraction
    url = "https://corsproxy.io/?url=https://www.jepx.org/market/excel/spot_2026.csv"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    
    print("Routing request through high-reliability edge proxy...")
    try:
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.content.decode('shift_jis')))
    except Exception as e:
        print(f"Primary proxy failed. Trying alternative mirror routing...")
        try:
            # Secondary backup proxy mirror layer
            alt_url = "https://api.allorigins.win/raw?url=https://www.jepx.org/market/excel/spot_2026.csv"
            response = requests.get(alt_url, headers=headers, timeout=20)
            response.raise_for_status()
            return pd.read_csv(io.StringIO(response.content.decode('shift_jis')))
        except Exception as alt_err:
            print(f"Upstream Dependency Error: All proxy pipelines exhausted. Reason: {alt_err}")
            sys.exit(1)


def convert_slot_to_time(date_str, slot_num):
    base_date = datetime.strptime(date_str, "%Y/%m/%d")
    minutes_to_add = (int(slot_num) - 1) * 30
    exact_time = base_date + timedelta(minutes=minutes_to_add)
    return exact_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def process_and_push():
    # 1. NEW DATASET ID FIXED HERE
    dataset_id = "a92d827c-26ab-4e15-beed-f09dc35ec050"

    # 2. Retrieve Credentials from GitHub Secrets environment mapping
    api_key = os.getenv("MAIRA_API_KEY")
    project_key = os.getenv("MAIRA_PROJECT_KEY")

    # Local Testing Fallback: If GitHub secrets aren't found, use your provided keys locally
    if not api_key or not project_key:
        print("⚠️ GitHub environment secrets not found. Using local fallback keys for testing...")
        api_key = "gAAAAABp1wAXakpN28axAC05xKfoIrFrVb9-NJlZPs5SPRCdwLQp8SVcUhTxyKE7dKIshDLWXFfPoDnRigNBFW_hC54T-v9jjxJXs_YOA2kUcraQBi4MT2uO3OPP-47Wu5MFEwOJp1P1"
        project_key = "8Y-AM8ETtstpE8hl2OeVUwlgPiVzktZ5PWQeETlItpg="

    print("Fetching live data from JEPX...")
    df = get_jepx_data()
    df.columns = [col.strip() for col in df.columns]

    # Extract a 48-Hour Rolling Window (Today + Tomorrow)
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    target_dates = [today.strftime("%Y/%m/%d"), tomorrow.strftime("%Y/%m/%d")]

    filtered_df = df[df['年月日'].isin(target_dates)]

    payload_records = []
    for _, row in filtered_df.iterrows():
        try:
            timestamp = convert_slot_to_time(row['年月日'], row['コマ'])
            system_price = float(row['システム(円/kWh)'])
            payload_records.append({
                "timestamp": timestamp,
                "system_price": system_price
            })
        except Exception:
            continue

    if not payload_records:
        print("No target records found for the current 48-hour window.")
        return

    # Convert payload back to a clean CSV format string for Maira TS injection
    payload_df = pd.DataFrame(payload_records)
    csv_buffer = io.StringIO()
    payload_df.to_csv(csv_buffer, index=False)

    # Executing Ingestion PUT Request to Maira endpoint
    target_url = f"https://api.recommender.gigalogy.com/v1/gpt/datasets_ts/{dataset_id}/file"
    headers = {
        "Api-key": api_key,
        "project-key": project_key,
        "Content-Type": "text/csv"
    }

    print(f"Pushing {len(payload_records)} records into Maira AI Agent...")
    response = requests.put(target_url, headers=headers, data=csv_buffer.getvalue())

    if response.status_code in [200, 201, 204]:
        print("🚀 Success: Data Pipeline Synced and processed cleanly!")
    else:
        print(f"❌ Failed Ingestion. API Status: {response.status_code}, Context: {response.text}")


if __name__ == "__main__":
    process_and_push()
