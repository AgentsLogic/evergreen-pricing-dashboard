#!/usr/bin/env python3
"""
Script to update frontend configuration for Render backend integration.
Run this after deploying the Flask backend to Render.
"""

import re
import sys

def update_frontend_config(render_backend_url):
    """Update the frontend HTML files to point to the Render backend."""

    # Update price_dashboard.html
    with open('price_dashboard.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Update API endpoints to point to Render backend
    content = re.sub(
        r'fetch\(\'/api/',
        f'fetch(\'{render_backend_url}/api/',
        content
    )

    # Update EventSource connections
    content = re.sub(
        r'new EventSource\(\'/api/',
        f'new EventSource(\'{render_backend_url}/api/',
        content
    )

    with open('price_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Updated price_dashboard.html to use backend: {render_backend_url}")

    # Update other dashboard files if they have API calls
    for filename in ['graphs_dashboard.html', 'popularity_dashboard.html', 'multi_site_comparison.html']:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update API endpoints
            content = re.sub(
                r'fetch\(\'/api/',
                f'fetch(\'{render_backend_url}/api/',
                content
            )

            content = re.sub(
                r'new EventSource\(\'/api/',
                f'new EventSource(\'{render_backend_url}/api/',
                content
            )

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ Updated {filename}")
        except FileNotFoundError:
            pass  # File doesn't exist or doesn't have API calls

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_frontend_config.py <render_backend_url>")
        print("Example: python update_frontend_config.py https://your-app.onrender.com")
        sys.exit(1)

    render_url = sys.argv[1]
    update_frontend_config(render_url)
