@echo off
echo ================================================================================
echo   Starting Competitor Price Dashboard
echo ================================================================================
echo.
echo   Dashboard will open at: http://localhost:8080
echo.
echo   All buttons will work:
echo   - Refresh Data: Reloads the latest scraped data
echo   - Export CSV: Downloads data as CSV file
echo   - Run Scraper: Actually runs the scraper (choose basic or AI)
echo.
echo   Press Ctrl+C to stop the server
echo.
echo ================================================================================
echo.

python dashboard_server.py

