import json
import os

def filter_pcl_products_without_grades():
    """Remove PCLiquidations products that don't have cosmetic grades"""

    # Load current data
    with open('competitor_prices.json', 'r') as f:
        data = json.load(f)

    if 'PCLiquidations' not in data:
        print("No PCLiquidations data found")
        return

    pcl_data = data['PCLiquidations']
    original_count = pcl_data['total_products']
    products = pcl_data['products']

    # Filter products that have cosmetic grades
    filtered_products = []
    removed_count = 0

    for product in products:
        if (product.get('config', {}).get('cosmetic_grade') and
            product['config']['cosmetic_grade'] != 'null' and
            product['config']['cosmetic_grade'] is not None):
            filtered_products.append(product)
        else:
            removed_count += 1

    # Update the data
    pcl_data['products'] = filtered_products
    pcl_data['total_products'] = len(filtered_products)

    # Save filtered data
    with open('competitor_prices.json', 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Original PCLiquidations products: {original_count}")
    print(f"Products with grades: {len(filtered_products)}")
    print(f"Products removed: {removed_count}")

    return len(filtered_products)

if __name__ == "__main__":
    filter_pcl_products_without_grades()
