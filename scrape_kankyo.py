import os
import asyncio
from playwright.async_api import async_playwright


async def scrape_kankyo():
    # List of all 9 regional subpages on Kankyo-Ichiba
    regions = {
        "hokkaido": "https://kankyo-ichiba.jp/hokkaido",
        "tohoku": "https://kankyo-ichiba.jp/tohoku",
        "tokyo": "https://kankyo-ichiba.jp/tokyo",
        "chubu": "https://kankyo-ichiba.jp/chubu",
        "hokuriku": "https://kankyo-ichiba.jp/hokuriku",
        "kansai": "https://kankyo-ichiba.jp/kansai",
        "chugoku": "https://kankyo-ichiba.jp/chugoku",
        "shikoku": "https://kankyo-ichiba.jp/shikoku",
        "kyushu": "https://kankyo-ichiba.jp/kyushu"
    }

    all_extracted_data = []

    async with async_playwright() as p:
        print("Launching headless Chromium browser via Playwright...")
        # Disable automation flags to bypass anti-bot security systems
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            ignore_https_errors=True,  # CRITICAL: Bypasses the SSLV3 alert failure
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        for region_name, url in regions.items():
            print(f"Navigating to {region_name} page...")
            try:
                # Wait until network activity is quiet and table elements render
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector("table", timeout=15000)

                # JavaScript execution to extract text contents from HTML tables
                rows_data = await page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('table tr');
                        return Array.from(rows).map(row =>
                            Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim())
                        );
                    }
                """)
                all_extracted_data.append({"region": region_name, "matrix": rows_data})
                print(f"Successfully scraped matrix data for: {region_name}")
            except Exception as e:
                print(f"Failed to extract data for region '{region_name}': {e}")

        await browser.close()

    # Locate the directory where this script file lives to establish absolute path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "raw_data.txt")

    # Write the array structure directly into the data exchange file
    print(f"Writing parsed matrix content to cache file: {file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(all_extracted_data))
    print("Scraping stage complete.")


if __name__ == "__main__":
    asyncio.run(scrape_kankyo())
