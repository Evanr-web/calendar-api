#!/usr/bin/env python3
"""
Parse downloaded liturgical data and build the static Calendar API.

Outputs:
  api/
    2026/
      calendar.json          — Full year summary (365 entries)
      01/
        calendar.json        — Month summary
        01.json              — Full day data (metadata + services)
        02.json
        ...
      ...
"""

import json
import os
import re
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
API_DIR = os.path.join(BASE_DIR, "api", "2026")
CALENDAR_FILE = os.path.join(BASE_DIR, "..", "PWA Site", "prayer-app", "data", "calendar2026.json")

DAYS_IN_MONTH = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

MONTH_NAMES_EN = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
MONTH_NAMES_UK = ['', 'Січень', 'Лютий', 'Березень', 'Квітень', 'Травень', 'Червень',
                  'Липень', 'Серпень', 'Вересень', 'Жовтень', 'Листопад', 'Грудень']

# ── HTML to plain text helper ─────────────────────────────────
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

def read_file(path):
    """Read a file, return content or None if missing."""
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

# ── Parse ustav file ──────────────────────────────────────────
def parse_ustav(html):
    """Extract saint names and rubrics from ustav file."""
    if not html:
        return {"saints": [], "rubrics": ""}
    
    # Split on <hr> — content before is saint names, after is rubrics
    parts = re.split(r'<hr\s*/?>', html, maxsplit=1)
    
    saints_html = parts[0] if len(parts) > 0 else ""
    rubrics_html = parts[1] if len(parts) > 1 else ""
    
    # Extract saint names (each <p> before <hr> is a saint)
    saint_matches = re.findall(r'<p>(.*?)(?:</p>|$)', saints_html, re.DOTALL)
    saints = [strip_html(s).strip() for s in saint_matches if strip_html(s).strip()]
    
    # Clean rubrics
    rubrics = strip_html(rubrics_html).strip()
    
    return {"saints": saints, "rubrics": rubrics}

# ── Parse saints/synaxarion file ──────────────────────────────
def parse_saints(html):
    """Extract troparion, kontakion, and synaxarion text."""
    if not html:
        return {"troparion": "", "kontakion": "", "synaxarion": ""}
    
    troparion = ""
    kontakion = ""
    
    # Find troparion — look for "Тропар" in italic tags
    trop_match = re.search(r'<(?:i|em)>\s*Тропар\s*\([^)]*\)\s*:?\s*</(?:i|em)>\s*(.*?)(?=<(?:i|em)>\s*Кондак|<p><b>|$)', html, re.DOTALL | re.IGNORECASE)
    if trop_match:
        troparion = strip_html(trop_match.group(1)).strip()
    
    # Find kontakion
    kond_match = re.search(r'<(?:i|em)>\s*Кондак\s*\([^)]*\)\s*:?\s*</(?:i|em)>\s*(.*?)(?=<p>[^<]*(?:Про |У |Був |Народ|Святий|Блажен|Преподоб)|<p>__|$)', html, re.DOTALL | re.IGNORECASE)
    if kond_match:
        kontakion = strip_html(kond_match.group(1)).strip()
    
    # Synaxarion — the saint's life text
    # Strategy: find all <p> tags, skip icon divs, title, troparion, kontakion,
    # and source attribution. Everything else is synaxarion body.
    synaxarion_parts = []
    
    # Remove icon div blocks first
    clean_html = re.sub(r'<!--\s*ICON\s*-->.*?</div>\s*</div>', '', html, flags=re.DOTALL)
    clean_html = re.sub(r'<div class="icovita">.*?</div>\s*</div>', '', clean_html, flags=re.DOTALL)
    
    paragraphs = re.findall(r'<p>(.*?)(?:</p>|<p>|$)', clean_html, re.DOTALL)
    
    found_kontakion = False
    for p in paragraphs:
        text = strip_html(p).strip()
        if not text:
            continue
        # Skip title lines (bold saint name)
        if re.match(r'^(Житіє|Пам.ять|Празник|Свято|Собор|Різдво|Успіння|Благовіщ)', text):
            continue
        # Skip troparion/kontakion lines  
        if re.match(r'^Тропар\s*\(', text):
            continue
        if re.match(r'^Кондак\s*\(', text):
            found_kontakion = True
            continue
        # Stop at source attribution
        if text.startswith('__') or 'Луцик' in text or 'Видавництво' in text:
            break
        if text.startswith('У той самий день'):
            break
        # After kontakion, everything is synaxarion body
        # Also catch long paragraphs even if kontakion wasn't found
        if found_kontakion or len(text) > 150:
            found_kontakion = True  # Once we start, keep going
            synaxarion_parts.append(text)
    
    synaxarion = '\n\n'.join(synaxarion_parts)
    
    return {
        "troparion": troparion,
        "kontakion": kontakion,
        "synaxarion": synaxarion
    }

# ── Parse service file (vespers, matins, compline/hours) ──────
def parse_service(html, service_type="vespers"):
    """Parse a service HTML file into structured sections."""
    if not html:
        return None
    
    # For the API, store the raw HTML (it's already well-structured)
    # and also extract a plain-text version
    return {
        "html": html.strip(),
        "text": strip_html(html).strip()[:500] + "..."  # Preview only
    }

# ── Fast code to human-readable ──────────────────────────────
def decode_fast(fast):
    """Convert fast code to structured info."""
    if not fast:
        return {"level": "unknown", "label_en": "", "label_uk": ""}
    
    fast_map = {
        "***": {"level": "feast", "label_en": "Feast day", "label_uk": "Свято"},
        "30d": {"level": "none", "label_en": "No fast", "label_uk": "Без посту"},
        "31d": {"level": "light", "label_en": "Meat permitted", "label_uk": "М'ясо дозволено"},
        "32d": {"level": "fish", "label_en": "Fish permitted", "label_uk": "Риба дозволена"},
        "33d": {"level": "fish", "label_en": "Fish permitted", "label_uk": "Риба дозволена"},
        "34d": {"level": "fish", "label_en": "Fish permitted", "label_uk": "Риба дозволена"},
        "35d": {"level": "fish", "label_en": "Fish permitted", "label_uk": "Риба дозволена"},
        "36d": {"level": "wine_oil", "label_en": "Wine & oil permitted", "label_uk": "Вино та олія дозволені"},
        "37d": {"level": "wine", "label_en": "Wine permitted", "label_uk": "Вино дозволено"},
        "38d": {"level": "strict", "label_en": "Strict fast", "label_uk": "Суворий піст"},
        "00m": {"level": "free", "label_en": "Fast-free week", "label_uk": "Тиждень без посту"},
        "00s": {"level": "dairy", "label_en": "Dairy permitted (Cheesefare)", "label_uk": "Молочна їжа дозволена"},
    }
    
    if fast in fast_map:
        return fast_map[fast]
    
    # Lenten weeks
    lent_match = re.match(r'^0(\d)p$', fast)
    if lent_match:
        week = int(lent_match.group(1))
        return {"level": "lent", "label_en": f"Great Lent (Week {week})", "label_uk": f"Великий Піст (тиждень {week})"}
    
    # Paschal weeks
    easter_match = re.match(r'^0(\d)e$', fast)
    if easter_match:
        week = int(easter_match.group(1))
        return {"level": "paschal", "label_en": f"Paschal season (Week {week})", "label_uk": f"Пасхальний час (тиждень {week})"}
    
    # Weeks after Pentecost
    pent_match = re.match(r'^(\d+)d$', fast)
    if pent_match:
        week = int(pent_match.group(1))
        return {"level": "ordinary", "label_en": f"Week {week} after Pentecost", "label_uk": f"{week}-й тиждень після П'ятидесятниці"}
    
    return {"level": "unknown", "label_en": fast, "label_uk": fast}

def decode_rank(rank):
    """Convert rank code to human-readable."""
    rank_map = {
        "#": {"level": "great_feast", "label_en": "Great Feast", "label_uk": "Велике свято"},
        "@": {"level": "feast", "label_en": "Feast", "label_uk": "Свято"},
        "&": {"level": "polyeleos", "label_en": "Polyeleos", "label_uk": "Поліелей"},
        "+": {"level": "commemoration", "label_en": "Commemoration", "label_uk": "Святкування"},
        "*": {"level": "special", "label_en": "Special", "label_uk": "Особливий"},
        "-": {"level": "ordinary", "label_en": "Ordinary", "label_uk": "Звичайний"},
    }
    return rank_map.get(rank, {"level": "ordinary", "label_en": "Ordinary", "label_uk": "Звичайний"})

# ── English saints from the PWA ───────────────────────────────
def load_en_saints():
    """Load the EN_SAINTS from the PWA index.html (embedded JS object)."""
    pwa_path = os.path.join(BASE_DIR, "..", "PWA Site", "prayer-app", "index.html")
    if not os.path.exists(pwa_path):
        return {}
    
    with open(pwa_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the EN_SAINTS object
    match = re.search(r'const EN_SAINTS\s*=\s*\{(.*?)\};', content, re.DOTALL)
    if not match:
        return {}
    
    saints = {}
    # Parse the JS object entries
    for entry in re.finditer(r'"(\d{4})"\s*:\s*"((?:[^"\\]|\\.)*)"', match.group(1)):
        key = entry.group(1)
        value = entry.group(2).replace('\\"', '"').replace("\\'", "'")
        saints[key] = value
    
    return saints

# ── Main build ────────────────────────────────────────────────
def main():
    print("Loading calendar metadata...")
    cal_data = {}
    if os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, 'r', encoding='utf-8') as f:
            cal_data = json.load(f)
    
    print("Loading English saint names...")
    en_saints = load_en_saints()
    print(f"  Found {len(en_saints)} English saint entries")
    
    os.makedirs(API_DIR, exist_ok=True)
    
    year_calendar = []
    
    for month in range(1, 13):
        mm = f"{month:02d}"
        month_dir = os.path.join(RAW_DIR, mm)
        api_month_dir = os.path.join(API_DIR, mm)
        os.makedirs(api_month_dir, exist_ok=True)
        
        month_calendar = []
        
        days = DAYS_IN_MONTH[month]
        print(f"\nProcessing {MONTH_NAMES_EN[month]} ({days} days)...")
        
        for day in range(1, days + 1):
            dd = f"{day:02d}"
            key = f"{mm}{dd}"
            
            # Load calendar metadata
            cal_entry = cal_data.get(key, {})
            fast_code = cal_entry.get("fast", "")
            rank_code = cal_entry.get("rank", "-")
            tone = cal_entry.get("tone", 0)
            
            # Parse ustav
            ustav_html = read_file(os.path.join(month_dir, f"u{dd}.html"))
            ustav = parse_ustav(ustav_html)
            
            # Parse saints/synaxarion
            saints_html = read_file(os.path.join(month_dir, f"s{dd}.html"))
            saints_data = parse_saints(saints_html)
            
            # Parse services
            vespers_html = read_file(os.path.join(month_dir, f"t{dd}v.html"))
            matins_html = read_file(os.path.join(month_dir, f"t{dd}u.html"))
            compline_html = read_file(os.path.join(month_dir, f"t{dd}c.html"))
            
            has_vespers = vespers_html is not None
            has_matins = matins_html is not None
            has_compline = compline_html is not None
            
            # Build day entry
            day_entry = {
                "date": f"2026-{mm}-{dd}",
                "month": month,
                "day": day,
                "dayOfWeek": cal_entry.get("wd", 0),  # 1=Mon...7=Sun
                "tone": tone,
                "fast": decode_fast(fast_code),
                "fastCode": fast_code,
                "rank": decode_rank(rank_code),
                "rankCode": rank_code,
                "saints": {
                    "uk": ustav.get("saints", []),
                    "en": en_saints.get(key, ""),
                },
                "troparion": saints_data.get("troparion", ""),
                "kontakion": saints_data.get("kontakion", ""),
                "rubrics": ustav.get("rubrics", ""),
                "services": {
                    "vespers": has_vespers,
                    "matins": has_matins,
                    "compline": has_compline,
                }
            }
            
            # Calendar summary (lightweight)
            cal_summary = {
                "date": day_entry["date"],
                "dayOfWeek": day_entry["dayOfWeek"],
                "tone": tone,
                "fastCode": fast_code,
                "fast": day_entry["fast"]["label_en"],
                "rankCode": rank_code,
                "rank": day_entry["rank"]["label_en"],
                "saints_uk": "; ".join(ustav.get("saints", [])),
                "saints_en": en_saints.get(key, ""),
                "troparion": saints_data.get("troparion", "")[:200],
                "services": day_entry["services"],
            }
            
            month_calendar.append(cal_summary)
            year_calendar.append(cal_summary)
            
            # Full day file (includes service HTML if available)
            full_day = dict(day_entry)
            if has_vespers:
                full_day["vespers"] = {"html": vespers_html.strip()}
            if has_matins:
                full_day["matins"] = {"html": matins_html.strip()}
            if has_compline:
                full_day["compline"] = {"html": compline_html.strip()}
            # Synaxarion excluded pending copyright clearance with Svichado/Lutsyk
            
            # Write individual day file
            day_path = os.path.join(api_month_dir, f"{dd}.json")
            with open(day_path, 'w', encoding='utf-8') as f:
                json.dump(full_day, f, ensure_ascii=False, indent=2)
        
        # Write month calendar
        month_cal_path = os.path.join(api_month_dir, "calendar.json")
        with open(month_cal_path, 'w', encoding='utf-8') as f:
            json.dump({
                "year": 2026,
                "month": month,
                "monthName": {"en": MONTH_NAMES_EN[month], "uk": MONTH_NAMES_UK[month]},
                "days": month_calendar
            }, f, ensure_ascii=False, indent=2)
        
        services_count = sum(1 for d in month_calendar if d["services"]["vespers"])
        print(f"  ✓ {days} days, {services_count} with full services")
    
    # Write year calendar
    year_cal_path = os.path.join(API_DIR, "calendar.json")
    with open(year_cal_path, 'w', encoding='utf-8') as f:
        json.dump({
            "year": 2026,
            "totalDays": 365,
            "calendar": "UGCC (Gregorian)",
            "source": "prayer-service.pp.ua",
            "generated": "2026-05-01",
            "days": year_calendar
        }, f, ensure_ascii=False, indent=2)
    
    # Stats
    total_files = sum(1 for _, _, files in os.walk(API_DIR) for f in files if f.endswith('.json'))
    total_with_services = sum(1 for d in year_calendar if d["services"]["vespers"])
    
    print(f"\n{'='*50}")
    print(f"BUILD COMPLETE")
    print(f"  Output: {API_DIR}/")
    print(f"  JSON files: {total_files}")
    print(f"  Days with full services: {total_with_services}/365")
    print(f"  Days with calendar data: {len(year_calendar)}/365")
    print(f"  English saint names: {len(en_saints)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
