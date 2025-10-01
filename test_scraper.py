"""
Quick test script to verify the scraper works
Tests with a single competitor page
"""

import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


async def test_basic_crawl():
    """Test basic crawling without extraction"""
    
    print("\n" + "="*80)
    print("🧪 Testing Basic Crawl")
    print("="*80 + "\n")
    
    # Test URL - PCLiquidations Dell laptops
    test_url = "https://www.pcliquidations.com/collections/dell-laptops"
    
    print(f"📡 Crawling: {test_url}\n")
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
    )
    
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for_images=False,
        delay_before_return_html=2.0,
    )
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url, config=crawler_config)
            
            if result.success:
                print("✅ Crawl successful!\n")
                print(f"📄 Page title: {result.metadata.get('title', 'N/A')}")
                print(f"📊 Content length: {len(result.markdown.raw_markdown)} characters")
                print(f"🔗 Links found: {len(result.links.get('internal', []))}")
                
                # Save markdown for inspection
                with open("test_page_content.md", "w", encoding="utf-8") as f:
                    f.write(result.markdown.raw_markdown)
                
                print(f"\n💾 Page content saved to: test_page_content.md")
                
                # Show a preview
                print(f"\n📝 Content Preview (first 500 chars):")
                print("="*80)
                print(result.markdown.raw_markdown[:500])
                print("="*80)
                
                # Try to find product indicators
                content_lower = result.markdown.raw_markdown.lower()
                
                print(f"\n🔍 Quick Analysis:")
                print(f"   - Contains 'dell': {'✅' if 'dell' in content_lower else '❌'}")
                print(f"   - Contains 'laptop': {'✅' if 'laptop' in content_lower else '❌'}")
                print(f"   - Contains price ($): {'✅' if '$' in result.markdown.raw_markdown else '❌'}")
                print(f"   - Contains 'i5' or 'i7': {'✅' if 'i5' in content_lower or 'i7' in content_lower else '❌'}")
                print(f"   - Contains RAM info: {'✅' if 'gb' in content_lower and ('ram' in content_lower or 'memory' in content_lower) else '❌'}")
                
                return True
            else:
                print("❌ Crawl failed!")
                print(f"Error: {result.error_message}")
                return False
    
    except Exception as e:
        print(f"❌ Error during crawl: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_sites():
    """Test crawling multiple competitor sites"""
    
    print("\n" + "="*80)
    print("🧪 Testing Multiple Competitor Sites")
    print("="*80 + "\n")
    
    test_sites = [
        ("PCLiquidations", "https://www.pcliquidations.com/collections/dell-laptops"),
        ("DiscountElectronics", "https://www.discountelectronics.com"),
        ("SystemLiquidation", "https://www.systemliquidation.com"),
        ("DellRefurbished", "https://www.dellrefurbished.com"),
    ]
    
    results = {}
    
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for_images=False,
        delay_before_return_html=2.0,
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for name, url in test_sites:
            print(f"🔍 Testing {name}...")
            try:
                result = await crawler.arun(url=url, config=crawler_config)
                
                if result.success:
                    results[name] = {
                        "status": "✅ Success",
                        "title": result.metadata.get('title', 'N/A'),
                        "content_length": len(result.markdown.raw_markdown),
                        "has_products": '$' in result.markdown.raw_markdown
                    }
                    print(f"   ✅ Success - {result.metadata.get('title', 'N/A')[:50]}...")
                else:
                    results[name] = {
                        "status": "❌ Failed",
                        "error": result.error_message
                    }
                    print(f"   ❌ Failed - {result.error_message}")
            
            except Exception as e:
                results[name] = {
                    "status": "❌ Error",
                    "error": str(e)
                }
                print(f"   ❌ Error - {str(e)}")
            
            # Small delay between requests
            await asyncio.sleep(1)
    
    # Print summary
    print("\n" + "="*80)
    print("📊 Test Summary")
    print("="*80 + "\n")
    
    for name, data in results.items():
        print(f"{name}:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        print()
    
    # Save results
    with open("test_results_summary.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("💾 Results saved to: test_results_summary.json")


async def test_product_extraction():
    """Test extracting product information from a page"""
    
    print("\n" + "="*80)
    print("🧪 Testing Product Extraction")
    print("="*80 + "\n")
    
    test_url = "https://www.pcliquidations.com/collections/dell-laptops"
    
    print(f"📡 Extracting products from: {test_url}\n")
    
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for_images=False,
        scan_full_page=True,
        delay_before_return_html=3.0,
    )
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url, config=crawler_config)
            
            if result.success:
                content = result.markdown.raw_markdown
                
                # Simple pattern matching to find products
                import re
                
                # Find prices
                prices = re.findall(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', content)
                
                # Find processor mentions
                processors = re.findall(r'(i[3579])-?(\d{1,2})(?:th|st|nd|rd)?\s*gen', content.lower())
                
                # Find RAM mentions
                ram = re.findall(r'(\d+)\s*GB', content)
                
                # Find storage mentions
                storage = re.findall(r'(\d+(?:\.\d+)?)\s*(GB|TB)\s*(?:SSD|HDD)', content, re.IGNORECASE)
                
                print(f"✅ Extraction Results:\n")
                print(f"   💰 Prices found: {len(prices)}")
                if prices[:5]:
                    print(f"      Examples: {', '.join(['$' + p for p in prices[:5]])}")
                
                print(f"\n   🖥️  Processors found: {len(processors)}")
                if processors[:5]:
                    print(f"      Examples: {', '.join([f'{p[0].upper()}-{p[1]}th gen' for p in processors[:5]])}")
                
                print(f"\n   💾 RAM mentions: {len(ram)}")
                if ram[:5]:
                    print(f"      Examples: {', '.join([r + 'GB' for r in ram[:5]])}")
                
                print(f"\n   📀 Storage mentions: {len(storage)}")
                if storage[:5]:
                    print(f"      Examples: {', '.join([f'{s[0]}{s[1]}' for s in storage[:5]])}")
                
                # Estimate number of products
                estimated_products = min(len(prices), len(processors)) if prices and processors else 0
                print(f"\n   📦 Estimated products: ~{estimated_products}")
                
                return True
            else:
                print(f"❌ Failed to crawl page")
                return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("\n" + "="*80)
    print("🚀 Competitor Scraper Test Suite")
    print("="*80)
    
    print("\nThis will test the scraper functionality without requiring an API key.")
    print("Choose a test to run:\n")
    print("1. Basic Crawl Test (single page)")
    print("2. Multiple Sites Test (all competitors)")
    print("3. Product Extraction Test (pattern matching)")
    print("4. Run All Tests")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        await test_basic_crawl()
    elif choice == "2":
        await test_multiple_sites()
    elif choice == "3":
        await test_product_extraction()
    elif choice == "4":
        print("\n🏃 Running all tests...\n")
        await test_basic_crawl()
        await asyncio.sleep(2)
        await test_product_extraction()
        await asyncio.sleep(2)
        await test_multiple_sites()
    else:
        print("Invalid choice")
    
    print("\n" + "="*80)
    print("✅ Testing Complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

