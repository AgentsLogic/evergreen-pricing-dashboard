"""
Competitor MSRP Price Scraper for Dell, HP, and Lenovo Products
Extracts pricing and configuration data from competitor websites
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
from pydantic import BaseModel, Field


# ============================================================================
# Data Models
# ============================================================================

class ProductConfig(BaseModel):
    """Product configuration details"""
    processor: Optional[str] = Field(None, description="Processor details (e.g., i5-11th gen, i7-13th gen)")
    ram: Optional[str] = Field(None, description="RAM size (e.g., 8GB, 16GB, 32GB)")
    storage: Optional[str] = Field(None, description="Hard drive size (e.g., 500GB, 1TB, 2TB)")
    cosmetic_grade: Optional[str] = Field(None, description="Cosmetic grade (A, B, C)")
    form_factor: Optional[str] = Field(None, description="Desktop form factor (Tower, SFF, MFF/Tiny)")
    screen_resolution: Optional[str] = Field(None, description="Laptop screen resolution (HD, FHD, QHD, 4K UHD)")
    screen_size: Optional[str] = Field(None, description="Screen size in inches")


class Product(BaseModel):
    """Product information"""
    brand: str = Field(..., description="Brand (Dell, HP, Lenovo)")
    model: str = Field(..., description="Model number")
    product_type: str = Field(..., description="Product type (Laptop or Desktop)")
    title: str = Field(..., description="Product title/name")
    price: Optional[float] = Field(None, description="Price in USD")
    price_text: Optional[str] = Field(None, description="Original price text")
    url: Optional[str] = Field(None, description="Product URL")
    config: ProductConfig = Field(default_factory=ProductConfig, description="Product configuration")
    availability: Optional[str] = Field(None, description="Stock availability")
    condition: Optional[str] = Field(None, description="Product condition (Refurbished, New, etc)")


class CompetitorData(BaseModel):
    """Competitor website data"""
    competitor: str
    website: str
    scrape_date: str
    products: List[Product]
    total_products: int


# ============================================================================
# Competitor Website Configurations
# ============================================================================

COMPETITORS = {
    "PCLiquidations": {
        "url": "https://www.pcliquidations.com",
        "laptop_urls": [
            "https://www.pcliquidations.com/refurbished-laptops",
        ],
        "desktop_urls": [
            "https://www.pcliquidations.com/refurbished-desktop-computers",
        ]
    },
    "DiscountElectronics": {
        "url": "https://www.discountelectronics.com",
        "laptop_urls": [
            "https://discountelectronics.com/refurbished-laptops/",
        ],
        "desktop_urls": [
            "https://discountelectronics.com/refurbished-computers/",
        ]
    },
    "SystemLiquidation": {
        "url": "https://www.systemliquidation.com",
        "laptop_urls": [
            "https://systemliquidation.com/collections/refurbished-laptops",
            "https://systemliquidation.com/collections/refurbished-mobile-workstations",
        ],
        "desktop_urls": [
            "https://systemliquidation.com/collections/refurbished-desktop-computers",
        ]
    },
    "DellRefurbished": {
        "url": "https://www.dellrefurbished.com",
        "laptop_urls": [
            "https://www.dellrefurbished.com/laptops",
        ],
        "desktop_urls": [
            "https://www.dellrefurbished.com/desktop-computers",
            "https://www.dellrefurbished.com/computer-workstation",
        ]
    },
    "DiscountPC": {
        "url": "https://discountpc.com",
        "laptop_urls": [
            "https://discountpc.com/collections/laptops",
        ],
        "desktop_urls": [
            "https://discountpc.com/collections/desktops",
        ]
    },
    "EvergreenElectronics": {
        "url": "https://evergreenelectronics.com",
        "laptop_urls": [
            "https://evergreenelectronics.com/collections/certified-refurbished-laptops",
        ],
        "desktop_urls": [
            "https://evergreenelectronics.com/collections/windows-11-computers",
        ]
    },
}


# ============================================================================
# LLM Extraction Schema
# ============================================================================

LLM_EXTRACTION_PROMPT = """
Extract product information from this webpage. Focus on Dell, HP, and Lenovo laptops and desktops only.

For each product, extract:
1. Brand (Dell, HP, or Lenovo)
2. Model number (e.g., Latitude 5420, EliteBook 840, ThinkPad T14)
3. Product type (Laptop or Desktop)
4. Title/Name
5. Price (convert to numeric value)
6. Configuration details:
   - Processor (e.g., "i5-11th gen", "i7-13th gen", "Ryzen 5")
   - RAM (e.g., "8GB", "16GB", "32GB")
   - Storage (e.g., "256GB SSD", "1TB HDD", "512GB SSD")
   - Cosmetic Grade (if mentioned: Grade A, B, or C)
   - Form Factor for desktops (Tower, SFF, MFF, Tiny)
   - Screen Resolution for laptops (HD/1366x768, FHD/1920x1080, QHD/2560x1440, 4K UHD/3840x2160)
   - Screen Size for laptops (e.g., "14 inch", "15.6 inch")
7. Product URL
8. Availability/Stock status
9. Condition (Refurbished, New, etc.)

Only include products from Dell, HP, or Lenovo. Ignore all other brands.
"""


# ============================================================================
# Helper Functions
# ============================================================================

def parse_brand_from_text(text: str) -> Optional[str]:
    """Extract brand from product text"""
    text_lower = text.lower()
    if 'dell' in text_lower:
        return 'Dell'
    elif 'hp' in text_lower or 'hewlett' in text_lower:
        return 'HP'
    elif 'lenovo' in text_lower:
        return 'Lenovo'
    return None


def parse_price(price_text: str) -> Optional[float]:
    """Extract numeric price from text"""
    if not price_text:
        return None
    # Remove currency symbols and extract number
    price_match = re.search(r'[\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', price_text.replace(',', ''))
    if price_match:
        return float(price_match.group(1))
    return None


def classify_product_type(title: str, description: str = "") -> str:
    """Determine if product is laptop or desktop"""
    text = (title + " " + description).lower()

    laptop_keywords = ['laptop', 'notebook', 'latitude', 'precision mobile', 'elitebook', 'probook', 'thinkpad']
    desktop_keywords = ['desktop', 'optiplex', 'precision tower', 'precision sff', 'elitedesk', 'prodesk', 'thinkcentre', 'tower', 'sff', 'mff', 'tiny']

    for keyword in laptop_keywords:
        if keyword in text:
            return 'Laptop'

    for keyword in desktop_keywords:
        if keyword in text:
            return 'Desktop'

    return 'Unknown'


def extract_processor_info(text: str) -> Optional[str]:
    """Extract processor information from text"""
    text_lower = text.lower()

    # Enhanced patterns for Intel processors
    intel_patterns = [
        r'i([3579])-(\d{1,2})(?:th|st|nd|rd)?\s*gen(?:eration)?',
        r'intel\s*(?:core\s*)?i([3579])-(\d{1,2})(?:th|st|nd|rd)?\s*gen',
        r'core\s*i([3579])-(\d{1,2})(?:th|st|nd|rd)?\s*gen',
        r'i([3579])-(\d{1,2})\s*(?:gen|generation)',
    ]

    for pattern in intel_patterns:
        intel_match = re.search(pattern, text_lower)
        if intel_match:
            return f"{intel_match.group(1).upper()}-{intel_match.group(2)}th gen"

    # Enhanced patterns for AMD processors
    amd_patterns = [
        r'ryzen\s*(\d+)\s*(\d{4})?',
        r'amd\s*ryzen\s*(\d+)\s*(\d{4})?',
        r'ryzen\s*(\d+)\s*pro\s*(\d{4})?',
    ]

    for pattern in amd_patterns:
        amd_match = re.search(pattern, text_lower)
        if amd_match:
            processor = f"Ryzen {amd_match.group(1)}"
            if amd_match.group(2):
                processor += f" {amd_match.group(2)}"
            return processor.title()

    # Look for specific processor models
    processor_keywords = [
        'celeron', 'pentium', 'xeon', 'athlon', 'i3', 'i5', 'i7', 'i9'
    ]

    for keyword in processor_keywords:
        if keyword in text_lower:
            # Extract the full processor name around the keyword
            pattern = rf'(\w*\s*{keyword}\s*\w*)'
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1).title()

    return None


def extract_ram_info(text: str) -> Optional[str]:
    """Extract RAM information from text"""
    text_lower = text.lower()

    # More specific patterns for RAM
    ram_patterns = [
        r'(\d+)\s*GB\s*(?:DDR|RAM|Memory|RAM\s*DDR)',
        r'(\d+)\s*GB\s*(?:DDR[3-5]|RAM\s+DDR[3-5])',
        r'(\d+)\s*GB\s*(?:PC[3-5]|RAM\s+PC[3-5])',
        r'(\d+)\s*GB\s*(?:SDRAM|RAM\s+SDRAM)',
        r'(\d+)\s*GB\s*(?:LPDDR|RAM\s+LPDDR)',
    ]

    for pattern in ram_patterns:
        ram_match = re.search(pattern, text_lower)
        if ram_match:
            ram_size = ram_match.group(1)
            # Only accept reasonable RAM sizes (1GB to 128GB)
            if 1 <= int(ram_size) <= 128:
                return f"{ram_size}GB"

    # Look for RAM in product specifications context
    if 'ram' in text_lower or 'memory' in text_lower:
        # Find numbers followed by GB in context of RAM/memory
        context_patterns = [
            r'(?:ram|memory)[\s:]+(\d+)\s*GB',
            r'(\d+)\s*GB[\s:]+(?:ram|memory)',
            r'(\d+)\s*GB\s+(?:DDR[3-5]|SDRAM|LPDDR)',
        ]

        for pattern in context_patterns:
            ram_match = re.search(pattern, text_lower)
            if ram_match:
                ram_size = ram_match.group(1)
                if 1 <= int(ram_size) <= 128:
                    return f"{ram_size}GB"

    return None


def extract_storage_info(text: str) -> Optional[str]:
    """Extract storage information from text"""
    text_lower = text.lower()

    # Enhanced patterns for storage
    storage_patterns = [
        r'(\d+(?:\.\d+)?)\s*(GB|TB)\s*(?:SSD|HDD|NVMe|M\.2|Hard\s*Drive|Solid\s*State)',
        r'(\d+(?:\.\d+)?)\s*(GB|TB)\s+(?:SSD|HDD|NVMe|M\.2)',
        r'(?:SSD|HDD|NVMe|M\.2)[\s:]+(\d+(?:\.\d+)?)\s*(GB|TB)',
        r'(\d+(?:\.\d+)?)\s*(GB|TB)[\s:]+(?:SSD|HDD|NVMe|M\.2)',
    ]

    for pattern in storage_patterns:
        storage_match = re.search(pattern, text_lower)
        if storage_match:
            size = storage_match.group(1)
            unit = storage_match.group(2).upper()
            return f"{size}{unit}"

    # Look for storage in product specifications context
    if any(keyword in text_lower for keyword in ['storage', 'hard drive', 'ssd', 'hdd']):
        # Find numbers followed by GB/TB in context of storage
        context_patterns = [
            r'(?:storage|hard\s*drive|ssd|hdd)[\s:]+(\d+(?:\.\d+)?)\s*(GB|TB)',
            r'(\d+(?:\.\d+)?)\s*(GB|TB)[\s:]+(?:storage|hard\s*drive|ssd|hdd)',
        ]

        for pattern in context_patterns:
            storage_match = re.search(pattern, text_lower)
            if storage_match:
                size = storage_match.group(1)
                unit = storage_match.group(2).upper()
                return f"{size}{unit}"

    return None


def extract_screen_resolution(text: str) -> Optional[str]:
    """Extract screen resolution from text"""
    text_lower = text.lower()

    if '3840' in text or '2160' in text or '4k' in text_lower or 'uhd' in text_lower:
        return '4K UHD (3840x2160)'
    elif '2560' in text or '1440' in text or 'qhd' in text_lower or '2k' in text_lower:
        return 'QHD (2560x1440)'
    elif '1920' in text or '1080' in text or 'fhd' in text_lower or 'full hd' in text_lower:
        return 'FHD (1920x1080)'
    elif '1366' in text or '768' in text or text_lower.count('hd') > 0:
        return 'HD (1366x768)'

    return None


def extract_form_factor(text: str) -> Optional[str]:
    """Extract desktop form factor from text"""
    text_lower = text.lower()

    if 'tiny' in text_lower or 'mff' in text_lower or 'micro' in text_lower:
        return 'MFF/Tiny'
    elif 'sff' in text_lower or 'small form' in text_lower:
        return 'SFF'
    elif 'tower' in text_lower or 'mt' in text_lower:
        return 'Tower'

    return None


# ============================================================================
# Main Scraper Class
# ============================================================================

class CompetitorPriceScraper:
    """Main scraper for competitor pricing data"""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.results: Dict[str, CompetitorData] = {}

    async def scrape_competitor(self, competitor_name: str, config: dict) -> CompetitorData:
        """Scrape a single competitor website"""
        print(f"\n{'='*80}")
        print(f"🔍 Scraping {competitor_name} - {config['url']}")
        print(f"{'='*80}\n")

        all_products = []

        # Scrape laptop pages with pagination
        print(f"📱 Scraping Laptop Pages...")
        for url in config.get('laptop_urls', []):
            products = await self.scrape_pages_with_pagination(url, competitor_name, 'Laptop')
            all_products.extend(products)
            print(f"   ✓ Found {len(products)} laptops from {url} (multiple pages)")

        # Scrape desktop pages with pagination
        print(f"🖥️  Scraping Desktop Pages...")
        for url in config.get('desktop_urls', []):
            products = await self.scrape_pages_with_pagination(url, competitor_name, 'Desktop')
            all_products.extend(products)
            print(f"   ✓ Found {len(products)} desktops from {url} (multiple pages)")

        # Filter for Dell, HP, Lenovo only
        filtered_products = [p for p in all_products if p.brand in ['Dell', 'HP', 'Lenovo']]

        # Enrich PCLiquidations products with missing Grade by visiting product pages
        if competitor_name == 'PCLiquidations':
            print("\nEnriching PCLiquidations products to capture cosmetic Grade...")
            filtered_products = await self.enrich_pcliquidations_grades_safe(filtered_products)

        print(f"\n✅ Total products found: {len(all_products)}")
        print(f"✅ Dell/HP/Lenovo products: {len(filtered_products)}")

        return CompetitorData(
            competitor=competitor_name,
            website=config['url'],
            scrape_date=datetime.now().isoformat(),
            products=filtered_products,
            total_products=len(filtered_products)
        )

    async def scrape_pages_with_pagination(self, base_url: str, competitor: str, product_type: str) -> List[Product]:
        """Scrape multiple pages with pagination for a given URL"""
        all_products = []

        try:
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
            )

            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_for_images=False,
                scan_full_page=True,
                delay_before_return_html=2.0,
            )

            max_pages = 20  # Limit to prevent endless scraping
            page_num = 1

            async with AsyncWebCrawler(config=browser_config) as crawler:
                while page_num <= max_pages:
                    # Construct page URL
                    if page_num == 1:
                        current_url = base_url
                    else:
                        current_url = self.construct_page_url(base_url, competitor, page_num)

                    print(f"     📄 Page {page_num}: {current_url}")

                    try:
                        result = await crawler.arun(url=current_url, config=crawler_config)

                        if not result.success:
                            print(f"       ❌ Failed to load page {page_num}")
                            break

                        # Parse products from this page
                        products = self.parse_products_from_markdown(
                            result.markdown.raw_markdown,
                            competitor,
                            product_type,
                            current_url
                        )

                        if not products:
                            print(f"       ⚠️  No products found on page {page_num}")
                            # Check if page has pagination indicators
                            if not self.has_more_pages(result.markdown.raw_markdown):
                                print(f"       ✅ Reached end of products at page {page_num}")
                                break
                        else:
                            print(f"       ✅ Found {len(products)} products on page {page_num}")
                            all_products.extend(products)

                        # Small delay between pages
                        await asyncio.sleep(1)

                    except Exception as e:
                        print(f"       ❌ Error on page {page_num}: {str(e)}")
                        break

                    page_num += 1

                print(f"     📊 Total products from {base_url}: {len(all_products)} across {page_num-1} pages")

        except Exception as e:
            print(f"   ❌ Error with pagination for {base_url}: {str(e)}")

        return all_products

    def construct_page_url(self, base_url: str, competitor: str, page_num: int) -> str:
        """Construct the URL for a specific page based on competitor's pagination pattern"""
        if competitor == "PCLiquidations":
            # PCLiquidations uses Shopify-style pagination: /refurbished-laptops?page=2
            if '?' in base_url:
                return f"{base_url}&page={page_num}"
            else:
                return f"{base_url}?page={page_num}"

        elif competitor == "DiscountElectronics":
            # Similar to PCLiquidations
            if '?' in base_url:
                return f"{base_url}&paged={page_num}"
            else:
                return f"{base_url}?paged={page_num}"

        elif competitor == "SystemLiquidation":
            # Shopify style
            if '?' in base_url:
                return f"{base_url}&page={page_num}"
            else:
                return f"{base_url}?page={page_num}"

        elif competitor == "DellRefurbished":
            # Custom pagination pattern - may need adjustment
            if '?' in base_url:
                return f"{base_url}&page={page_num}"
            else:
                return f"{base_url}?page={page_num}"

        elif competitor == "DiscountPC":
            # Shopify style
            if '?' in base_url:
                return f"{base_url}&page={page_num}"
            else:
                return f"{base_url}?page={page_num}"

        # Default fallback
        if '?' in base_url:
            return f"{base_url}&page={page_num}"
        else:
            return f"{base_url}?page={page_num}"

    def has_more_pages(self, markdown_content: str) -> bool:
        """Check if there's likely more pages based on content"""
        content_lower = markdown_content.lower()

        # Look for common pagination indicators
        pagination_indicators = [
            'next page', 'next', '>', '»',
            'load more', 'see more', 'pagination',
            'page 2', 'page 3', 'page 4', 'page 5'
        ]

        return any(indicator in content_lower for indicator in pagination_indicators)

    async def scrape_page(self, url: str, competitor: str, product_type: str) -> List[Product]:
        """Scrape a single page"""
        products = []

        try:
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
            )

            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_for_images=False,
                scan_full_page=True,
                delay_before_return_html=2.0,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)

                if result.success:
                    # Parse the markdown content to extract products
                    products = self.parse_products_from_markdown(
                        result.markdown.raw_markdown,
                        competitor,
                        product_type,
                        url
                    )

        except Exception as e:
            print(f"   ❌ Error scraping {url}: {str(e)}")

        return products

    def parse_products_from_markdown(self, markdown: str, competitor: str,
                                    product_type: str, page_url: str) -> List[Product]:
        """Parse products from markdown content"""
        products = []

        # Split into sections that might contain product information
        sections = self.split_into_product_sections(markdown)

        for section in sections:
            if not section.strip():
                continue

            # Extract product information from each section
            product = self.extract_product_from_section(section, competitor, product_type, page_url)
            if product:
                products.append(product)

        return products

    def split_into_product_sections(self, markdown: str) -> List[str]:
        """Split markdown into potential product sections"""
        sections = []

        # Look for common product separators and patterns
        lines = markdown.split('\n')

        # Patterns that might indicate product boundaries
        separators = [
            r'^\s*[\$]\s*\d+',  # Lines starting with price
            r'^\s*Dell\s+',     # Dell product lines
            r'^\s*HP\s+',       # HP product lines
            r'^\s*Lenovo\s+',   # Lenovo product lines
            r'^\s*Latitude\s+', # Dell Latitude models
            r'^\s*Precision\s+', # Dell Precision models
            r'^\s*OptiPlex\s+', # Dell OptiPlex models
            r'^\s*EliteBook\s+', # HP EliteBook models
            r'^\s*ProBook\s+',  # HP ProBook models
            r'^\s*ThinkPad\s+', # Lenovo ThinkPad models
            r'^\s*ThinkCentre\s+', # Lenovo ThinkCentre models
        ]

        current_section = []
        in_product_section = False

        for line in lines:
            line_stripped = line.strip()

            # Check if this line starts a new product section
            is_separator = any(re.search(pattern, line_stripped, re.IGNORECASE) for pattern in separators)

            if is_separator or ('$' in line and any(char.isdigit() for char in line)):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
                in_product_section = True
            elif in_product_section and line_stripped:
                current_section.append(line)
            elif in_product_section and not line_stripped:
                # Empty line - might be end of product section
                if current_section:
                    sections.append('\n'.join(current_section))
                    current_section = []
                    in_product_section = False

        # Add final section if exists
        if current_section:
            sections.append('\n'.join(current_section))

        return sections

    def extract_product_from_section(self, section: str, competitor: str,
                                   product_type: str, page_url: str) -> Optional[Product]:
        """Extract product information from a section"""
        lines = section.split('\n')
        title = ""
        price = None
        price_text = ""

        # Find the main product line (usually contains brand and model)
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Look for brand and model information
            brand = parse_brand_from_text(line_stripped)
            if brand:
                title = line_stripped
                break

        # If no clear brand found, use first meaningful line
        if not title:
            for line in lines:
                line_stripped = line.strip()
                if (line_stripped and
                    len(line_stripped) > 10 and
                    not line_stripped.startswith('[') and
                    not line_stripped.startswith('*')):
                    title = line_stripped
                    break

        if not title:
            return None

        # Extract price
        for line in lines:
            if '$' in line and any(char.isdigit() for char in line):
                price = parse_price(line)
                if price:
                    price_text = line.strip()
                    break

        if not price:
            return None

        # Extract brand
        brand = parse_brand_from_text(title)

        # Extract model (look for specific model patterns)
        model = self.extract_model_from_title(title)

        # Extract configuration details from all lines in section
        all_text = ' '.join(lines)

        config = ProductConfig(
            processor=extract_processor_info(all_text),
            ram=extract_ram_info(all_text),
            storage=extract_storage_info(all_text),
            cosmetic_grade=self.extract_cosmetic_grade(all_text),
        )

        if product_type == 'Laptop':
            config.screen_resolution = extract_screen_resolution(all_text)
            config.screen_size = self.extract_screen_size(all_text)
        else:
            config.form_factor = extract_form_factor(all_text)

        # Try to extract a direct product URL from this section (e.g., /p12345-...)
        product_url = self.extract_product_url_from_section(section, competitor)
        final_url = product_url or page_url

        # Clean the title to remove markdown formatting
        cleaned_title = clean_markdown_text(title)

        return Product(
            brand=brand or "Unknown",
            model=model,
            product_type=product_type,
            title=cleaned_title[:200],  # Limit title length
            price=price,
            price_text=price_text,
            url=final_url,
            config=config
        )

    def extract_model_from_title(self, title: str) -> str:
        """Extract model number from product title"""
        # Common model patterns
        model_patterns = [
            r'Latitude\s+(\w+\s*\d+)',
            r'Precision\s+(\w+\s*\d+)',
            r'OptiPlex\s+(\w+\s*\d+)',
            r'EliteBook\s+(\w+\s*\d+)',
            r'ProBook\s+(\w+\s*\d+)',
            r'ThinkPad\s+(\w+\s*\d+)',
            r'ThinkCentre\s+(\w+\s*\d+)',
            r'(\w+\s*\d+)\s*(?:inch|")',  # Generic model with size
        ]

        for pattern in model_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""


    def extract_product_url_from_section(self, section: str, competitor: str) -> Optional[str]:
        """Try to extract a product detail URL from a section.
        For PCLiquidations, product pages look like /p12345-some-slug
        """
        try:
            # Absolute URL first
            m_abs = re.search(r'(https?://[^\s"\)\]]*?/p\d{5,}-[a-z0-9\-]+)', section, re.IGNORECASE)
            if m_abs:
                return m_abs.group(1)

            # Relative URL like /p125225-dell-latitude-3510-15
            m_rel = re.search(r'\b(/p\d{5,}-[a-z0-9\-]+)', section, re.IGNORECASE)
            if m_rel:
                base = COMPETITORS.get(competitor, {}).get('url', '').rstrip('/')
                if base:
                    return f"{base}{m_rel.group(1)}"
        except Exception:
            pass
        return None

    async def enrich_pcliquidations_grades(self, products: List[Product]) -> List[Product]:
        """Visit PCLiquidations product pages to fill missing cosmetic grades."""
        targets = [p for p in products if (p.config is not None and p.config.cosmetic_grade in (None, '')) and p.url and 'pcliquidations.com' in p.url]
        if not targets:
            return products

        print(f"   8157 Enriching {len(targets)} products with Grade from product pages...")

        browser_config = BrowserConfig(headless=True, verbose=False)
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for_images=False,
            scan_full_page=True,
            delay_before_return_html=2.0,
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for p in targets:
                    try:
                        res = await crawler.arun(url=p.url, config=crawler_config)
                        if res.success:
                            page_text = (res.markdown.raw_markdown or '') + ' ' + (res.metadata.get('title', '') or '')
                            grade = self.extract_cosmetic_grade(page_text)
                            if grade:
                                p.config.cosmetic_grade = grade
                                # Also, if our model was blank, try to refine from H1/title
                                if not p.model:
                                    p.model = self.extract_model_from_title(page_text)
                    except Exception as e:
                        print(f"      6a7 Unable to enrich grade for {p.url}: {e}")
        except Exception as e:
            print(f"   6a8 Grade enrichment session error: {e}")

        return products

    async def enrich_pcliquidations_grades_safe(self, products: List[Product]) -> List[Product]:
        """Visit PCLiquidations product pages and extract all grade variants as separate products."""
        targets = [p for p in products if p.url and 'pcliquidations.com' in p.url]
        if not targets:
            return products

        print(f"   Enriching {len(targets)} PCLiquidations products with all grade variants...")

        browser_config = BrowserConfig(headless=True, verbose=False)
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for_images=False,
            scan_full_page=True,
            delay_before_return_html=2.0,
        )

        enriched_products = []

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for p in targets:
                    try:
                        res = await crawler.arun(url=p.url, config=crawler_config)
                        if res.success:
                            page_text = (res.markdown.raw_markdown or '') + ' ' + (res.metadata.get('title', '') or '')

                            # Extract all grade variants from this page
                            grade_variants = self.extract_all_grade_variants(page_text, p)

                            if grade_variants:
                                enriched_products.extend(grade_variants)
                                print(f"      ✓ Found {len(grade_variants)} grade variants for {p.title[:50]}...")
                            else:
                                # If no grades found, keep original product
                                enriched_products.append(p)
                                print(f"      ⚠️ No grade variants found for {p.title[:50]}...")
                        else:
                            # If page failed to load, keep original product
                            enriched_products.append(p)
                            print(f"      ❌ Failed to load page for {p.title[:50]}...")
                    except Exception as e:
                        # If error occurred, keep original product
                        enriched_products.append(p)
                        print(f"      ❌ Error processing {p.title[:50]}...: {e}")

        except Exception as e:
            print(f"   ❌ Grade enrichment session error: {e}")
            return products

        print(f"   ✅ PCLiquidations enrichment complete! {len(enriched_products)} total products after enrichment")
        return enriched_products


    def extract_all_grade_variants(self, page_text: str, original_product: Product) -> List[Product]:
        """Extract all grade variants from a PCLiquidations product page"""
        variants = []

        # Look for grade-specific pricing patterns in PCLiquidations pages
        # They typically have sections like "Grade A: $XXX", "Grade B: $XXX", etc.

        # Pattern 1: "Grade A: $XXX" format
        grade_price_pattern = r'Grade\s*([ABC])\s*[:\-]?\s*[\$]?(\d+(?:,\d{3})*(?:\.\d{2})?)'
        matches = re.findall(grade_price_pattern, page_text, re.IGNORECASE)

        if matches:
            for grade, price_str in matches:
                grade = grade.upper()
                price = float(price_str.replace(',', ''))

                # Create a new product for this grade variant
                variant = Product(
                    brand=original_product.brand,
                    model=original_product.model,
                    product_type=original_product.product_type,
                    title=f"{original_product.title} (Grade {grade})",
                    price=price,
                    price_text=f"${price:.2f}",
                    url=original_product.url,
                    config=ProductConfig(
                        processor=original_product.config.processor,
                        ram=original_product.config.ram,
                        storage=original_product.config.storage,
                        cosmetic_grade=f"Grade {grade}",
                        form_factor=original_product.config.form_factor,
                        screen_resolution=original_product.config.screen_resolution,
                        screen_size=original_product.config.screen_size
                    ),
                    availability=original_product.availability,
                    condition=original_product.condition
                )
                variants.append(variant)

        # If no structured grade patterns found, try to extract from product options
        if not variants:
            # Look for grade mentions and associated prices
            grade_mentions = []
            if 'grade a' in page_text.lower():
                grade_mentions.append(('A', 'grade a'))
            if 'grade b' in page_text.lower():
                grade_mentions.append(('B', 'grade b'))
            if 'grade c' in page_text.lower():
                grade_mentions.append(('C', 'grade c'))

            # Try to find prices near each grade mention
            for grade, grade_keyword in grade_mentions:
                # Look for price within 100 characters of grade mention
                grade_pos = page_text.lower().find(grade_keyword)
                if grade_pos != -1:
                    # Extract text around the grade mention
                    start = max(0, grade_pos - 100)
                    end = min(len(page_text), grade_pos + 100)
                    context = page_text[start:end]

                    # Look for price in this context
                    price_match = re.search(r'[\$](\d+(?:,\d{3})*(?:\.\d{2})?)', context)
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))

                        variant = Product(
                            brand=original_product.brand,
                            model=original_product.model,
                            product_type=original_product.product_type,
                            title=f"{original_product.title} (Grade {grade})",
                            price=price,
                            price_text=f"${price:.2f}",
                            url=original_product.url,
                            config=ProductConfig(
                                processor=original_product.config.processor,
                                ram=original_product.config.ram,
                                storage=original_product.config.storage,
                                cosmetic_grade=f"Grade {grade}",
                                form_factor=original_product.config.form_factor,
                                screen_resolution=original_product.config.screen_resolution,
                                screen_size=original_product.config.screen_size
                            ),
                            availability=original_product.availability,
                            condition=original_product.condition
                        )
                        variants.append(variant)

        # If still no variants found, try one more approach - look for multiple price points
        if not variants:
            # Extract all prices from the page
            all_prices = re.findall(r'[\$](\d+(?:,\d{3})*(?:\.\d{2})?)', page_text)
            unique_prices = list(set(float(p.replace(',', '')) for p in all_prices))

            # If we find multiple prices, assume they correspond to different grades
            if len(unique_prices) >= 2:
                # Sort prices and assume lowest is Grade C, highest is Grade A
                unique_prices.sort()
                grade_order = ['C', 'B', 'A']  # Lowest price = Grade C, highest = Grade A

                for i, price in enumerate(unique_prices[:3]):  # Max 3 grades
                    if i < len(grade_order):
                        grade = grade_order[i]
                        variant = Product(
                            brand=original_product.brand,
                            model=original_product.model,
                            product_type=original_product.product_type,
                            title=f"{original_product.title} (Grade {grade})",
                            price=price,
                            price_text=f"${price:.2f}",
                            url=original_product.url,
                            config=ProductConfig(
                                processor=original_product.config.processor,
                                ram=original_product.config.ram,
                                storage=original_product.config.storage,
                                cosmetic_grade=f"Grade {grade}",
                                form_factor=original_product.config.form_factor,
                                screen_resolution=original_product.config.screen_resolution,
                                screen_size=original_product.config.screen_size
                            ),
                            availability=original_product.availability,
                            condition=original_product.condition
                        )
                        variants.append(variant)

        return variants

    def extract_cosmetic_grade(self, text: str) -> Optional[str]:
        """Extract cosmetic grade from text"""
        text_lower = text.lower()

        # Enhanced patterns for cosmetic grades
        grade_patterns = [
            r'grade\s*([ABC])',
            r'([ABC])\s*grade',
            r'condition[\s:]*([ABC])',
            r'([ABC])\s*condition',
            r'cosmetic[\s:]*([ABC])',
            r'([ABC])\s*cosmetic',
        ]

        for pattern in grade_patterns:
            grade_match = re.search(pattern, text_lower)
            if grade_match:
                grade = grade_match.group(1).upper()
                return f'Grade {grade}'

        # Direct keyword searches
        if 'grade a' in text_lower or 'grade-a' in text_lower or 'a grade' in text_lower:
            return 'Grade A'
        elif 'grade b' in text_lower or 'grade-b' in text_lower or 'b grade' in text_lower:
            return 'Grade B'
        elif 'grade c' in text_lower or 'grade-c' in text_lower or 'c grade' in text_lower:
            return 'Grade C'

        return None

    def extract_screen_size(self, text: str) -> Optional[str]:
        """Extract screen size from text"""
        # Look for patterns like "15.6 inch", "14"", "17 inch"
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:inch|")',
            r'(\d+(?:\.\d+)?)\s*inch',
        ]

        for pattern in size_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                size = match.group(1)
                return f"{size} inch"

        return None


def clean_markdown_text(text: str) -> str:
    """Clean markdown formatting from text"""
    if not text:
        return ""

    # Remove markdown image syntax: ![alt](url) or [alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]+\)', r'\1', text)

    # Remove markdown links but keep the text: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove common markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)     # Italic
    text = re.sub(r'__([^_]+)__', r'\1', text)     # Underline
    text = re.sub(r'_([^_]+)_', r'\1', text)       # Italic/Underline

    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove markdown lists
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove extra whitespace and newlines
    text = re.sub(r'\n+', ' ', text)  # Multiple newlines to space
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
    text = text.strip()

    return text


def clean_product_title(title: str) -> str:
    """Clean and format product title"""
    if not title:
        return ""

    # Apply general markdown cleaning
    title = clean_markdown_text(title)

    # Remove common unwanted phrases
    unwanted_phrases = [
        'Refurbished',
        'Used',
        'Grade A',
        'Grade B',
        'Grade C',
        'Lenovo',
        'Dell',
        'HP',
        'ThinkPad',
        'Latitude',
        'EliteBook',
        'ProBook',
        'Precision',
        'OptiPlex',
        'ThinkCentre'
    ]

    # Only remove these if they're standalone words (not part of model numbers)
    words = title.split()
    cleaned_words = []

    for word in words:
        # Keep words that are likely part of model numbers or important specs
        if (len(word) > 2 and
            not any(unwanted in word for unwanted in unwanted_phrases) and
            not word.isdigit()):
            cleaned_words.append(word)

    title = ' '.join(cleaned_words)

    # Limit length and ensure it's reasonable
    if len(title) > 100:
        title = title[:97] + "..."

        return title.strip()

    def save_results(self, filename: str = "competitor_prices.json"):
        """Save results to JSON file with merge logic to prevent data loss"""
        try:
            # Load existing data
            existing_data = {}
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except FileNotFoundError:
                print(f"   [INFO] Creating new data file")

            # Merge new results with existing data - never remove existing products
            for competitor, new_data in self.results.items():
                existing_products = existing_data.get(competitor, {}).get('products', [])

                # Convert new products to dict format for easier comparison
                new_products_dict = {}
                for product in new_data.products:
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

                # Update the competitor data with merged results
                existing_data[competitor] = {
                    "competitor": competitor,
                    "website": new_data.website,
                    "scrape_date": new_data.scrape_date,
                    "total_products": len(merged_products),
                    "existing_products": len(existing_products),
                    "new_additions": new_additions,
                    "products": merged_products
                }

                print(f"   [MERGE] {competitor}: {len(merged_products)} total products (+{new_additions} new)")

            # Save updated data
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            print(f"\n💾 Merged results saved to {filename}")

        except Exception as e:
            print(f"   [ERROR] Failed to save merged results: {e}")
            # Fallback to simple save if merge fails
            output = {
                competitor: data.model_dump()
                for competitor, data in self.results.items()
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"\n💾 Fallback save completed to {filename}")

    def generate_report(self) -> str:
        """Generate a summary report"""
        report = []
        report.append("\n" + "="*80)
        report.append("📊 COMPETITOR PRICING REPORT")
        report.append("="*80 + "\n")

        for competitor, data in self.results.items():
            report.append(f"\n{competitor} ({data.website})")
            report.append(f"  Scrape Date: {data.scrape_date}")
            report.append(f"  Total Products: {data.total_products}")

            # Count by brand
            brand_counts = {}
            for product in data.products:
                brand_counts[product.brand] = brand_counts.get(product.brand, 0) + 1

            for brand, count in brand_counts.items():
                report.append(f"    - {brand}: {count} products")

        return "\n".join(report)

    def save_results(self, filename: str = "competitor_prices.json"):
        """Save results to JSON file"""
        output = {
            competitor: data.model_dump()
            for competitor, data in self.results.items()
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Results saved to {filename}")

    async def scrape_all_competitors(self) -> Dict[str, CompetitorData]:
        """Scrape all competitor websites"""
        print("\n" + "="*80)
        print("🚀 Starting Competitor Price Scraping")
        print("="*80)

        for competitor_name, config in COMPETITORS.items():
            try:
                data = await self.scrape_competitor(competitor_name, config)
                self.results[competitor_name] = data
            except Exception as e:
                print(f"❌ Failed to scrape {competitor_name}: {str(e)}")

        return self.results


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Main execution function"""
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # Check for command line arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=str, help='Specific site to scrape (e.g., PCLiquidations)')
    args = parser.parse_args()

    scraper = CompetitorPriceScraper(use_llm=False)

    if args.site and args.site != 'all':
        # Scrape specific site only
        if args.site in COMPETITORS:
            print(f"\n🎯 Scraping specific site: {args.site}")
            data = await scraper.scrape_competitor(args.site, COMPETITORS[args.site])
            scraper.results[args.site] = data
        else:
            print(f"❌ Unknown site: {args.site}")
            print(f"Available sites: {', '.join(COMPETITORS.keys())}")
            return
    else:
        # Scrape all competitors
        results = await scraper.scrape_all_competitors()

    # Save results
    scraper.save_results("competitor_prices.json")

    # Generate and print report
    print(scraper.generate_report())

    print("\n✅ Scraping complete!")


if __name__ == "__main__":
    asyncio.run(main())
