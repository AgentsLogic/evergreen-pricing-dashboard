#!/usr/bin/env python3
"""
Extract cosmetic grades for PCLiquidations products
"""

import json
import sys
import os
from pathlib import Path
from competitor_price_scraper import CompetitorPriceScraper

def extract_pcl_grades():
    """Extract cosmetic grades for PCLiquidations products"""

    # Load current data
    with open('competitor_prices.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    pcl_data = data.get('PCLiquidations', {})
    products = pcl_data.get('products', [])

    print(f"🔍 Processing {len(products)} PCLiquidations products...")

    scraper = CompetitorPriceScraper()
    updated_count = 0

    for i, product in enumerate(products):
        # Skip products that already have grade information
        if product.get('config', {}).get('cosmetic_grade'):
            continue

        print(f"   [{i+1}/{len(products)}] Processing: {product['title'][:50]}...")

        try:
            # For PCLiquidations products, we need to scrape the individual product page
            # to extract the grade information
            if product.get('url'):
                # Use the existing scraper method to extract grade from the product page
                # For now, we'll use a simple pattern matching approach
                grade = extract_grade_from_title(product['title'])

                if grade:
                    product['config']['cosmetic_grade'] = grade
                    updated_count += 1
                    print(f"      ✅ Grade: {grade}")
                else:
                    print("      ⚠️  No grade found")
            else:
                print("      ⚠️  No URL available")
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")

    # Save updated data
    pcl_data['total_products'] = len(products)
    data['PCLiquidations'] = pcl_data

    with open('competitor_prices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Grade extraction complete!")
    print(f"📊 Updated {updated_count} products with grade information")

    return updated_count

def extract_grade_from_title(title):
    """Extract grade from product title using pattern matching"""
    title_lower = title.lower()

    # Common grade patterns in PCLiquidations titles
    if 'grade a' in title_lower:
        return 'Grade A'
    elif 'grade b' in title_lower:
        return 'Grade B'
    elif 'grade c' in title_lower:
        return 'Grade C'
    elif 'refurbished' in title_lower and 'excellent' in title_lower:
        return 'Grade A'
    elif 'refurbished' in title_lower and 'very good' in title_lower:
        return 'Grade B'
    elif 'refurbished' in title_lower and 'good' in title_lower:
        return 'Grade C'

    return None

if __name__ == "__main__":
    print("🚀 PCLiquidations Grade Extraction")
    print("="*50)

    try:
        updated = extract_pcl_grades()
        print(f"\n🎉 Successfully updated {updated} PCLiquidations products with grade information!")

    except Exception as e:
        print(f"❌ Error during grade extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
