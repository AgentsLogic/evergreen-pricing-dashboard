#!/usr/bin/env python3
"""
Quick test script to debug DiscountPC scraping
"""

import asyncio
import sys
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def test_discountpc():
    """Test scraping DiscountPC"""

    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
    )

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=3.0,
        page_timeout=30000,
        wait_for_images=False,
        remove_overlay_elements=True
    )

    test_urls = [
        "https://discountpc.com/collections/laptops",
        "https://discountpc.com/collections/desktops"
    ]

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in test_urls:
            print(f"\n{'='*60}")
            print(f"Testing: {url}")
            print(f"{'='*60}")

            try:
                result = await crawler.arun(url=url, config=crawler_config)

                if result.success:
                    html = result.markdown.raw_markdown
                    print(f"✓ Success! Content length: {len(html)} characters")

                    # Look for product indicators
                    dell_count = html.upper().count('DELL')
                    hp_count = html.upper().count('HP')
                    lenovo_count = html.upper().count(' LENOVO')
                    product_count = html.upper().count('LAPTOP') + html.upper().count('DESKTOP') + html.upper().count('COMPUTER')

                    print(f"Found brand mentions:")
                    print(f"  - DELL: {dell_count}")
                    print(f"  - HP: {hp_count}")
                    print(f"  - LENOVO: {lenovo_count}")
                    print(f"  - PRODUCTS: {product_count}")

                    # Show first 1000 characters
                    print("\nFirst 1000 chars of content:")
                    print(f"'{html[:1000]}...'")

                    # Look for product grid/structure
                    if 'product' in html.lower():
                        print("✓ Contains 'product' keyword - structure looks good")
                    else:
                        print("⚠️  No 'product' keyword found")

                    if 'collection' in html.lower():
                        print("✓ Contains 'collection' keyword - Shopify site detected")
                    else:
                        print("⚠️  No 'collection' keyword found")

                else:
                    print("❌ Failed to load page")
                    if hasattr(result, 'error_message'):
                        print(f"Error: {result.error_message}")

            except Exception as e:
                print(f"❌ Exception: {e}")

            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_discountpc())
