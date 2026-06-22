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
    TIMEOUT_MS = 30000  # back to a reasonable 30s since the real issue was the URL, not speed

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
                    await page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
                    await page.wait_for_selector("table", timeout=TIMEOUT_MS)

                    rows_data = await page.evaluate("""
                        () => {
                            const rows = document.querySelectorAll('table tr');
                            return Array.from(rows).map(row =>
                                Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim())
                            );
                        }
                    """)
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

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "raw_data.txt")

    print(f"Writing parsed matrix content to cache file: {file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(all_extracted_data))
    print(f"Scraping stage complete. Successfully captured {len(all_extracted_data)}/{len(regions)} regions.")


if __name__ == "__main__":
    asyncio.run(scrape_kankyo())
