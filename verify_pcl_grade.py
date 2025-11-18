from competitor_price_scraper import CompetitorPriceScraper

if __name__ == "__main__":
    with open('pcliquidationssource.txt', 'r', encoding='utf-8') as f:
        html = f.read()
    scraper = CompetitorPriceScraper()
    grade = scraper.extract_cosmetic_grade(html)
    url = scraper.extract_product_url_from_section(html, 'PCLiquidations')
    print("Grade extracted:", grade)
    print("Product URL extracted:", url)

