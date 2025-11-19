"""
Competitor MSRP Price Scraper v2 - Complete Rebuild
Scrapes all products from 5 competitor websites
"""

import asyncio
import json
import re
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
from pathlib import Path

# Set default encoding to UTF-8 for all file operations
import locale
if sys.platform == 'win32':
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass  # Use system default if UTF-8 locales not available
    # Reconfigure stdout to handle UTF-8 encoding properly on Windows
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass  # If reconfigure fails, continue with default

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)


# ============================================================================
# Data Models
# ============================================================================

class ProductConfig(BaseModel):
    """Product configuration details"""
    processor: Optional[str] = Field(None, description="Processor (e.g., i5-11th gen, i7-13th gen)")
    ram: Optional[str] = Field(None, description="RAM (e.g., 8GB, 16GB, 32GB)")
    storage: Optional[str] = Field(None, description="Storage (e.g., 256GB SSD, 1TB HDD)")
    cosmetic_grade: Optional[str] = Field(None, description="Grade A, B, or C")
    form_factor: Optional[str] = Field(None, description="Desktop: Tower, SFF, MFF/Tiny")
    screen_resolution: Optional[str] = Field(None, description="Laptop: HD, FHD, QHD, 4K")
    screen_size: Optional[str] = Field(None, description="Screen size in inches")


class ReviewData(BaseModel):
    """Review and rating information"""
    review_count: Optional[int] = Field(None, description="Number of customer reviews")
    average_rating: Optional[float] = Field(None, description="Average star rating (1-5)")
    rating_distribution: Optional[Dict[str, int]] = Field(None, description="5-star, 4-star, etc. counts")
    is_best_seller: Optional[bool] = Field(None, description="Has 'Best Seller' badge")
    is_top_rated: Optional[bool] = Field(None, description="Has 'Top Rated' badge")
    sales_rank: Optional[str] = Field(None, description="Sales rank category or number")


class Product(BaseModel):
    """Product information"""
    brand: str = Field(..., description="Dell, HP, or Lenovo")
    model: str = Field(..., description="Model number")
    product_type: str = Field(..., description="Laptop or Desktop")
    title: str = Field(..., description="Product title")
    price: Optional[float] = Field(None, description="Price in USD")
    url: Optional[str] = Field(None, description="Product URL")
    config: ProductConfig = Field(default_factory=ProductConfig)
    availability: Optional[str] = Field(None, description="In stock, Out of stock, etc")
    reviews: Optional[ReviewData] = Field(default_factory=ReviewData, description="Review and rating data")
    competitor: Optional[str] = Field(None, description="Competitor name")


# ============================================================================
# Competitor URLs - ALL PAGES
# ============================================================================

COMPETITORS = {
    "DellRefurbished": {
        "base_url": "https://www.dellrefurbished.com",
        "urls": [
            "https://www.dellrefurbished.com/laptops",
            "https://www.dellrefurbished.com/desktop-computers",
            "https://www.dellrefurbished.com/computer-workstation",
        ]
    },
    "DiscountElectronics": {
        "base_url": "https://discountelectronics.com",
        "urls": [
            "https://discountelectronics.com/refurbished-laptops/",
            "https://discountelectronics.com/refurbished-computers/",
        ]
    },
    "SystemLiquidation": {
        "base_url": "https://systemliquidation.com",
        "urls": [
            "https://systemliquidation.com/collections/refurbished-desktop-computers",
            "https://systemliquidation.com/collections/refurbished-laptops",
            "https://systemliquidation.com/collections/refurbished-mobile-workstations",
        ]
    },
    "PCLiquidations": {
        "base_url": "https://www.pcliquidations.com",
        "urls": [
            "https://www.pcliquidations.com/refurbished-desktop-computers",
            "https://www.pcliquidations.com/refurbished-laptops",
        ]
    },
    "DiscountPC": {
        "base_url": "https://discountpc.com",
        "urls": [
            "https://discountpc.com/collections/laptops",
            "https://discountpc.com/collections/desktops",
        ]
    }
}


# ============================================================================
# AI-Powered Scraper
# ============================================================================

class CompetitorScraper:
    """AI-powered competitor scraper using DeepSeek/OpenAI"""

    def __init__(self):
        # Determine provider
        self.provider = os.getenv("LLM_PROVIDER", "deepseek")

        if self.provider == "deepseek":
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.model = "deepseek/deepseek-chat"
        else:
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.model = "openai/gpt-4o-mini"

        # Track how many products we drop per competitor due to Jeff's 8th-gen+ Intel filter
        self.skipped_counts = defaultdict(int)

        if not self.api_key:
            print(f"[WARNING] No {self.provider.upper()} API key found.")
            print(f"   Set {self.provider.upper()}_API_KEY in .env file")
            print("[INFO] Scraping will continue but may be less accurate.")

    # ------------------------------------------------------------------
    # Brand / CPU helpers to enforce Jeff's scope (Dell/HP/Lenovo, Intel 8th+)
    # ------------------------------------------------------------------
    def _normalize_brand(self, brand: Optional[str]) -> Optional[str]:
        """Map various brand spellings to canonical form; return None if not Dell/HP/Lenovo."""
        if not brand:
            return None
        b = brand.strip().lower()
        if "dell" in b:
            return "Dell"
        if b in {"hp", "hewlett-packard", "hewlett packard", "hewlett\u2011packard"} or "hewlett" in b:
            return "HP"
        if "lenovo" in b:
            return "Lenovo"
        return None

    def _extract_intel_generation(self, text: Optional[str]) -> Optional[int]:
        """Best-effort Intel CPU generation parser.

        We treat anything we cannot confidently parse as "unknown" (None),
        which lets us conservatively drop it from the dataset if desired.
        """
        if not text:
            return None
        t = text.lower()

        # Must look like an Intel family CPU; otherwise we treat as non-Intel
        if "intel" not in t and "core i" not in t:
            return None

        # Pattern like "11th Gen" / "8th gen"
        m = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s*gen", t)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

        # Pattern like "i5-8350U" or "i7 9700"
        m = re.search(r"\bi[3579]-?(\d{4,5})", t)
        if m:
            digits = m.group(1)
            try:
                if len(digits) >= 5 and digits[:2].isdigit():
                    gen = int(digits[:2])  # 10xxx, 11xxx, 12xxx, etc.
                else:
                    gen = int(digits[0])   # 8xxx, 9xxx
                if 1 <= gen <= 20:
                    return gen
            except ValueError:
                pass

        # Fallback: "i5 8th gen" style
        m = re.search(r"\bi[3579]\s*(\d{1,2})\w*\s*gen", t)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

        return None

    def _is_relevant_product(self, product: "Product") -> bool:
        """Return True only for Dell/HP/Lenovo with Intel 8th-gen or newer CPUs.

        This implements Jeff's business rule: only show 8th+ gen Intel laptops/desktops
        from Dell, HP, or Lenovo. 7th gen and older (or non-Intel/unknown) are dropped.
        """
        # Normalize/validate brand first
        normalized = self._normalize_brand(getattr(product, "brand", None))
        if not normalized:
            return False
        product.brand = normalized

        # Derive CPU text from config first, then fall back to title/model
        cpu_text = None
        cfg = getattr(product, "config", None)
        if cfg and getattr(cfg, "processor", None):
            cpu_text = cfg.processor
        else:
            # Some sites may only mention CPU in the title
            cpu_text = (product.title or "") + " " + (product.model or "")

        gen = self._extract_intel_generation(cpu_text)
        if gen is None:
            # We couldn't verify Intel generation -> treat as not relevant
            return False

        # Enforce 8th generation and newer only
        return gen >= 8

    async def scrape_url(self, url: str, competitor: str, max_pages: int = 5) -> List[Product]:
        """Scrape a single URL and extract all products (handles pagination)"""
        print(f"\n[SCRAPING] Scraping: {url}")

        # Determine product type from URL
        url_lower = url.lower()
        if 'laptop' in url_lower or 'notebook' in url_lower:
            product_type = "Laptop"
        elif 'desktop' in url_lower or 'workstation' in url_lower:
            product_type = "Desktop"
        else:
            product_type = "Unknown"

        all_products = []
        consecutive_failures = 0

        # Try to scrape multiple pages
        for page_num in range(1, max_pages + 1):
            # Construct page URL
            if page_num == 1:
                page_url = url
            else:
                # Different sites use different pagination patterns
                if '?' in url:
                    page_url = f"{url}&page={page_num}"
                else:
                    page_url = f"{url}?page={page_num}"

            print(f"   [PAGE] Page {page_num}...")

            try:
                products = await self._scrape_single_page(page_url, competitor, product_type)

                if not products:
                    consecutive_failures += 1
                    if page_num == 1:
                        print(f"   [WARNING] No products found on first page - may need manual review")
                        break
                    elif consecutive_failures >= 2:
                        print(f"   [SUCCESS] Reached end of pages at page {page_num}")
                        break
                else:
                    consecutive_failures = 0
                    all_products.extend(products)
                    print(f"   [SUCCESS] Found {len(products)} products on page {page_num}")
                    
                    # Save incrementally after each page
                    self._save_incremental_results(competitor, all_products)

                # Be respectful - delay between pages
                await asyncio.sleep(3)

            except Exception as e:
                print(f"   [ERROR] Error on page {page_num}: {str(e)}")
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    print(f"   [WARNING] Too many failures, stopping pagination")
                    break
                await asyncio.sleep(5)  # Longer delay after error

        return all_products

    async def _scrape_single_page(self, url: str, competitor: str, product_type: str) -> List[Product]:
        """Scrape a single page"""
        # Browser configuration
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )

        # Try LLM extraction first, but if it fails, fall back to CSS extraction
        try:
            extraction_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(
                    provider=self.model,
                    api_token=self.api_key
                ),
                schema=Product.model_json_schema(),
                extraction_type="schema",
                instruction=f"""
                Extract ALL {product_type} products from this page.

                IMPORTANT RULES:
                1. ONLY extract products from these brands: Dell, HP, Lenovo
                2. Ignore all other brands (Acer, Asus, Microsoft, etc.)
                3. Extract ALL products on the page, not just the first few
                4. For each product, ALL FIELDS ARE REQUIRED:
                   - Brand: Must be "Dell", "HP", or "Lenovo" (case sensitive)
                   - Model: Extract the model number or name (never null/empty)
                   - Product type: "{product_type}"
                   - Title: Full product title/name from the page
                   - Price: Numeric price (no $ sign, just numbers)
                   - URL: Full product URL from the page
                   - Processor: CPU description (may be null)
                   - RAM: Memory amount (may be null)
                   - Storage: Storage capacity (may be null)
                   - Cosmetic grade: "Grade A", "Grade B", "Grade C" or null
                   - Form factor: For desktops only (may be null)
                   - Screen resolution: For laptops only (may be null)
                   - Availability: Stock status (may be null)

                   CPU / GENERATION FILTERING (VERY IMPORTANT):
                   - Only include products with Intel Core CPUs that are 8th generation or newer.
                   - If you cannot confidently determine the Intel generation (from model numbers like i5-8350U, i7-9700, i5-1135G7, or phrases like "11th Gen"), SKIP that product.
                   - Skip any products with non-Intel CPUs (AMD, Ryzen, etc).

                DO NOT include products where:
                - Brand is not exactly "Dell", "HP", or "Lenovo"
                - Model is empty/null/None

                Return a JSON array of Product objects. Each product must have a valid model field.
                """
            )
        except Exception as e:
            print(f"   [WARNING] Failed to initialize LLM extraction, using CSS fallback: {e}")
            # Fall back to a simple text extraction for debugging
            extraction_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(
                    provider=self.model,
                    api_token=self.api_key
                ),
                schema=Product.model_json_schema(),
                extraction_type="schema",
                instruction="Return an empty JSON array [] since LLM extraction failed."
            )

        # Crawler configuration - removed wait_for to avoid selector timeout
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            delay_before_return_html=5.0,  # Increased delay to let page load
            page_timeout=90000,  # Increased timeout
            mean_delay=2.0,
            max_range=4.0,
            wait_for_images=False,  # Don't wait for images
            remove_overlay_elements=True  # Remove popups/overlays
        )

        products = []

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=crawler_config
                )

                if result.success:
                    if result.extracted_content:
                        try:
                            # Clean the extracted content - remove any BOM or extra whitespace
                            content = result.extracted_content.strip()

                            # DEBUG: Print the extracted content to see what's happening
                            print(f"   [DEBUG] Extracted content length: {len(content)}")
                            print(f"   [DEBUG] First 200 chars: {content[:200]}")

                            # Handle potential encoding issues
                            if isinstance(content, bytes):
                                content = content.decode('utf-8', errors='ignore')

                            # Try to extract JSON from the content (LLM might add extra text)
                            json_start = content.find('[')
                            json_end = content.rfind(']') + 1

                            if json_start == -1:
                                # Try to find object instead
                                json_start = content.find('{')
                                json_end = content.rfind('}') + 1

                            if json_start != -1 and json_end > json_start:
                                json_content = content[json_start:json_end]
                                extracted_data = json.loads(json_content)
                            else:
                                extracted_data = json.loads(content)

                            if isinstance(extracted_data, list):
                                for item in extracted_data:
                                    try:
                                        # Ensure competitor field is set
                                        item['competitor'] = competitor
                                        product = Product(**item)

                                        # Enforce brand / CPU rules (Dell/HP/Lenovo, Intel 8th-gen+)
                                        if not self._is_relevant_product(product):
                                            # Count products that fail Jeff's 8th-gen+ Intel filter
                                            self.skipped_counts[competitor] += 1
                                            continue

                                        # Ensure URL is absolute
                                        if product.url and not product.url.startswith('http'):
                                            base_url = COMPETITORS[competitor]["base_url"]
                                            product.url = base_url + product.url
                                        products.append(product)
                                    except Exception as e:
                                        print(f"   [WARNING] Error parsing product: {e}")
                                        continue
                            elif isinstance(extracted_data, dict):
                                # Sometimes LLM returns a single object instead of array
                                try:
                                    # Ensure competitor field is set
                                    extracted_data['competitor'] = competitor
                                    product = Product(**extracted_data)

                                    # Enforce brand / CPU rules; if this single object
                                    # does not qualify, treat the page as having no products
                                    # from our target set so fallback logic can run.
                                    if not self._is_relevant_product(product):
                                        # Count this as skipped and let fallback logic run
                                        self.skipped_counts[competitor] += 1
                                        return []

                                    if product.url and not product.url.startswith('http'):
                                        base_url = COMPETITORS[competitor]["base_url"]
                                        product.url = base_url + product.url
                                    products.append(product)
                                except Exception as e:
                                    print(f"   [WARNING] Error parsing product: {e}")

                        except json.JSONDecodeError as e:
                            print(f"   [ERROR] JSON decode error: {e}")
                            print(f"   Raw content: {result.extracted_content[:200]}...")
                        except Exception as e:
                            print(f"   [ERROR] Error processing extracted content: {e}")
                    else:
                        print(f"   [WARNING] No extracted content (page may be empty or LLM failed)")
                else:
                    error_msg = result.error_message if hasattr(result, 'error_message') else 'Unknown error'
                    print(f"   [ERROR] Crawl failed: {error_msg}")

                # Fallback: if LLM-based extraction produced no products but we have markdown,
                # use the older heuristic markdown parser from competitor_price_scraper.
                if not products and hasattr(result, "markdown") and getattr(result, "markdown", None):
                    try:
                        from competitor_price_scraper import CompetitorPriceScraper
                        print("   [INFO] No products from LLM extraction; falling back to heuristic markdown parser.")

                        fallback_scraper = CompetitorPriceScraper(use_llm=False)
                        fallback_products = fallback_scraper.parse_products_from_markdown(
                            result.markdown.raw_markdown,
                            competitor,
                            product_type,
                            url,
                        )
                        print(f"   [INFO] Fallback parser found {len(fallback_products)} products")

                        for legacy_product in fallback_products:
                            try:
                                legacy_cfg = getattr(legacy_product, "config", None)
                                new_cfg = ProductConfig(
                                    processor=getattr(legacy_cfg, "processor", None) if legacy_cfg else None,
                                    ram=getattr(legacy_cfg, "ram", None) if legacy_cfg else None,
                                    storage=getattr(legacy_cfg, "storage", None) if legacy_cfg else None,
                                    cosmetic_grade=getattr(legacy_cfg, "cosmetic_grade", None) if legacy_cfg else None,
                                    form_factor=getattr(legacy_cfg, "form_factor", None) if legacy_cfg else None,
                                    screen_resolution=getattr(legacy_cfg, "screen_resolution", None) if legacy_cfg else None,
                                    screen_size=getattr(legacy_cfg, "screen_size", None) if legacy_cfg else None,
                                )

                                product = Product(
                                    brand=getattr(legacy_product, "brand", None),
                                    model=getattr(legacy_product, "model", None),
                                    product_type=getattr(legacy_product, "product_type", product_type),
                                    title=getattr(legacy_product, "title", None),
                                    price=getattr(legacy_product, "price", None),
                                    url=getattr(legacy_product, "url", None),
                                    config=new_cfg,
                                    availability=getattr(legacy_product, "availability", None),
                                    competitor=competitor,
                                )

                                # Enforce brand / CPU rules; skip non-qualifying PCL products
                                if not self._is_relevant_product(product):
                                    # Count products dropped by the 8th-gen+ Intel filter
                                    self.skipped_counts[competitor] += 1
                                    continue

                                # Ensure URL is absolute
                                if product.url and not product.url.startswith('http'):
                                    base_url = COMPETITORS[competitor]["base_url"]
                                    product.url = base_url + product.url

                                products.append(product)
                            except Exception as conv_e:
                                print(f"   [WARNING] Error converting fallback product: {conv_e}")
                    except ImportError as ie:
                        print(f"   [WARNING] Fallback parser not available: {ie}")
                    except Exception as fe:
                        print(f"   [WARNING] Fallback markdown parsing failed: {fe}")

        except Exception as e:
            print(f"   [ERROR] Error: {str(e)}")

        return products

    async def scrape_competitor(self, competitor: str, config: Dict) -> List[Product]:
        """Scrape all URLs for a competitor"""
        print(f"\n{'='*80}")
        print(f"[SCRAPER] Scraping {competitor}")
        print(f"{'='*80}")

        all_products = []

        for url in config["urls"]:
            products = await self.scrape_url(url, competitor)
            all_products.extend(products)

            # Be respectful - delay between pages
            await asyncio.sleep(3)

        print(f"\n[SUCCESS] {competitor}: Found {len(all_products)} total products")
        return all_products

    async def scrape_all(self) -> Dict[str, List[Product]]:
        """Scrape all competitors"""
        results = {}

        for competitor, config in COMPETITORS.items():
            products = await self.scrape_competitor(competitor, config)
            results[competitor] = products

        return results

    def _save_incremental_results(self, competitor: str, products: List[Product]):
        """Save incremental results after each page scrape - merge with existing data"""
        try:
            filename = "competitor_prices.json"

            # Load existing data
            existing_data = {}
            existing_products = []
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # Get existing products for this competitor
                    if competitor in existing_data:
                        existing_products = existing_data[competitor].get('products', [])
            except FileNotFoundError:
                print(f"   [INFO] Creating new data file")

            # Convert new products to dict format for easier comparison
            new_products_dict = {}
            for product in products:
                # Use URL as unique key, or create a composite key if URL is missing
                key = product.url if product.url else f"{product.brand}_{product.model}_{product.price}"
                new_products_dict[key] = product.model_dump()

            # Merge with existing products - never remove existing ones
            merged_products = existing_products.copy()

            # Add new products that don't already exist
            new_additions = 0
            for key, product_dict in new_products_dict.items():
                # Check if this product already exists (by URL or by brand/model/price combination)
                exists = False
                for existing_product in merged_products:
                    existing_key = existing_product.get('url') if existing_product.get('url') else f"{existing_product.get('brand')}_{existing_product.get('model')}_{existing_product.get('price')}"
                    if existing_key == key:
                        exists = True
                        break

                if not exists:
                    merged_products.append(product_dict)
                    new_additions += 1

            # Create timestamped backup before updating (only if data exists)
            if existing_products:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"competitor_prices_backup_{timestamp}.json"

                # Save backup
                with open(backup_filename, 'w', encoding='utf-8', errors='ignore') as f:
                    json.dump(existing_data, f, indent=2, ensure_ascii=False)

                print(f"   [BACKUP] Created backup: {backup_filename}")

                # Clean up old backups (keep last 5)
                self._cleanup_old_backups()

            # Update only the current competitor's data
            existing_data[competitor] = {
                "competitor": competitor,
                "website": COMPETITORS[competitor]["base_url"],
                "scrape_date": datetime.now().isoformat(),
                "total_products": len(merged_products),
                "existing_products": len(existing_products),
                "new_additions": new_additions,
                "products": merged_products
            }

            # Save updated data
            with open(filename, 'w', encoding='utf-8', errors='ignore') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            print(f"   [MERGE] Merged data: {len(merged_products)} total products (+{new_additions} new) for {competitor}")

        except Exception as e:
            print(f"   [ERROR] Failed to save incremental results: {e}")
            import traceback
            traceback.print_exc()

    def _cleanup_old_backups(self, keep_count: int = 5):
        """Clean up old backup files, keeping only the most recent ones"""
        try:
            # Find all backup files
            backup_files = []
            for file in Path('.').glob('competitor_prices_backup_*.json'):
                try:
                    # Extract timestamp from filename
                    stat = file.stat()
                    backup_files.append((file, stat.st_mtime))
                except Exception:
                    continue
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Delete old backups beyond keep_count
            deleted_count = 0
            for file, _ in backup_files[keep_count:]:
                try:
                    file.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"   [WARNING] Failed to delete old backup {file}: {e}")
            
            if deleted_count > 0:
                print(f"   [CLEANUP] Deleted {deleted_count} old backup(s), kept {min(len(backup_files), keep_count)}")
        
        except Exception as e:
            print(f"   [WARNING] Backup cleanup failed: {e}")

    def save_results(self, results: Dict[str, List[Product]], filename: str = "competitor_prices.json"):
        """Save results to JSON file.

        Products passed into this method have already gone through Jeff's
        Dell/HP/Lenovo + Intel 8th‑gen+ filter. Here we only look up how many
        products were skipped during scraping so the dashboard can display it.
        """
        output = {}

        for competitor, products in results.items():
            # Products are already filtered when they reach save_results
            filtered: List[Product] = list(products)

            # How many products did we drop for this competitor during scraping?
            dropped = 0
            try:
                if hasattr(self, "skipped_counts"):
                    dropped = int(self.skipped_counts.get(competitor, 0))
            except Exception:
                dropped = 0

            if dropped:
                print(
                    f"[FILTER] {competitor}: dropped {dropped} products at save time "
                    f"that do not match Dell/HP/Lenovo Intel 8th-gen+ rule"
                )

            output[competitor] = {
                "competitor": competitor,
                "website": COMPETITORS[competitor]["base_url"],
                "scrape_date": datetime.now().isoformat(),
                "total_products": len(filtered),
                "skipped_products": dropped,
                "products": [p.model_dump() for p in filtered]
            }

        with open(filename, 'w', encoding='utf-8', errors='ignore') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] Results saved to {filename}")

    def print_summary(self, results: Dict[str, List[Product]]):
        """Print summary of results"""
        print("\n" + "="*80)
        print("[SUMMARY] SCRAPING SUMMARY")
        print("="*80)

        total = 0
        for competitor, products in results.items():
            count = len(products)
            total += count
            print(f"  {competitor:25} {count:4} products")

        print(f"  {'─'*25} {'─'*4}")
        print(f"  {'TOTAL':25} {total:4} products")
        print("="*80)


class ReviewScraper:
    """Scrapes review data from individual product pages"""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "deepseek")

        if self.provider == "deepseek":
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.model = "deepseek/deepseek-chat"
        else:
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.model = "openai/gpt-4o-mini"

    async def scrape_product_reviews(self, product_url: str) -> Optional[ReviewData]:
        """Scrape review data from a single product page"""
        try:
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
            )

            extraction_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(
                    provider=self.model,
                    api_token=self.api_key
                ),
                schema=ReviewData.model_json_schema(),
                extraction_type="schema",
                instruction="""
                Extract review and rating information from this product page.

                Look for:
                - Number of customer reviews (e.g., "47 reviews", "234 customer ratings")
                - Average star rating (e.g., "4.2 out of 5 stars")
                - Rating distribution (5-star, 4-star, 3-star, 2-star, 1-star counts)
                - "Best Seller" badges or indicators
                - "Top Rated" or "Editor's Choice" badges
                - Sales rank information

                Return a ReviewData object with all available fields.
                If no review data is found, return empty/null values.
                """
            )

            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=extraction_strategy,
                delay_before_return_html=3.0,
                page_timeout=60000,
                wait_for_images=False,
                remove_overlay_elements=True
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=product_url,
                    config=crawler_config
                )

                if result.success and result.extracted_content:
                    try:
                        review_data = ReviewData(**json.loads(result.extracted_content))
                        return review_data
                    except Exception as e:
                        print(f"   ⚠️  Error parsing review data: {e}")
                        return ReviewData()

                return ReviewData()

        except Exception as e:
            print(f"   ❌ Error scraping reviews: {str(e)}")
            return ReviewData()

    async def enrich_products_with_reviews(self, products: List[Product]) -> List[Product]:
        """Add review data to existing products"""
        print(f"\n🔍 Enriching {len(products)} products with review data...")

        enriched_products = []
        for i, product in enumerate(products):
            if product.url:
                print(f"   📝 [{i+1}/{len(products)}] Getting reviews for {product.title[:50]}...")

                try:
                    review_data = await self.scrape_product_reviews(product.url)
                    product.reviews = review_data
                    enriched_products.append(product)

                    # Be respectful - delay between products
                    await asyncio.sleep(2)

                except Exception as e:
                    print(f"   ⚠️  Failed to get reviews for {product.title}: {str(e)}")
                    enriched_products.append(product)
            else:
                enriched_products.append(product)

        return enriched_products

    def save_enriched_results(self, results: Dict[str, List[Product]], filename: str = "competitor_prices_with_reviews.json"):
        """Save results with review data to JSON file"""
        output = {}

        for competitor, products in results.items():
            output[competitor] = {
                "competitor": competitor,
                "website": COMPETITORS[competitor]["base_url"],
                "scrape_date": datetime.now().isoformat(),
                "total_products": len(products),
                "products_with_reviews": len([p for p in products if p.reviews and (p.reviews.review_count or p.reviews.average_rating)]),
                "products": [p.model_dump() for p in products]
            }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Results with review data saved to {filename}")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Main execution"""

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Scrape competitor prices")
    parser.add_argument('--competitor', type=str, help='Specific competitor to scrape (e.g., PCLiquidations)')
    parser.add_argument('--with-reviews', action='store_true', help='Also scrape review data from product pages')
    args = parser.parse_args()

    if args.competitor:
        # Scrape only the specified competitor
        if args.competitor not in COMPETITORS:
            print(f"❌ Unknown competitor: {args.competitor}")
            print(f"   Available: {', '.join(COMPETITORS.keys())}")
            return

        print("\n" + "="*80)
        print(f"[SCRAPER] Competitor Price Scraper v2 - {args.competitor} Only")
        print("="*80)
        print(f"\n[TARGET] Single competitor: {args.competitor}")
        print("[INFO] Extracting: Dell, HP, Lenovo products only")
        print("="*80)

        scraper = CompetitorScraper()

        # Scrape only the specified competitor
        products = await scraper.scrape_competitor(args.competitor, COMPETITORS[args.competitor])

        # Final hard filter (defensive) to enforce 8th-gen+ Intel rule
        filtered_products = [p for p in products if scraper._is_relevant_product(p)]
        if len(filtered_products) != len(products):
            print(
                f"[FILTER] {args.competitor}: dropped {len(products) - len(filtered_products)} "
                f"products in final hard 8th-gen+ Intel filter"
            )
        products = filtered_products

        # DEBUG: Print extracted products before saving
        print(f"\n{'='*80}")
        print("[DEBUG] Extracted Products Summary:")
        print(f"{'='*80}")
        for i, product in enumerate(products[:10], 1):  # Show first 10
            print(f"{i:2d}. {product.brand} {product.model} - ${product.price} ({product.product_type})")
        if len(products) > 10:
            print(f"... and {len(products)-10} more products")
        print(f"Total products found: {len(products)}")

        # Save results - load existing data and update only this competitor
        try:
            with open("competitor_prices.json", 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # Look up how many products we skipped for this competitor during scraping
        dropped_for_competitor = 0
        try:
            if hasattr(scraper, "skipped_counts"):
                dropped_for_competitor = int(scraper.skipped_counts.get(args.competitor, 0))
        except Exception:
            dropped_for_competitor = 0

        # Update only the specified competitor
        existing_data[args.competitor] = {
            "competitor": args.competitor,
            "website": COMPETITORS[args.competitor]["base_url"],
            "scrape_date": datetime.now().isoformat(),
            "total_products": len(products),
            "skipped_products": dropped_for_competitor,
            "products": [p.model_dump() for p in products]
        }

        # Save updated data
        with open("competitor_prices.json", 'w') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] {args.competitor} scraping complete!")
        print(f"[DASHBOARD] View results in dashboard: http://localhost:8080")

    else:
        # Scrape all competitors (original behavior)
        print("\n" + "="*80)
        print("[SCRAPER] Competitor Price Scraper v2")
        print("="*80)
        print("\n[LIST] Scraping 5 competitors:")
        for name in COMPETITORS.keys():
            print(f"   • {name}")
        print("\n[TARGET] Extracting: Dell, HP, Lenovo products only")
        print("="*80)

        scraper = CompetitorScraper()

        # Scrape all competitors
        results = await scraper.scrape_all()

        # Save results
        scraper.save_results(results)

        # Optionally enrich with review data
        if args.with_reviews:
            print("\n" + "="*80)
            print("[PROCESS] ENRICHING WITH REVIEW DATA")
            print("="*80)

            review_scraper = ReviewScraper()

            # Flatten all products for review scraping
            all_products = []
            for competitor_products in results.values():
                all_products.extend(competitor_products)

            print(f"[INFO] Will scrape reviews for {len(all_products)} products...")
            print("[WARNING] This will take a long time due to rate limiting...")

            # Enrich products with review data
            enriched_products = await review_scraper.enrich_products_with_reviews(all_products)

            # Group back by competitor
            enriched_results = {}
            for competitor in results.keys():
                competitor_products = [p for p in enriched_products if getattr(p, 'competitor', None) == competitor]
                enriched_results[competitor] = competitor_products

            # Save enriched results
            review_scraper.save_enriched_results(enriched_results)

            # Print summary with review data
            scraper.print_summary(enriched_results)

            # Count products with review data
            products_with_reviews = sum(1 for p in enriched_products if p.reviews and (p.reviews.review_count or p.reviews.average_rating))
            print(f"[STATS] Products with review data: {products_with_reviews}/{len(enriched_products)}")

        else:
            # Print summary
            scraper.print_summary(results)

        print("\n✅ Scraping complete!")
        print(f"📊 View results in dashboard: http://localhost:8080")


if __name__ == "__main__":
    asyncio.run(main())
