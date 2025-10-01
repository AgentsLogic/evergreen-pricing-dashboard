# 🚀 Quick Start Guide - Competitor Price Scraper

## ✅ What's Been Created

I've built a complete competitor pricing intelligence system for your MSRP project:

### 📁 Files Created

1. **`competitor_price_scraper.py`** - Main scraper (pattern-based, no API key needed)
2. **`advanced_scraper.py`** - AI-powered scraper (requires OpenAI API key)
3. **`price_dashboard.html`** - Beautiful web dashboard to view results
4. **`test_scraper.py`** - Test suite to verify everything works
5. **`competitor_prices.json`** - Sample data (will be replaced with real data)
6. **`COMPETITOR_SCRAPER_README.md`** - Full documentation
7. **`QUICK_START.md`** - This file!

## 🎯 What It Does

Automatically scrapes these competitor websites:
- ✅ **PCLiquidations.com**
- ✅ **DiscountElectronics.com**
- ✅ **SystemLiquidation.com**
- ✅ **DellRefurbished.com**

### Data Extracted for Each Product:

**Basic Info:**
- Brand (Dell, HP, Lenovo only)
- Model number
- Product type (Laptop/Desktop)
- Price (MSRP)

**Configuration:**
- ✅ Processor (i5-11th gen, i7-13th gen, etc.)
- ✅ RAM (8GB, 16GB, 32GB, 64GB)
- ✅ Storage (256GB SSD, 1TB HDD, etc.)
- ✅ Cosmetic Grade (A, B, C when available)

**Laptop-Specific:**
- ✅ Screen Resolution (HD, FHD, QHD, 4K UHD)
- ✅ Screen Size (14", 15.6", etc.)

**Desktop-Specific:**
- ✅ Form Factor (Tower, SFF, MFF/Tiny)

## 🏃 How to Use

### Option 1: View the Dashboard (Already Open!)

The dashboard is already running at: **http://localhost:8001/price_dashboard.html**

Features:
- 🔍 Filter by competitor, brand, type, price
- 📊 View statistics and charts
- 🔎 Search by model or specs
- 📥 Export to CSV

### Option 2: Run a Test Scrape

```bash
# Test the scraper without API key
python test_scraper.py
```

Choose option 1 to test a single page first.

### Option 3: Run Full Scraper (Basic - No API Key)

```bash
# Scrape all competitors using pattern matching
python competitor_price_scraper.py
```

This will:
1. Scrape all competitor websites
2. Extract product data
3. Save to `competitor_prices.json`
4. Show a summary report

### Option 4: Run Advanced AI Scraper (Recommended)

```bash
# Set your OpenAI API key first
export OPENAI_API_KEY="sk-your-key-here"

# Or on Windows:
set OPENAI_API_KEY=sk-your-key-here

# Run the advanced scraper
python advanced_scraper.py
```

Choose option 1 to test a single URL, or option 2 for all competitors.

**Why use the AI scraper?**
- ✅ More accurate extraction
- ✅ Better at handling different website layouts
- ✅ Extracts more detailed information
- ✅ Adapts to website changes

## 📊 Dashboard Features

### Filters
- **Competitor**: Filter by specific website
- **Brand**: Dell, HP, or Lenovo
- **Product Type**: Laptops or Desktops
- **Price Range**: Various price brackets
- **Search**: Find by model, processor, or any spec

### Statistics
- Total products found
- Average price
- Lowest price
- Highest price

### Charts
- Products by brand (pie chart)
- Price distribution (bar chart)

### Export
- Download filtered results as CSV
- Open in Excel or Google Sheets

## 🔧 Customization

### Add More Competitor URLs

Edit `competitor_price_scraper.py`:

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
    # Add new competitors here
}
```

### Schedule Regular Scraping

**Windows (Task Scheduler):**
1. Create a batch file: `scrape_daily.bat`
```batch
cd C:\Users\JR\Documents\PROJECTS\JEFF\crawl4ai
python advanced_scraper.py
```
2. Schedule it in Task Scheduler

**Linux/Mac (Cron):**
```bash
# Daily at 2 AM
0 2 * * * cd /path/to/crawl4ai && python advanced_scraper.py
```

## 📈 Next Steps

### 1. Test the System
```bash
python test_scraper.py
```

### 2. Run Your First Real Scrape
```bash
# If you have OpenAI API key:
python advanced_scraper.py

# Otherwise:
python competitor_price_scraper.py
```

### 3. View Results
Open the dashboard (already running):
http://localhost:8001/price_dashboard.html

### 4. Export Data
Click "Export to CSV" in the dashboard to download for analysis

### 5. Schedule Regular Updates
Set up automated scraping to track price changes over time

## 🎨 Dashboard Preview

The dashboard shows:
- **Header**: Total stats and action buttons
- **Filters**: Narrow down products by multiple criteria
- **Statistics Cards**: Key metrics at a glance
- **Charts**: Visual representation of data
- **Product Cards**: Detailed product listings with all specs

## 💡 Tips

1. **Start with test scraper** to verify websites are accessible
2. **Use AI scraper** for best results (requires API key)
3. **Check robots.txt** on competitor sites to be respectful
4. **Schedule regular scraping** to track price changes
5. **Export to CSV** for deeper analysis in Excel

## 🐛 Troubleshooting

### Dashboard shows no data
- Make sure `competitor_prices.json` exists
- Refresh the browser page
- Check browser console for errors

### Scraper finds no products
- Website structure may have changed
- Try the AI scraper instead
- Check if URLs are correct

### AI scraper fails
- Verify OpenAI API key is set
- Check API quota/credits
- Try basic scraper as fallback

## 📞 Support

For issues:
1. Check `COMPETITOR_SCRAPER_README.md` for detailed docs
2. Review error messages in terminal
3. Test with `test_scraper.py` first

## 🎉 You're All Set!

Your competitor pricing intelligence system is ready to use!

**Current Status:**
- ✅ Dashboard running at http://localhost:8001/price_dashboard.html
- ✅ Sample data loaded
- ✅ All scripts ready to run
- ✅ Documentation complete

**Next Action:**
Run a test scrape to get real data:
```bash
python test_scraper.py
```

---

**Happy Price Tracking! 🏷️**

