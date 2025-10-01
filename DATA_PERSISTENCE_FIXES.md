# Data Persistence and Product Matching Fixes

## Problem Summary

The competitor price scraper was experiencing inconsistent product counts, fluctuating between 400 and 200 products. This was caused by two main issues:

1. **Data Persistence Issues in scraper_v2.py**
   - Complete data overwrite with no backup during incremental saves
   - No validation before saving (could lose data if scrape failed mid-process)
   - No history of previous scrapes maintained

2. **Product Matching Issues in dashboard_server.py**
   - Dell Latitude 5320 special case was too broad (grouped ALL variants together)
   - Inconsistent handling of product configurations
   - Poor null/empty value handling in signatures

## Changes Made

### 1. scraper_v2.py - Data Persistence Safeguards

#### A. Backup System
- **Added timestamped backups** before overwriting data
  - Format: `competitor_prices_backup_YYYYMMDD_HHMMSS.json`
  - Creates backup only when existing data exists
  - Prevents data loss from failed scrapes

#### B. Validation Logic
- **30% threshold check** to prevent significant data loss
  - If new scrape has >30% fewer products, keeps existing data
  - Saves rejected data to `{competitor}_temp.json` for manual review
  - Logs detailed warnings about the data loss

#### C. Automatic Backup Cleanup
- **Keeps last 5 backups** automatically
  - Deletes older backups to prevent disk space issues
  - Uses file modification time for sorting

#### D. Change Tracking
- **Tracks product count changes** in saved data
  - Shows (+X) for increases, (-X) for decreases
  - Includes previous_count and change fields in JSON
  - Provides clear visibility into data changes

### 2. dashboard_server.py - Product Matching Improvements

#### A. Removed Dell Latitude 5320 Special Case
- **Before:** All 5320 variants grouped together regardless of specs
  ```python
  # Old problematic code:
  if brand == 'dell' and '5320' in model.lower():
      return f"dell_latitude_5320_touch_{product_type}"
  ```
- **After:** Uses standard matching logic with RAM/storage differentiation
  - Dell Latitude 5320 with 8GB/256GB now separate from 16GB/512GB
  - Each configuration tracked independently

#### B. Improved Signature Generation
- **Consistent approach** for all products
- **Better null handling** - filters out None/empty values before joining
- **Includes key specs** in signature:
  - Brand
  - Model
  - Product Type
  - Processor (if available)
  - RAM (if available)
  - Storage (if available)

## Benefits

### Data Safety
1. ✅ **No more data loss** from failed scrapes
2. ✅ **Automatic backups** for recovery
3. ✅ **Validation warnings** alert to problems
4. ✅ **Change tracking** for visibility

### Product Matching
1. ✅ **More accurate counts** - configurations properly differentiated
2. ✅ **Consistent matching** - no special cases causing issues
3. ✅ **Better multi-site comparison** - same products properly grouped

## How It Works

### Scraping Flow with New Safeguards

```
1. Start scraping competitor
   ↓
2. Scrape page 1
   ↓
3. Load existing data + count
   ↓
4. Validate new data (>30% loss check)
   ├─ PASS → Create backup → Save new data
   └─ FAIL → Keep old data → Save to temp file
   ↓
5. Continue to page 2...
```

### Validation Example

```
Previous scrape: 100 products
Current scrape: 65 products (35% reduction)

❌ REJECTED - Too much loss!
✅ Existing data preserved
📁 New data saved to competitor_temp.json
```

## Testing Recommendations

1. **Test with single competitor:**
   ```bash
   python scraper_v2.py --competitor SystemLiquidation
   ```

2. **Monitor output for:**
   - ✅ `[BACKUP] Created backup:` messages
   - ✅ `[SAVE] Incremental save: X products (+/-Y)` messages
   - ⚠️  `[WARNING] Significant data loss detected!` alerts

3. **Check generated files:**
   - `competitor_prices.json` - main data file
   - `competitor_prices_backup_*.json` - timestamped backups (max 5)
   - `{competitor}_temp.json` - rejected data for review

## Recovery Procedures

### If Data is Lost
1. Check for backup files: `competitor_prices_backup_*.json`
2. Restore latest backup:
   ```bash
   copy competitor_prices_backup_20250101_123456.json competitor_prices.json
   ```

### If Bad Data is Saved
1. Check temp files: `{competitor}_temp.json`
2. Compare with backups to determine correct state
3. Manually merge or restore as needed

## Files Modified

1. **scraper_v2.py**
   - Modified `_save_incremental_results()` method
   - Added `_cleanup_old_backups()` helper method
   - Enhanced error handling and logging

2. **dashboard_server.py**
   - Modified `create_product_signature()` function
   - Removed Dell Latitude 5320 special case
   - Improved null value handling

3. **New File Created**
   - `competitor_prices_backup_manual.json` - manual backup before changes

## Monitoring

### Key Metrics to Watch

1. **Product Count Stability**
   - Should remain relatively stable between scrapes
   - Small fluctuations (±5%) are normal (actual inventory changes)
   - Large drops (>30%) will be blocked

2. **Backup File Count**
   - Should see 1-5 backup files at any time
   - Files automatically cleaned up after 5th backup

3. **Change Tracking**
   - Check `change` field in JSON data
   - Monitor for unexpected large changes

## Future Enhancements

Potential improvements for consideration:

1. **Web UI for Backup Management**
   - View backup history
   - One-click restore
   - Compare backup versions

2. **Email Alerts**
   - Notify on validation failures
   - Alert on significant data changes

3. **Merge Logic**
   - Smart merge instead of overwrite
   - Keep products not seen in new scrape

4. **Historical Tracking**
   - Store complete scrape history
   - Track product price changes over time

## Summary

These changes provide robust data protection and more accurate product matching:

- ✅ **Prevents data loss** through backups and validation
- ✅ **Improves product counts** through better matching logic  
- ✅ **Provides visibility** with change tracking and logging
- ✅ **Enables recovery** with automatic backups

The system is now much more resilient to scraping errors and provides better data quality for the dashboard.
