#!/usr/bin/env python3
"""
Download all liturgical data from prayer-service.pp.ua for 2026.
File types: t (text), s (saints), u (ustav/rubrics)
Suffixes: v (vespers), u (matins), c (compline), n (midnight?)
"""

import os
import time
import urllib.request
import urllib.error
from datetime import date, timedelta

BASE_URL = "https://prayer-service.pp.ua/assets/2026n"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "raw")

# File prefixes and suffixes to download
# t = service texts, s = saints/synaxarion, u = ustav/rubrics, b = ?
PREFIXES = ["t", "s", "u"]
# For 't' prefix: v=vespers, u=matins, c=compline
T_SUFFIXES = ["v", "u", "c"]

# Days in each month for 2026
DAYS_IN_MONTH = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

def download_file(url, filepath):
    """Download a URL to a file. Returns True if successful."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ByzantineDoors/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) < 50:  # Skip near-empty files
                return False
            with open(filepath, 'wb') as f:
                f.write(data)
            return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total = 0
    downloaded = 0
    skipped = 0
    failed = 0
    
    for month in range(1, 13):
        month_str = f"{month:02d}"
        month_dir = os.path.join(OUTPUT_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        days = DAYS_IN_MONTH[month]
        print(f"\n{'='*50}")
        print(f"Month {month_str} ({days} days)")
        print(f"{'='*50}")
        
        for day in range(1, days + 1):
            day_str = f"{day:02d}"
            files_for_day = []
            
            # Saints/synaxarion file: sDD.html
            files_for_day.append(("s", f"s{day_str}.html", f"s{day_str}.html"))
            
            # Ustav file: uDD.html  
            files_for_day.append(("u", f"u{day_str}.html", f"u{day_str}.html"))
            
            # Text files: tDDv.html, tDDu.html, tDDc.html
            for suffix in T_SUFFIXES:
                fname = f"t{day_str}{suffix}.html"
                files_for_day.append(("t", fname, fname))
            
            for prefix, remote_name, local_name in files_for_day:
                total += 1
                filepath = os.path.join(month_dir, local_name)
                
                # Skip if already downloaded
                if os.path.exists(filepath) and os.path.getsize(filepath) > 50:
                    skipped += 1
                    continue
                
                url = f"{BASE_URL}/{month_str}/{remote_name}"
                ok = download_file(url, filepath)
                
                if ok:
                    downloaded += 1
                    print(f"  ✓ {month_str}/{local_name}")
                else:
                    failed += 1
                    # Remove empty/failed files
                    if os.path.exists(filepath):
                        os.remove(filepath)
                
                # Small delay between requests
                time.sleep(0.05)
        
        print(f"  Month {month_str} complete")
    
    print(f"\n{'='*50}")
    print(f"DONE")
    print(f"  Total files attempted: {total}")
    print(f"  Downloaded: {downloaded}")
    print(f"  Already had: {skipped}")
    print(f"  Failed/empty: {failed}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
