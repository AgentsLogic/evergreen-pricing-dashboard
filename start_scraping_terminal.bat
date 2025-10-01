@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

echo ================================================
echo 🚀 Competitor Price Scraper - Live Terminal View
echo ================================================
echo.
echo This terminal will show real-time scraping progress
echo You can watch the scraping process here while using the web dashboard
echo.
echo Available scrapers:
echo   1. PCLiquidations (Fast, ~100 products)
echo   2. SystemLiquidation (Slow but good data)
echo   3. DiscountElectronics (Medium speed)
echo   4. DiscountPC (Medium speed)
echo   5. All Competitors (Very slow - 30+ minutes)
echo.
echo Dashboard: http://localhost:8080
echo ================================================
echo.

:menu
echo Choose which scraper to run:
echo 1) PCLiquidations (Recommended)
echo 2) SystemLiquidation
echo 3) DiscountElectronics
echo 4) DiscountPC
echo 5) All Competitors
echo.

set /p choice="Enter choice (1-5): "

if "%choice%"=="1" goto pcliquidations
if "%choice%"=="2" goto systemliquidation
if "%choice%"=="3" goto discountelectronics
if "%choice%"=="4" goto discountpc
if "%choice%"=="5" goto all
goto invalid

:pcliquidations
echo.
echo ================================================
echo 🚀 Starting PCLiquidations Scraper
echo ================================================
python -u scraper_v2.py --competitor PCLiquidations
set "EXITCODE=%ERRORLEVEL%"
goto end

:systemliquidation
echo.
echo ================================================
echo 🚀 Starting SystemLiquidation Scraper
echo ================================================
python -u scraper_v2.py --competitor SystemLiquidation
set "EXITCODE=%ERRORLEVEL%"
goto end

:discountelectronics
echo.
echo ================================================
echo 🚀 Starting DiscountElectronics Scraper
echo ================================================
python -u scraper_v2.py --competitor DiscountElectronics
set "EXITCODE=%ERRORLEVEL%"
goto end

:discountpc
echo.
echo ================================================
echo 🚀 Starting DiscountPC Scraper
echo ================================================
python -u scraper_v2.py --competitor DiscountPC
set "EXITCODE=%ERRORLEVEL%"
goto end

:all
echo.
echo ================================================
echo 🚀 Starting ALL Competitors Scraper (30+ min)
echo ================================================
echo WARNING: This will take 30+ minutes to complete!
echo Press Ctrl+C to cancel within the next 10 seconds...
timeout /t 10
python -u scraper_v2.py
set "EXITCODE=%ERRORLEVEL%"
goto end

:invalid
echo Invalid choice. Please run again and select 1-5.
pause
goto menu

:end
echo.
echo ================================================
if defined EXITCODE if not "%EXITCODE%"=="0" (
  echo ❌ Scraper exited with error code %EXITCODE%.
  echo See logs above for details.
) else (
  echo ✅ Scraping Complete!
)
echo ================================================
echo Check the dashboard at: http://localhost:8080
echo Your scraped data is saved to competitor_prices.json
echo.
pause
endlocal
