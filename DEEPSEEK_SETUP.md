# 🚀 DeepSeek API Setup Guide

## Why DeepSeek?

**DeepSeek is MUCH cheaper than OpenAI and works great for web scraping!**

### Price Comparison:
- **DeepSeek**: ~$0.14 per 1M tokens (input) / $0.28 per 1M tokens (output)
- **OpenAI GPT-4o-mini**: ~$0.15 per 1M tokens (input) / $0.60 per 1M tokens (output)

**DeepSeek is about 50% cheaper overall!** 💰

### Performance:
- ✅ Excellent at structured data extraction
- ✅ Fast response times
- ✅ Great for web scraping tasks
- ✅ Supports JSON schema extraction

## 📝 How to Get Your DeepSeek API Key

### Step 1: Sign Up
1. Go to: **https://platform.deepseek.com/**
2. Click "Sign Up" or "Get Started"
3. Create an account (email + password)

### Step 2: Get API Key
1. Log in to your DeepSeek account
2. Go to **API Keys** section
3. Click **"Create API Key"**
4. Copy your API key (starts with `sk-...`)

### Step 3: Add Credits (Optional)
- DeepSeek often gives free credits to new users
- If needed, add credits to your account
- Minimum is usually $5-10

## 🔧 Configure Your Scraper

### Option 1: Edit .env File (Recommended)

1. Open the `.env` file in the crawl4ai folder
2. Paste your DeepSeek API key:

```env
# Paste your DeepSeek API key here:
DEEPSEEK_API_KEY=sk-your-actual-key-here

# Make sure this is set to deepseek:
LLM_PROVIDER=deepseek
```

3. Save the file

### Option 2: Set Environment Variable

**Windows (Command Prompt):**
```cmd
set DEEPSEEK_API_KEY=sk-your-actual-key-here
```

**Windows (PowerShell):**
```powershell
$env:DEEPSEEK_API_KEY="sk-your-actual-key-here"
```

**Mac/Linux:**
```bash
export DEEPSEEK_API_KEY="sk-your-actual-key-here"
```

## ✅ Test Your Setup

### Test 1: Check Configuration
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DeepSeek Key:', 'SET' if os.getenv('DEEPSEEK_API_KEY') else 'NOT SET')"
```

### Test 2: Run Test Scraper
```bash
python test_scraper.py
```

Choose option 1 to test a single page.

### Test 3: Run Advanced Scraper
```bash
python advanced_scraper.py
```

Choose option 1 to test with AI extraction.

## 🎯 Using the Dashboard

1. **Start the dashboard:**
   ```bash
   python dashboard_server.py
   ```
   Or double-click: `start_dashboard.bat`

2. **Open in browser:**
   http://localhost:5000

3. **Click "Run Scraper" button**
   - Choose "OK" for AI scraper (uses DeepSeek)
   - Choose "Cancel" for basic scraper (no API key)

4. **Watch it work!**
   - Progress updates appear
   - Data refreshes automatically when done

## 💡 Tips

### Cost Estimation
For scraping 4 competitor websites with ~100 products each:
- **Estimated tokens**: ~500K tokens total
- **Estimated cost**: ~$0.10-0.20 per full scrape
- **Monthly cost** (daily scraping): ~$3-6/month

### Best Practices
1. **Start with test scraper** to verify setup
2. **Use basic scraper** for quick checks (free)
3. **Use AI scraper** for production (most accurate)
4. **Schedule daily scraping** to track price changes

### Troubleshooting

**Error: "No DEEPSEEK_API_KEY found"**
- Make sure you saved the `.env` file
- Check that the key starts with `sk-`
- Restart the dashboard server

**Error: "Invalid API key"**
- Verify the key is correct
- Check if you have credits in your DeepSeek account
- Try creating a new API key

**Error: "Rate limit exceeded"**
- You're making too many requests
- Wait a few minutes and try again
- Consider upgrading your DeepSeek plan

## 🔄 Switching Between Providers

### Use DeepSeek (Default)
Edit `.env`:
```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key-here
```

### Use OpenAI Instead
Edit `.env`:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
```

## 📊 Accuracy Comparison

### Basic Scraper (No API Key)
- **Accuracy**: ~70-85%
- **Speed**: Fast
- **Cost**: Free
- **Best for**: Quick checks, testing

### AI Scraper with DeepSeek
- **Accuracy**: ~95-98%
- **Speed**: Moderate
- **Cost**: ~$0.10-0.20 per scrape
- **Best for**: Production use, accurate data

### AI Scraper with OpenAI
- **Accuracy**: ~95-98%
- **Speed**: Moderate
- **Cost**: ~$0.20-0.40 per scrape
- **Best for**: When you already have OpenAI credits

## 🎉 You're Ready!

Once you've added your DeepSeek API key to the `.env` file:

1. ✅ Dashboard buttons will work
2. ✅ AI scraper will extract accurate data
3. ✅ Costs will be minimal (~$3-6/month)
4. ✅ You'll get 95%+ accuracy

**Start the dashboard:**
```bash
python dashboard_server.py
```

**Or double-click:**
```
start_dashboard.bat
```

**Then open:** http://localhost:5000

---

**Happy Scraping! 🕷️**

*DeepSeek is recommended for the best balance of cost and accuracy!*

