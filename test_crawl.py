import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    print("🚀 Starting Crawl4AI test...")
    
    async with AsyncWebCrawler() as crawler:
        print("📡 Crawling https://www.nbcnews.com/business...")
        result = await crawler.arun(
            url="https://www.nbcnews.com/business",
        )
        
        print("\n✅ Crawl completed successfully!")
        print(f"📄 Title: {result.metadata.get('title', 'N/A')}")
        print(f"📊 Content length: {len(result.markdown)} characters")
        print("\n📝 First 500 characters of markdown:")
        print("=" * 80)
        print(result.markdown[:500])
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

