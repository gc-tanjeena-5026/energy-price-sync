import ast
import csv
import re
import os
from datetime import datetime

# Read the raw data file
current_dir = os.path.dirname(os.path.abspath(__file__))
raw_path = os.path.join(current_dir, "raw_data.txt")
csv_path = os.path.join(current_dir, "kankyo_data.csv")

with open(raw_path, "r", encoding="utf-8") as f:
    all_data = ast.literal_eval(f.read())

def clean(text):
    """Remove all tabs, newlines, and extra spaces."""
    text = re.sub(r'[\t\n\r]', ' ', str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_price(text):
    """Pull out just the number from '13.89 円/kWh'."""
    match = re.search(r'[\d.]+(?=\s*円/kWh)', text)
    return match.group(0) if match else None

rows = []

for region_data in all_data:
    region = region_data["region"]
    matrix = region_data["matrix"]

    for row in matrix:
        # Only keep rows that contain a price (円/kWh)
        row_text = " ".join(row)
        if "円/kWh" not in row_text:
            continue

        cleaned = [clean(cell) for cell in row]
        row_text_clean = " ".join(cleaned)

        # Extract key stats
        if "全時間帯の平均単価" in row_text_clean:
            price = extract_price(row_text_clean)
            rows.append([region, "all_hours_avg", price])

        elif "8～22時の平均単価" in row_text_clean:
            price = extract_price(row_text_clean)
            rows.append([region, "daytime_avg_8_22", price])

        elif "22～8時の平均単価" in row_text_clean:
            price = extract_price(row_text_clean)
            rows.append([region, "nighttime_avg_22_8", price])

        elif "最安単価" in row_text_clean:
            price = extract_price(row_text_clean)
            time_match = re.search(r'\d{1,2}:\d{2}', row_text_clean)
            time = time_match.group(0) if time_match else ""
            rows.append([region, f"cheapest_price_{time}", price])

        elif "最高単価" in row_text_clean:
            price = extract_price(row_text_clean)
            time_match = re.search(r'\d{1,2}:\d{2}', row_text_clean)
            time = time_match.group(0) if time_match else ""
            rows.append([region, f"highest_price_{time}", price])

        elif "月間の平均単価" in row_text_clean:
            price = extract_price(row_text_clean)
            rows.append([region, "monthly_avg", price])

        elif "月間の最安値" in row_text_clean:
            price = extract_price(row_text_clean)
            rows.append([region, "monthly_lowest", price])

        elif "月間の最高値" in row_text_clean:
            price = extract_price(row_text_clean)
            rows.append([region, "monthly_highest", price])

# ── Safety check: refuse to save if too few rows were extracted ──────────────
MINIMUM_EXPECTED_ROWS = 50  # 9 regions x ~9 metrics each = ~81 rows expected

if len(rows) < MINIMUM_EXPECTED_ROWS:
    print(f"ERROR: Only {len(rows)} rows extracted — expected at least {MINIMUM_EXPECTED_ROWS}.")
    print("This likely means scraping failed for one or more regions.")
    print("Refusing to save a partial/incomplete CSV.")
    exit(1)

# ── Build a proper timestamp for each row based on its metric name ──────────
today_date = datetime.now().strftime("%Y-%m-%d")

def build_timestamp(metric_name, fallback_date):
    """
    Extracts HH:MM from metric names like 'cheapest_price_10:00' or 'highest_price_18:30'
    and builds a proper timestamp reflecting the actual time that price occurred.
    Falls back to 00:00:00 for summary stats (all_hours_avg, monthly_avg, etc.)
    since those represent the whole day/month, not a single moment.
    """
    time_match = re.search(r'(\d{1,2}):(\d{2})', metric_name)
    if time_match:
        hour, minute = time_match.groups()
        return f"{fallback_date}T{hour.zfill(2)}:{minute}:00"
    else:
        return f"{fallback_date}T00:00:00"

# ── Write clean CSV with per-row timestamps ──────────────────────────────────
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "region", "metric", "price_yen_per_kwh"])
    for row in rows:
        region, metric, price = row
        timestamp = build_timestamp(metric, today_date)
        writer.writerow([timestamp, region, metric, price])

print(f"Done! Saved {len(rows)} rows to kankyo_data.csv with per-metric timestamps")
print("\nPreview:")
for region, metric, price in rows[:10]:
    ts = build_timestamp(metric, today_date)
    print([ts, region, metric, price])
