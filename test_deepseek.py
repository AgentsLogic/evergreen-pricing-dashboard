"""
Quick test to verify DeepSeek API is working
"""

import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables
from dotenv import load_dotenv
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

print("\n" + "="*80)
print("🧪 Testing DeepSeek API Configuration")
print("="*80 + "\n")

# Check if API key is set
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    print("❌ DEEPSEEK_API_KEY not found!")
    print("\nPlease add your DeepSeek API key to the .env file:")
    print("   DEEPSEEK_API_KEY=sk-your-key-here")
    print("\nGet your key from: https://platform.deepseek.com/")
    sys.exit(1)

print(f"✅ DeepSeek API key found: {api_key[:10]}...{api_key[-4:]}")

# Test the API with a simple request
print("\n🔄 Testing API connection...")

try:
    from litellm import completion
    
    response = completion(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "user", "content": "Say 'Hello! DeepSeek is working!' and nothing else."}
        ],
        api_key=api_key
    )
    
    result = response.choices[0].message.content
    
    print(f"\n✅ API Test Successful!")
    print(f"Response: {result}")
    
    print("\n" + "="*80)
    print("🎉 DeepSeek is configured correctly!")
    print("="*80)
    print("\nYou can now:")
    print("  1. Run the advanced scraper: python advanced_scraper.py")
    print("  2. Use the dashboard 'Run Scraper' button (choose AI)")
    print("  3. Get 95%+ accuracy on product extraction")
    print("\n" + "="*80 + "\n")

except Exception as e:
    print(f"\n❌ API Test Failed!")
    print(f"Error: {str(e)}")
    print("\nPossible issues:")
    print("  1. Invalid API key")
    print("  2. No credits in DeepSeek account")
    print("  3. Network connection issue")
    print("\nPlease check:")
    print("  - Your API key is correct")
    print("  - You have credits in your DeepSeek account")
    print("  - Your internet connection is working")
    sys.exit(1)

