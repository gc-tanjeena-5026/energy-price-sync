import os
import asyncio
from playwright.async_api import async_playwright


async def scrape_kankyo():
    regions = {
        "hokkaido": "https://kankyo-ichiba.jp/hokkaido",
        "tohoku": "https://kankyo-ichiba.jp/touhoku",
        "tokyo": "https://kankyo-ichiba.jp/tokyo",
        "chubu": "https://kankyo-ichiba.jp/chuubu",
        "hokuriku": "https://kankyo-ichiba.jp/hokuriku",
        "kansai": "https://kankyo-ichiba.jp/kansai",
        "chugoku": "https://kankyo-ichiba.jp/chuugoku",
        "shikoku": "https://kankyo-ichiba.jp/sikoku",
        "kyushu": "https://kankyo-ichiba.jp/kyusyu"
    }

    all_extracted_data = []
    MAX_RETRIES = 3
    TIMEOUT_MS = 30000

    async with async_playwright() as p:
        print("Launching headless Chromium browser via Playwright...")
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        for region_name, url in regions.items():
            print(f"Navigating to {region_name} page ({url})...")
            success = False

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # Force a hard navigation each time, not relying on SPA routing
                    await page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
                    await page.wait_for_selector("table", timeout=TIMEOUT_MS)

                    # Extra wait to let JS finish updating the numbers after navigation
                    await page.wait_for_timeout(2000)

                    # Wait specifically for the average price box to have real content
                    await page.wait_for_function(
                        "document.querySelector('.da_24 .index_num')?.innerText.trim().length > 0",
                        timeout=TIMEOUT_MS
                    )

                    rows_data = await page.evaluate("""
                        () => {
                            const rows = document.querySelectorAll('table tr');
                            return Array.from(rows).map(row =>
                                Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim())
                            );
                        }
                    """)

                    # Sanity check: grab the actual average price box value to log it
                    avg_price_check = await page.evaluate(
                        "document.querySelector('.da_24 .index_num')?.innerText.trim()"
                    )
                    print(f"  -> {region_name} all_hours_avg from page: {avg_price_check}")

                    all_extracted_data.append({"region": region_name, "matrix": rows_data})
                    print(f"Successfully scraped matrix data for: {region_name} (attempt {attempt})")
                    success = True
                    break

                except Exception as e:
                    print(f"Attempt {attempt}/{MAX_RETRIES} failed for region '{region_name}': {e}")
                    if attempt < MAX_RETRIES:
                        print(f"Retrying {region_name} in 5 seconds...")
                        await asyncio.sleep(5)

            if not success:
                print(f"FINAL FAILURE: Could not scrape '{region_name}' after {MAX_RETRIES} attempts.")

        await browser.close()

    # Duplicate detection across regions — catches stale-page bugs immediately
    seen_signatures = {}
    for entry in all_extracted_data:
        region = entry["region"]
        signature = str(entry["matrix"][5:11])  # the core price rows
        if signature in seen_signatures:
            print(f"WARNING: '{region}' has IDENTICAL data to '{seen_signatures[signature]}' — likely a stale scrape!")
        else:
            seen_signatures[signature] = region

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "raw_data.txt")

    print(f"Writing parsed matrix content to cache file: {file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(all_extracted_data))
    print(f"Scraping stage complete. Successfully captured {len(all_extracted_data)}/{len(regions)} regions.")


if __name__ == "__main__":
    asyncio.run(scrape_kankyo())
