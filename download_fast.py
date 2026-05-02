#!/usr/bin/env python3
"""
Fast concurrent download of all liturgical data from prayer-service.pp.ua for 2026.
Uses asyncio + aiohttp for parallel downloads.
"""

import asyncio
import aiohttp
import os
import sys

BASE_URL = "https://prayer-service.pp.ua/assets/2026n"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

DAYS_IN_MONTH = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

# Concurrency limit — be reasonable but faster than serial
CONCURRENT = 10

async def download_one(session, sem, url, filepath):
    """Download a single file with semaphore-limited concurrency."""
    if os.path.exists(filepath) and os.path.getsize(filepath) > 50:
        return "skip"
    
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return "fail"
                data = await resp.read()
                if len(data) < 50:
                    return "empty"
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(data)
                return "ok"
        except Exception:
            return "fail"

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Build task list
    tasks_info = []
    for month in range(1, 13):
        mm = f"{month:02d}"
        days = DAYS_IN_MONTH[month]
        for day in range(1, days + 1):
            dd = f"{day:02d}"
            # Saint/synaxarion
            tasks_info.append((f"{BASE_URL}/{mm}/s{dd}.html", f"{OUTPUT_DIR}/{mm}/s{dd}.html"))
            # Ustav
            tasks_info.append((f"{BASE_URL}/{mm}/u{dd}.html", f"{OUTPUT_DIR}/{mm}/u{dd}.html"))
            # Vespers
            tasks_info.append((f"{BASE_URL}/{mm}/t{dd}v.html", f"{OUTPUT_DIR}/{mm}/t{dd}v.html"))
            # Matins
            tasks_info.append((f"{BASE_URL}/{mm}/t{dd}u.html", f"{OUTPUT_DIR}/{mm}/t{dd}u.html"))
            # Compline
            tasks_info.append((f"{BASE_URL}/{mm}/t{dd}c.html", f"{OUTPUT_DIR}/{mm}/t{dd}c.html"))
    
    print(f"Total files to check: {len(tasks_info)}")
    
    sem = asyncio.Semaphore(CONCURRENT)
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ByzantineDoors/1.0)'}
    
    connector = aiohttp.TCPConnector(limit=CONCURRENT, ttl_dns_cache=300)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        coros = [download_one(session, sem, url, fp) for url, fp in tasks_info]
        results = await asyncio.gather(*coros)
    
    ok = results.count("ok")
    skip = results.count("skip")
    fail = results.count("fail")
    empty = results.count("empty")
    
    print(f"\nDONE")
    print(f"  Downloaded: {ok}")
    print(f"  Already had: {skip}")
    print(f"  Failed (404/error): {fail}")
    print(f"  Empty (<50 bytes): {empty}")
    print(f"  Total: {len(results)}")
    
    # Summary per month
    idx = 0
    for month in range(1, 13):
        days = DAYS_IN_MONTH[month]
        n = days * 5
        month_results = results[idx:idx+n]
        month_ok = month_results.count("ok") + month_results.count("skip")
        print(f"  Month {month:02d}: {month_ok} files")
        idx += n

if __name__ == "__main__":
    asyncio.run(main())
