#!/usr/bin/env python3
"""
Download English troparia/kontakia from OCA website for all 365 days of 2026.
Source: oca.org/saints/troparia/YYYY/MM/DD
"""

import asyncio
import aiohttp
import os
import json
import re
from html.parser import HTMLParser

BASE_URL = "https://www.oca.org/saints/troparia/2026"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oca_troparia")

DAYS_IN_MONTH = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

CONCURRENT = 8

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
    def handle_data(self, data):
        self.result.append(data)
    def get_text(self):
        return ''.join(self.result).strip()

def strip_html(html):
    s = HTMLStripper()
    s.feed(html)
    return s.get_text()

def parse_troparia_page(html):
    """Parse OCA troparia page into structured data."""
    saints = []
    
    # The page has sections per saint, each with h2 (saint name), 
    # h3 (Troparion/Kontakion + tone), and text
    
    # Split by h2 to get individual saint sections
    saint_sections = re.split(r'<h2[^>]*>', html)
    
    for section in saint_sections[1:]:  # Skip content before first h2
        # Get saint name
        name_match = re.match(r'(.*?)</h2>', section, re.DOTALL)
        if not name_match:
            continue
        saint_name = strip_html(name_match.group(1)).strip()
        if not saint_name:
            continue
        
        saint_entry = {
            "name": saint_name,
            "troparion": None,
            "kontakion": None
        }
        
        # Find all h3 sections (Troparion/Kontakion headings)
        h3_parts = re.split(r'<h3[^>]*>', section)
        
        for part in h3_parts[1:]:
            heading_match = re.match(r'(.*?)</h3>', part, re.DOTALL)
            if not heading_match:
                continue
            heading = strip_html(heading_match.group(1)).strip()
            
            # Get the text after the heading (before next h2 or h3)
            text_after = part[heading_match.end():]
            # Get paragraphs
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', text_after, re.DOTALL)
            text = ' '.join(strip_html(p).strip() for p in paragraphs if strip_html(p).strip())
            
            if not text:
                continue
            
            # Parse tone
            tone_match = re.search(r'Tone\s+(\d+)', heading)
            tone = int(tone_match.group(1)) if tone_match else None
            
            if 'troparion' in heading.lower():
                saint_entry["troparion"] = {
                    "tone": tone,
                    "text": text
                }
            elif 'kontakion' in heading.lower():
                saint_entry["kontakion"] = {
                    "tone": tone,
                    "text": text
                }
        
        # Only add if we got at least a troparion
        if saint_entry["troparion"] or saint_entry["kontakion"]:
            saints.append(saint_entry)
    
    return saints

async def download_day(session, sem, month, day):
    """Download and parse troparia for a single day."""
    mm = f"{month:02d}"
    dd = f"{day:02d}"
    url = f"{BASE_URL}/{mm}/{dd}"
    
    output_path = os.path.join(OUTPUT_DIR, mm, f"{dd}.json")
    
    # Skip if already downloaded
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10:
        return "skip"
    
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return "fail"
                html = await resp.text()
                
                saints = parse_troparia_page(html)
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "date": f"2026-{mm}-{dd}",
                        "source": "oca.org",
                        "saints": saints
                    }, f, ensure_ascii=False, indent=2)
                
                return "ok"
        except Exception as e:
            return "fail"

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    sem = asyncio.Semaphore(CONCURRENT)
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ByzantineDoors/1.0)'}
    
    tasks = []
    connector = aiohttp.TCPConnector(limit=CONCURRENT, ttl_dns_cache=300)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        for month in range(1, 13):
            for day in range(1, DAYS_IN_MONTH[month] + 1):
                tasks.append(download_day(session, sem, month, day))
        
        print(f"Downloading troparia for {len(tasks)} days...")
        results = await asyncio.gather(*tasks)
    
    ok = results.count("ok")
    skip = results.count("skip")
    fail = results.count("fail")
    
    print(f"\nDONE")
    print(f"  Downloaded: {ok}")
    print(f"  Already had: {skip}")
    print(f"  Failed: {fail}")
    print(f"  Total: {len(results)}")

if __name__ == "__main__":
    asyncio.run(main())
