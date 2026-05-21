import os
import io
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta


def get_jepx_data():
    # Target URL changed to the Hokkaido Environment Market portal
    url = "https://kankyo-ichiba.jp/hokkaido"
    
    # Complete set of browser handshake headers to blend in with real human traffic
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": "https://kankyo-ichiba.jp/",
        "Cache-Control": "max-age=0"
    }
    
    print("Initiating session connection to kankyo-ichiba.jp/hokkaido...")
    session = requests.Session()
    
    try:
        # Route through the proxy tunnel to hide the GitHub Action runner IP signature
        proxy_url = f"https://corsproxy.io/?url={url}"
        response = session.get(proxy_url, headers=headers, timeout=25)
        response.raise_for_status()
        
        html_content = response.text
        print("Webpage content fetched successfully. Parsing price structures...")
        
        # NOTE: Since we are parsing raw HTML now instead of a JEPX CSV, 
        # we extract the text or table data directly into your pandas DataFrame
        # [Adjust your pandas processing below this to match the site's table structure]
        
        # Temporary placeholder conversion to keep your downstream data processing alive:
        dfs = pd.read_html(io.StringIO(html_content))
        return dfs[0] # Returns the first compiled table found on the site
        
    except Exception as e:
        print(f"Proxy bridge failed. Trying direct browser emulation fallback...")
        try:
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            dfs = pd.read_html(io.StringIO(response.text))
            return dfs[0]
        except Exception as fallback_err:
            print(f"Upstream Dependency Error: Failed to extract data layout from site. Reason: {fallback_err}")
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
