# Competitor Price Scraper - Technical Documentation

## Overview
This scraper extracts Dell, HP, and Lenovo products (laptops and desktops) from competitor websites. It uses Crawl4AI with optional LLM extraction and a fallback heuristic parser.

## Current Status

### Working Sites
- **TechtoSchool**: 25 products - extracts models from URLs (e.g., `hp-probook-640-g8` extracts as "HP ProBook 640 G8")
- **WisetekMarket**: 27+ products - has CPU info in filters, extraction working
- **Reebelo**: Uses brand-specific collection URLs (`/collections/dell-laptops`, etc.) - finds some products

### Broken Sites
- **TechForLess**: Cloudflare blocked - requires proxy service to bypass
- **DeepSeek API**: Insufficient Balance - no LLM extraction available

### API Requirements
The scraper requires a valid LLM API key. Current options:
1. **DeepSeek** (default): Set `DEEPSEEK_API_KEY` in `.env` - currently exhausted
2. **OpenAI**: Set `OPENAI_API_KEY` in `.env` - currently placeholder
3. **GroQ**: Set `GROQ_API_KEY` in `.env` - free tier available, currently placeholder

To use a different provider, edit `scraper_v2.py` line ~220:
```python
if self.provider == "deepseek":
    self.api_key = os.getenv("DEEPSEEK_API_KEY")
    self.model = "deepseek/deepseek-chat"
else:
    self.api_key = os.getenv("OPENAI_API_KEY")
    self.model = "openai/gpt-4o-mini"
```

## Architecture

### Main Files
- `scraper_v2.py`: Main scraper class (CompetitorScraper), handles LLM extraction and filtering
- `competitor_price_scraper.py`: Fallback heuristic parser, handles product extraction without LLM

### Data Flow
1. `scrape_url()` - Fetches each page with pagination
2. `_scrape_single_page()` - Attempts LLM extraction first
3. On LLM failure - Falls back to `competitor_price_scraper.py` heuristic parser
4. `_is_relevant_product()` - Filters for Dell/HP/Lenovo with Intel 8th gen+ CPUs
5. `_save_incremental_results()` - Merges with existing data, creates backups

### CPU Generation Detection
The scraper extracts CPU generation from:
- Direct CPU text: "Intel Core i7-1185G7" (extracts 11th gen from "1185")
- Model numbers: "ProBook 640 G8" (extracts 8th gen from "G8")
- URL patterns: `probook-640-g8` → generation G8

## Adding New Sites

### Step 1: Identify Collection URLs
1. Visit the competitor's website
2. Find the laptop/desktop collection pages
3. Note the URL patterns (e.g., `/collections/laptops`, `/laptops`, etc.)
4. For sites with filters, check if brand-specific URLs exist

### Step 2: Update COMPETITORS Dictionary
Edit `scraper_v2.py` ~line 87:
```python
"NewCompetitor": {
    "base_url": "https://example.com",
    "urls": [
        "https://example.com/laptops",
        "https://example.com/desktops",
    ]
},
```

### Step 3: Add to Fallback Parser (if LLM unavailable)
Edit `competitor_price_scraper.py` line ~58:
```python
COMPETITORS = {
    "NewCompetitor": {
        "url": "https://example.com",
        "laptop_urls": ["https://example.com/laptops"],
        "desktop_urls": ["https://example.com/desktops"]
    },
    # ... existing sites
}
```

### Step 4: Test
Run: `python scraper_v2.py --competitor NewCompetitor`

## Site-Specific Issues

### Reebelo
- Products loaded via JavaScript after page render
- Initial `/collections/laptops` only shows Apple products
- Solution: Use brand-specific URLs (`/collections/dell-laptops`, etc.)
- Laptops: Dell, HP, Lenovo each have dedicated collection pages

### TechForLess
- Cloudflare protection active
- Currently returns only Cloudflare verification page
- Solutions:
  1. Use a proxy service (ScraperAPI, ProxyCrawl, etc.)
  2. Use Selenium with undetected-chromedriver
  3. Contact TechForLess for API access

### TechtoSchool
- Products include generation in model name (e.g., "ProBook 640 G8")
- URL contains full model: `/products/hp-probook-640-g8-14-laptop`
- Extractor now parses URL to get model and generation

### WisetekMarket
- Has good filter structure with CPU info
- Products have clear price patterns
- Works well with fallback parser

## Filtering Rules

### Brand Filter
Only Dell, HP, and Lenovo products are kept:
```python
def _normalize_brand(self, brand):
    if "dell" in brand.lower(): return "Dell"
    if "hp" in brand.lower(): return "HP"
    if "lenovo" in brand.lower(): return "Lenovo"
    return None
```

### CPU Generation Filter
Only Intel 8th generation and newer:
```python
def _extract_intel_generation(self, text):
    # Parses patterns like:
    # - "i7-1185G7" → 11
    # - "G8" → 8
    # - "11th Gen" → 11
```

## Debugging

### Enable Debug Output
The scraper outputs detailed logs:
- `[PAGE]` - Current page being scraped
- `[SUCCESS]` - Products found
- `[WARNING]` - Issues encountered
- `[DEBUG]` - Extracted content length and first 200 chars

### Save Debug Markdown
Run `debug_all_sites.py` to save raw markdown for analysis:
```bash
python debug_all_sites.py
```
Output files: `*_debug.md`

### Test Specific Competitor
```bash
python scraper_v2.py --competitor TechtoSchool
```

## File Structure
```
competitor_prices.json       # Current scraped data
competitor_prices_backup_*.json  # Auto-created backups
scraper_v2.py               # Main LLM-powered scraper
competitor_price_scraper.py  # Fallback heuristic parser
debug_all_sites.py           # Debug script
```

## Dashboard
- `dashboard_server.py` - Flask server for displaying results
- `price_dashboard.html` - Frontend dashboard
- Run dashboard: `python dashboard_server.py`

## Known Limitations

1. **LLM Required for Best Results**: Without valid API key, fallback parser finds fewer products
2. **JavaScript Sites**: Some sites (Reebelo) require JS rendering not captured by default
3. **Cloudflare**: Cannot bypass without proxy service
4. **Rate Limiting**: DeepSeek API has been rate limited
5. **CPU Info**: Not always available in listing - may need product page visits

## Next Steps for Agent

1. **Get valid API key**: OpenAI, GroQ, or add funds to DeepSeek
2. **Test Reebelo**: Verify brand-specific URLs capture Dell/HP/Lenovo products
3. **Improve fallback parser**: Current parser misses many products on complex pages
4. **Add TechForLess proxy**: If Cloudflare continues blocking, use proxy service
5. **Add more sites**: Follow the "Adding New Sites" section above

## API Keys Required
Get keys from:
- DeepSeek: https://platform.deepseek.com/
- OpenAI: https://platform.openai.com/
- GroQ: https://console.groq.com/ (free tier available)

## Contact
For issues or questions, check:
1. This document
2. `DATA_PERSISTENCE_FIXES.md` for data handling issues
3. `requirements.txt` for dependencies