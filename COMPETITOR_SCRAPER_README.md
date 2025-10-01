# 🏷️ Competitor MSRP Price Scraper

Automated web scraping solution for tracking competitor pricing on Dell, HP, and Lenovo laptops and desktops.

## 📋 Overview

This project scrapes pricing and configuration data from competitor websites:
- **PCLiquidations.com**
- **DiscountElectronics.com**
- **SystemLiquidation.com**
- **DellRefurbished.com**

### Data Extracted

For each product, the scraper extracts:

#### Basic Information
- Brand (Dell, HP, Lenovo)
- Model number
- Product type (Laptop/Desktop)
- Price (MSRP)
- Availability status

#### Configuration Details

**For ALL Products:**
- Processor (e.g., i5-11th gen, i7-13th gen, Ryzen 5)
- RAM (8GB, 16GB, 32GB, 64GB, etc.)
- Storage (256GB SSD, 1TB HDD, etc.)
- Cosmetic Grade (A, B, C - when available)

**For Laptops:**
- Screen Resolution:
  - HD (1366x768)
  - FHD (1920x1080)
  - QHD (2560x1440)
  - 4K UHD (3840x2160)
- Screen Size (14", 15.6", etc.)

**For Desktops:**
- Form Factor:
  - Tower
  - SFF (Small Form Factor)
  - MFF/Tiny (Micro Form Factor)

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+** installed
2. **Crawl4AI** installed (already done in your environment)
3. **OpenAI API Key** (for advanced LLM-based scraping)

### Installation

All dependencies are already installed in your environment!

### Basic Usage

#### Option 1: Basic Scraper (No API Key Required)

```bash
python competitor_price_scraper.py
```

This will:
- Scrape all competitor websites
- Extract product data using pattern matching
- Save results to `competitor_prices.json`
- Display a summary report

#### Option 2: Advanced AI-Powered Scraper (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Run the advanced scraper
python advanced_scraper.py
```

Choose option 1 to test a single URL first, or option 2 to scrape all competitors.

### View Results

Open the dashboard in your browser:

```bash
# Simply open this file in your browser
price_dashboard.html
```

Or use Python's built-in server:

```bash
python -m http.server 8000
# Then open: http://localhost:8000/price_dashboard.html
```

## 📊 Dashboard Features

The web dashboard (`price_dashboard.html`) provides:

### 🔍 Filtering
- Filter by competitor
- Filter by brand (Dell, HP, Lenovo)
- Filter by product type (Laptop/Desktop)
- Filter by price range
- Search by model, processor, or specs

### 📈 Analytics
- Total product count
- Average, minimum, and maximum prices
- Brand distribution chart
- Price distribution chart

### 📥 Export
- Export filtered results to CSV
- Download for Excel/Google Sheets analysis

### 🎨 Visual Features
- Color-coded by brand
- Responsive design
- Real-time filtering
- Interactive charts

## 📁 Project Files

```
crawl4ai/
├── competitor_price_scraper.py    # Basic scraper (pattern-based)
├── advanced_scraper.py            # AI-powered scraper (LLM-based)
├── price_dashboard.html           # Web dashboard for viewing results
├── competitor_prices.json         # Output data (generated after scraping)
└── COMPETITOR_SCRAPER_README.md   # This file
```

## 🔧 Configuration

### Adding/Modifying Competitor URLs

Edit `competitor_price_scraper.py` and modify the `COMPETITORS` dictionary:

```python
COMPETITORS = {
    "PCLiquidations": {
        "url": "https://www.pcliquidations.com",
        "laptop_urls": [
            "https://www.pcliquidations.com/collections/dell-laptops",
            # Add more URLs here
        ],
        "desktop_urls": [
            "https://www.pcliquidations.com/collections/dell-desktops",
            # Add more URLs here
        ]
    },
    # Add more competitors here
}
```

### Customizing Extraction

The advanced scraper uses AI to extract data. You can customize the extraction prompt in `advanced_scraper.py`:

```python
instruction="""
Your custom extraction instructions here...
"""
```

## 📊 Output Format

### JSON Structure

```json
{
  "PCLiquidations": {
    "competitor": "PCLiquidations",
    "website": "https://www.pcliquidations.com",
    "scrape_date": "2025-01-15T10:30:00",
    "total_products": 150,
    "products": [
      {
        "brand": "Dell",
        "model": "Latitude 5420",
        "product_type": "Laptop",
        "title": "Dell Latitude 5420 14\" Laptop",
        "price": 449.99,
        "url": "https://...",
        "config": {
          "processor": "i5-11th gen",
          "ram": "16GB",
          "storage": "256GB SSD",
          "cosmetic_grade": "Grade A",
          "screen_resolution": "FHD (1920x1080)",
          "screen_size": "14 inch"
        },
        "availability": "In Stock"
      }
    ]
  }
}
```

### CSV Export

The dashboard can export to CSV with these columns:
- Competitor
- Brand
- Type
- Model
- Price
- Processor
- RAM
- Storage
- Screen Resolution
- Form Factor
- Cosmetic Grade

## 🎯 Use Cases

### 1. Price Monitoring
Track competitor prices over time to adjust your pricing strategy.

### 2. Inventory Planning
See what configurations competitors are offering to plan your inventory.

### 3. Market Analysis
Analyze pricing trends by brand, configuration, and form factor.

### 4. Competitive Intelligence
Identify pricing gaps and opportunities in the market.

## 🔄 Automation

### Schedule Regular Scraping

**Windows (Task Scheduler):**
```bash
# Create a batch file: scrape_daily.bat
cd C:\Users\JR\Documents\PROJECTS\JEFF\crawl4ai
python advanced_scraper.py
```

**Linux/Mac (Cron):**
```bash
# Add to crontab (daily at 2 AM)
0 2 * * * cd /path/to/crawl4ai && python advanced_scraper.py
```

### Email Alerts

Add email notifications when prices change significantly (requires additional setup).

## 🐛 Troubleshooting

### Issue: No products found

**Solution:**
1. Check if the website structure has changed
2. Try the advanced scraper with LLM extraction
3. Verify the URLs are correct

### Issue: LLM extraction fails

**Solution:**
1. Verify your OpenAI API key is set correctly
2. Check your API quota/credits
3. Try with a different model (edit `provider` in code)

### Issue: Dashboard shows no data

**Solution:**
1. Make sure `competitor_prices.json` exists
2. Check the JSON file is valid
3. Refresh the browser page

## 📈 Advanced Features

### Custom Filters

Add custom filtering logic in the dashboard JavaScript:

```javascript
// Example: Filter by specific processor generation
filteredProducts = filteredProducts.filter(p => 
    p.config.processor && p.config.processor.includes('11th gen')
);
```

### Price Alerts

Monitor for specific price thresholds:

```python
# Add to scraper
for product in products:
    if product.price < 300 and product.config.ram == "16GB":
        send_alert(f"Great deal: {product.title} - ${product.price}")
```

### Historical Tracking

Save results with timestamps to track price changes:

```python
# Save with timestamp
filename = f"prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
```

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the Crawl4AI documentation
3. Check competitor website for structure changes

## 📝 Notes

- **Respect robots.txt**: Always check website terms of service
- **Rate limiting**: The scraper includes delays to avoid overwhelming servers
- **Data accuracy**: AI extraction is more accurate but requires API credits
- **Updates needed**: Websites change - you may need to update selectors/prompts

## 🎉 Next Steps

1. **Run a test scrape** with a single URL
2. **Review the results** in the dashboard
3. **Customize** the extraction for your specific needs
4. **Schedule** regular scraping for ongoing monitoring
5. **Integrate** with your pricing/inventory systems

---

**Happy Scraping! 🕷️**

