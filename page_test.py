import json

# Check current competitor prices data
try:
    with open('competitor_prices.json', 'r') as f:
        data = json.load(f)

    print('🧪 Current Data Status:')
    print('=' * 50)

    for site, info in data.items():
        products = info.get('products', [])
        if products:
            dell_count = sum(1 for p in products if p.get('brand') == 'Dell')
            hp_count = sum(1 for p in products if p.get('brand') == 'HP')
            lenovo_count = sum(1 for p in products if p.get('brand') == 'Lenovo')
            total_filtered = dell_count + hp_count + lenovo_count
            print(f'{site}: {total_filtered} Dell/HP/Lenovo products ({dell_count} Dell, {hp_count} HP, {lenovo_count} Lenovo)')
        else:
            print(f'{site}: No data yet')

    # Show sample products
    if 'PCLiquidations' in data and data['PCLiquidations'].get('products'):
        print('\n📋 Sample PCLiquidations Products:')
        print('-' * 50)
        sample_products = data['PCLiquidations']['products'][:3]
        for i, p in enumerate(sample_products, 1):
            print(f"{i}. {p.get('brand', 'Unknown')} {p.get('model', 'N/A')} - ${p.get('price', 'N/A')}")
            config = p.get('config', {})
            specs = []
            if config.get('processor'): specs.append(f"CPU: {config['processor']}")
            if config.get('ram'): specs.append(f"RAM: {config['ram']}")
            if config.get('storage'): specs.append(f"SSD: {config['storage']}")
            if config.get('cosmetic_grade'): specs.append(f"Grade: {config['cosmetic_grade']}")
            if specs: print(f"   Specs: {' | '.join(specs)}")
            print()

except FileNotFoundError:
    print("❌ competitor_prices.json not found")
