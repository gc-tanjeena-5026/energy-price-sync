import ast
import csv
import re
import os

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

# Write clean CSV
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["region", "metric", "price_yen_per_kwh"])
    writer.writerows(rows)

print(f"Done! Saved {len(rows)} rows to kankyo_data.csv")
print("\nPreview:")
for r in rows[:10]:
    print(r)
