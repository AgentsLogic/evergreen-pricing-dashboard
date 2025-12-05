#!/usr/bin/env python3
"""Generate weekly MSRP CSV report from competitor_prices.json with price deltas.

Usage:
    python generate_msrp_report.py [--date YYYY-MM-DD] [--history-dir msrp_history]

This script:
  * Flattens competitor_prices.json into one row per product/config
  * Looks at the most recent prior report in history dir
  * Computes price_previous, price_change, price_change_pct, change_flag (UP/DOWN/SAME/NEW)
  * Writes msrp_history/msrp_report_YYYY-MM-DD.csv (or given date)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional


CURRENT_JSON = Path("competitor_prices.json")
DEFAULT_HISTORY_DIR = Path("msrp_history")


@dataclass
class ProductRow:
    competitor: str
    brand: Optional[str]
    product_type: Optional[str]
    model: Optional[str]
    title: Optional[str]
    url: Optional[str]
    processor: Optional[str]
    ram: Optional[str]
    storage: Optional[str]
    cosmetic_grade: Optional[str]
    form_factor: Optional[str]
    screen_resolution: Optional[str]
    price_current: Optional[float]
    cpu_generation: Optional[int] = None

    def key(self) -> str:
        """Stable key for matching between weeks.

        Prefer competitor+URL; fall back to competitor+brand+model.
        """
        base = self.url or ""
        if not base:
            base = f"{self.brand or ''}|{self.model or ''}"
        return f"{self.competitor}|{base}".lower()


def extract_intel_generation(text: Optional[str]) -> Optional[int]:
    """Best-effort Intel CPU generation parser (mirrors dashboard logic)."""
    if not text:
        return None
    t = text.lower()

    # Must look like an Intel family CPU; otherwise treat as non-Intel
    if "intel" not in t and "core i" not in t:
        return None

    # Pattern like "11th Gen" / "8th gen"
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s*gen", t)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass

    # Pattern like "i5-8350U" or "i7 9700" (with optional space or hyphen)
    m = re.search(r"\bi[3579][\s-]?(\d{4,5})", t)
    if m:
        digits = m.group(1)
        try:
            if len(digits) >= 5 and digits[:2].isdigit():
                gen = int(digits[:2])  # 10xxx, 11xxx, etc.
            else:
                gen = int(digits[0])   # 8xxx, 9xxx
            if 1 <= gen <= 20:
                return gen
        except ValueError:
            pass

    # Fallback: "i5 8th gen" style
    m = re.search(r"\bi[3579]\s*(\d{1,2})\w*\s*gen", t)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass

    return None


def load_current_products(json_path: Path = CURRENT_JSON) -> List[ProductRow]:
    if not json_path.exists():
        raise FileNotFoundError(f"Current data file not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    rows: List[ProductRow] = []

    for competitor_name, comp_data in (data or {}).items():
        products = comp_data.get("products", []) or []
        for p in products:
            cfg = p.get("config") or {}
            cpu_text = cfg.get("processor") or f"{p.get('title','')} {p.get('model','')}"
            gen = extract_intel_generation(cpu_text)
            rows.append(
                ProductRow(
                    competitor=competitor_name,
                    brand=p.get("brand"),
                    product_type=p.get("product_type"),
                    model=p.get("model"),
                    title=p.get("title"),
                    url=p.get("url"),
                    processor=cfg.get("processor"),
                    ram=cfg.get("ram"),
                    storage=cfg.get("storage"),
                    cosmetic_grade=cfg.get("cosmetic_grade"),
                    form_factor=cfg.get("form_factor"),
                    screen_resolution=cfg.get("screen_resolution"),
                    price_current=p.get("price"),
                    cpu_generation=gen,
                )
            )

    return rows


def find_latest_report(history_dir: Path) -> Optional[Path]:
    if not history_dir.exists():
        return None
    candidates = sorted(history_dir.glob("msrp_report_*.csv"))
    return candidates[-1] if candidates else None


def load_previous_prices(report_path: Path) -> Dict[str, float]:
    """Return mapping key -> previous price_current from last report."""
    prices: Dict[str, float] = {}
    if not report_path or not report_path.exists():
        return prices

    with report_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("key") or ""
            if not key:
                # Rebuild key if older reports didn't store it explicitly
                key = make_key_from_row(row)
            raw_price = row.get("price_current") or row.get("price")
            try:
                if raw_price not in (None, ""):
                    prices[key] = float(raw_price)
            except ValueError:
                continue
    return prices


def make_key_from_row(row: Dict[str, str]) -> str:
    base = row.get("url") or ""
    if not base:
        base = f"{row.get('brand','')}|{row.get('model','')}"
    return f"{row.get('competitor','')}|{base}".lower()


def write_report(
    rows: List[ProductRow],
    previous_prices: Dict[str, float],
    history_dir: Path,
    report_date: date,
) -> Path:
    history_dir.mkdir(parents=True, exist_ok=True)
    out_path = history_dir / f"msrp_report_{report_date.isoformat()}.csv"

    fieldnames = [
        "week_date",
        "competitor",
        "brand",
        "product_type",
        "model",
        "title",
        "url",
        "processor",
        "pg",
        "ram",
        "storage",
        "cosmetic_grade",
        "form_factor",
        "screen_resolution",
        "price_previous",
        "price_current",
        "price_change",
        "price_change_pct",
        "change_flag",
        "key",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in rows:
            key = r.key()
            prev_price = previous_prices.get(key)
            cur_price = r.price_current if r.price_current is not None else None

            price_previous_str = str(int(round(prev_price))) if prev_price is not None else ""
            price_current_str = str(int(round(cur_price))) if cur_price is not None else ""

            change = None
            change_pct = None
            flag = "NEW"

            if prev_price is not None and cur_price is not None:
                change = cur_price - prev_price
                change_pct = (change / prev_price) * 100 if prev_price > 0 else None
                if change > 0:
                    flag = "UP"
                elif change < 0:
                    flag = "DOWN"
                else:
                    flag = "SAME"

            row_out = {
                "week_date": report_date.isoformat(),
                "competitor": r.competitor,
                "brand": r.brand or "",
                "product_type": r.product_type or "",
                "model": r.model or "",
                "title": r.title or "",
                "url": r.url or "",
                "processor": r.processor or "",
                "pg": str(r.cpu_generation) if r.cpu_generation is not None else "",
                "ram": r.ram or "",
                "storage": r.storage or "",
                "cosmetic_grade": r.cosmetic_grade or "",
                "form_factor": r.form_factor or "",
                "screen_resolution": r.screen_resolution or "",
                "price_previous": price_previous_str,
                "price_current": price_current_str,
                "price_change": str(int(round(change))) if change is not None else "",
                "price_change_pct": f"{change_pct:.2f}" if change_pct is not None else "",
                "change_flag": flag,
                "key": key,
            }
            writer.writerow(row_out)

    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate weekly MSRP CSV report")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--history-dir",
        default=str(DEFAULT_HISTORY_DIR),
        help="Directory to store reports (default: msrp_history)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.date:
        report_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        report_date = date.today()

    history_dir = Path(args.history_dir)

    current_rows = load_current_products()
    latest_report = find_latest_report(history_dir)
    previous_prices = load_previous_prices(latest_report) if latest_report else {}

    out_path = write_report(current_rows, previous_prices, history_dir, report_date)
    print(f"MSRP report written to: {out_path}")
    if latest_report:
        print(f"Compared against previous report: {latest_report}")
    else:
        print("No previous report found; all rows marked as NEW.")


if __name__ == "__main__":
    main()

