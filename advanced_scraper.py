"""
Advanced Competitor Price Scraper with LLM Extraction
Uses AI to intelligently extract product information
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field


# ============================================================================
# Data Models (same as before)
# ============================================================================

class ProductConfig(BaseModel):
    processor: str = Field(default="", description="Processor (e.g., i5-11th gen, i7-13th gen)")
    ram: str = Field(default="", description="RAM (e.g., 8GB, 16GB, 32GB)")
    storage: str = Field(default="", description="Storage (e.g., 256GB SSD, 1TB HDD)")
    cosmetic_grade: str = Field(default="", description="Grade A, B, or C")
    form_factor: str = Field(default="", description="Tower, SFF, MFF/Tiny")
    screen_resolution: str = Field(default="", description="HD, FHD, QHD, 4K UHD")
    screen_size: str = Field(default="", description="Screen size (e.g., 14 inch, 15.6 inch)")


class Product(BaseModel):
    brand: str = Field(..., description="Dell, HP, or Lenovo")
    model: str = Field(..., description="Model number")
    product_type: str = Field(..., description="Laptop or Desktop")
    title: str = Field(..., description="Product title")
    price: float = Field(default=0.0, description="Price in USD")
    url: str = Field(default="", description="Product URL")
    config: ProductConfig = Field(default_factory=ProductConfig)
    availability: str = Field(default="", description="In Stock, Out of Stock, etc")


# ============================================================================
# LLM-Based Scraper
# ============================================================================

class AdvancedCompetitorScraper:
    """Advanced scraper using LLM for intelligent extraction"""

    def __init__(self, api_key: str = None, provider: str = None):
        # Load environment variables from .env file if it exists
        from pathlib import Path
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)

        # Determine provider
        self.provider = provider or os.getenv("LLM_PROVIDER", "deepseek")

        # Get API key based on provider
        if self.provider == "deepseek":
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            self.provider_name = "deepseek/deepseek-chat"
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            self.provider_name = f"openai/{self.model}"

        if not self.api_key:
            print(f"⚠️  Warning: No {self.provider.upper()} API key found.")
            print(f"   Set {self.provider.upper()}_API_KEY in .env file or environment variable.")
    
    async def scrape_with_llm(self, url: str, product_type: str = "Laptop") -> List[Product]:
        """Scrape using LLM extraction"""
        
        print(f"\n🤖 Using AI to extract {product_type} data from: {url}")
        
        # Define extraction schema
        extraction_strategy = LLMExtractionStrategy(
            provider=self.provider_name,
            api_token=self.api_key,
            schema=Product.model_json_schema(),
            extraction_type="schema",
            instruction=f"""
            Extract ALL {product_type.lower()} products from this page. 
            
            ONLY include products from these brands: Dell, HP, Lenovo
            IGNORE all other brands (Acer, Asus, Microsoft, etc.)
            
            For each product, extract:
            1. Brand (must be Dell, HP, or Lenovo)
            2. Model number (e.g., Latitude 5420, EliteBook 840 G8, ThinkPad T14)
            3. Product type: "{product_type}"
            4. Full product title
            5. Price (numeric value in USD, without $ symbol)
            6. Product URL (if available)
            7. Configuration:
               - Processor: Extract generation and model (e.g., "i5-11th gen", "i7-13th gen", "Ryzen 5 5600")
               - RAM: Extract size (e.g., "8GB", "16GB", "32GB")
               - Storage: Extract size and type (e.g., "256GB SSD", "1TB HDD", "512GB NVMe")
               - Cosmetic Grade: If mentioned (Grade A, B, or C)
               - Form Factor (Desktop only): Tower, SFF, MFF, or Tiny
               - Screen Resolution (Laptop only): HD (1366x768), FHD (1920x1080), QHD (2560x1440), or 4K UHD (3840x2160)
               - Screen Size (Laptop only): e.g., "14 inch", "15.6 inch"
            8. Availability: In Stock, Out of Stock, Limited, etc.
            
            Be thorough and extract ALL matching products on the page.
            """,
            verbose=True
        )
        
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
        )
        
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            wait_for_images=False,
            scan_full_page=True,
            delay_before_return_html=3.0,
        )
        
        products = []
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)
                
                if result.success and result.extracted_content:
                    # Parse extracted content
                    extracted = json.loads(result.extracted_content)
                    
                    # Handle both single product and list of products
                    if isinstance(extracted, list):
                        products = [Product(**item) for item in extracted]
                    elif isinstance(extracted, dict):
                        products = [Product(**extracted)]
                    
                    print(f"   ✅ Extracted {len(products)} products")
                else:
                    print(f"   ❌ Failed to extract products")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        return products
    
    async def scrape_competitor_advanced(self, competitor_name: str, urls: dict) -> dict:
        """Scrape a competitor using advanced LLM extraction"""
        
        print(f"\n{'='*80}")
        print(f"🔍 Advanced Scraping: {competitor_name}")
        print(f"{'='*80}")
        
        all_products = []
        
        # Scrape laptops
        print(f"\n📱 Scraping Laptop Pages...")
        for url in urls.get('laptop_urls', []):
            products = await self.scrape_with_llm(url, "Laptop")
            all_products.extend(products)
        
        # Scrape desktops
        print(f"\n🖥️  Scraping Desktop Pages...")
        for url in urls.get('desktop_urls', []):
            products = await self.scrape_with_llm(url, "Desktop")
            all_products.extend(products)
        
        return {
            "competitor": competitor_name,
            "website": urls.get('url', ''),
            "scrape_date": datetime.now().isoformat(),
            "products": [p.model_dump() for p in all_products],
            "total_products": len(all_products)
        }


# ============================================================================
# Quick Test Function
# ============================================================================

async def test_single_url():
    """Test scraping a single URL"""
    
    # Test with PCLiquidations Dell laptops page
    test_url = "https://www.pcliquidations.com/collections/dell-laptops"
    
    scraper = AdvancedCompetitorScraper()
    products = await scraper.scrape_with_llm(test_url, "Laptop")
    
    print(f"\n{'='*80}")
    print(f"📊 Test Results")
    print(f"{'='*80}")
    print(f"Total products found: {len(products)}\n")
    
    for i, product in enumerate(products[:5], 1):  # Show first 5
        print(f"{i}. {product.brand} {product.model}")
        print(f"   Price: ${product.price}")
        print(f"   CPU: {product.config.processor}")
        print(f"   RAM: {product.config.ram}")
        print(f"   Storage: {product.config.storage}")
        if product.config.screen_resolution:
            print(f"   Display: {product.config.screen_resolution}")
        print()
    
    # Save test results
    with open("test_results.json", "w") as f:
        json.dump([p.model_dump() for p in products], f, indent=2)
    
    print(f"💾 Full results saved to test_results.json")


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Main execution"""

    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("\n" + "="*80)
    print("🚀 Advanced Competitor Price Scraper")
    print("="*80)
    print("\nThis scraper uses AI to intelligently extract product data.")
    print("Make sure you have set your API key in the .env file.\n")
    
    choice = input("Choose mode:\n1. Test single URL\n2. Scrape all competitors\n\nEnter choice (1 or 2): ")
    
    if choice == "1":
        await test_single_url()
    elif choice == "2":
        # Import competitor configs
        from competitor_price_scraper import COMPETITORS
        
        scraper = AdvancedCompetitorScraper()
        all_results = {}
        
        for competitor_name, config in COMPETITORS.items():
            try:
                result = await scraper.scrape_competitor_advanced(competitor_name, config)
                all_results[competitor_name] = result
            except Exception as e:
                print(f"❌ Failed to scrape {competitor_name}: {str(e)}")
        
        # Save results
        with open("competitor_prices.json", "w") as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n💾 Results saved to competitor_prices.json")
        print(f"🌐 Open price_dashboard.html in your browser to view results")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())

