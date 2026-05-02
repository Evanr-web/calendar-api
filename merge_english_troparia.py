#!/usr/bin/env python3
"""
Merge OCA English troparia into the Calendar API.
Matches by primary saint name against our UGCC calendar.
Adds english troparion/kontakion fields to each day's JSON.
"""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(BASE_DIR, "api", "2026")
OCA_DIR = os.path.join(BASE_DIR, "oca_troparia")

DAYS_IN_MONTH = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

def normalize(name):
    """Normalize a saint name for fuzzy matching."""
    name = name.lower()
    # Remove common prefixes/suffixes
    name = re.sub(r'^(the |holy |saint |st\.? |sts\.? |venerable |blessed |ven\.? |hieromartyr |martyr |prophet |apostle |equal-to-the-apostles? )', '', name)
    name = re.sub(r'\s*\(.*?\)', '', name)  # Remove parentheticals
    name = re.sub(r',.*$', '', name)  # Remove everything after comma
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def match_saint(en_saints, uk_saints_text, en_saint_name_from_api):
    """
    Try to match OCA saints to our UGCC calendar entry.
    Returns the best matching OCA saint entry, or the first one as fallback.
    """
    if not en_saints:
        return None
    
    # Normalize the English saint name from our API
    api_name = normalize(en_saint_name_from_api) if en_saint_name_from_api else ""
    
    # Try exact-ish match on primary saint
    for saint in en_saints:
        oca_name = normalize(saint["name"])
        # Check if key words overlap
        api_words = set(api_name.split())
        oca_words = set(oca_name.split())
        if api_words and oca_words:
            overlap = api_words & oca_words
            # If we share significant words (not just "the", "of", etc.)
            significant = overlap - {"the", "of", "and", "our", "in", "to", "for", "a"}
            if len(significant) >= 1:
                return saint
    
    # For Great Feasts, check for feast-specific keywords
    feast_keywords = {
        "nativity": ["nativity", "christmas"],
        "theophany": ["theophany", "baptism", "epiphany"],
        "annunciation": ["annunciation"],
        "transfiguration": ["transfiguration"],
        "dormition": ["dormition", "assumption"],
        "exaltation": ["exaltation", "cross"],
        "presentation": ["presentation", "encounter", "meeting"],
        "entry": ["entry", "entrance", "temple"],
        "ascension": ["ascension"],
        "pentecost": ["pentecost"],
        "palm": ["palm", "entry into jerusalem"],
        "pascha": ["pascha", "resurrection", "easter"],
    }
    
    for keyword_group in feast_keywords.values():
        if any(kw in api_name for kw in keyword_group):
            for saint in en_saints:
                oca_name_lower = saint["name"].lower()
                if any(kw in oca_name_lower for kw in keyword_group):
                    return saint
    
    # Fallback: return the first saint (usually the primary commemoration)
    return en_saints[0] if en_saints else None

def main():
    matched = 0
    unmatched = 0
    total = 0
    
    for month in range(1, 13):
        mm = f"{month:02d}"
        
        for day in range(1, DAYS_IN_MONTH[month] + 1):
            dd = f"{day:02d}"
            total += 1
            
            api_path = os.path.join(API_DIR, mm, f"{dd}.json")
            oca_path = os.path.join(OCA_DIR, mm, f"{dd}.json")
            
            if not os.path.exists(api_path):
                continue
            
            with open(api_path, 'r', encoding='utf-8') as f:
                api_data = json.load(f)
            
            # Load OCA data
            oca_saints = []
            if os.path.exists(oca_path):
                with open(oca_path, 'r', encoding='utf-8') as f:
                    oca_data = json.load(f)
                oca_saints = oca_data.get("saints", [])
            
            # Match
            en_saint_name = api_data.get("saints", {}).get("en", "")
            uk_saints = api_data.get("saints", {}).get("uk", [])
            uk_text = " ".join(uk_saints) if isinstance(uk_saints, list) else str(uk_saints)
            
            best_match = match_saint(oca_saints, uk_text, en_saint_name)
            
            if best_match:
                matched += 1
                
                # Add English troparion
                if best_match.get("troparion"):
                    api_data["troparion_en"] = {
                        "tone": best_match["troparion"]["tone"],
                        "text": best_match["troparion"]["text"],
                        "source": "OCA"
                    }
                
                # Add English kontakion
                if best_match.get("kontakion"):
                    api_data["kontakion_en"] = {
                        "tone": best_match["kontakion"]["tone"],
                        "text": best_match["kontakion"]["text"],
                        "source": "OCA"
                    }
                
                # Store the matched OCA saint name for reference
                api_data["matched_oca_saint"] = best_match["name"]
                
                # Also store ALL OCA saints for the day (secondary commemorations)
                api_data["oca_saints"] = [
                    {
                        "name": s["name"],
                        "troparion": s.get("troparion"),
                        "kontakion": s.get("kontakion")
                    }
                    for s in oca_saints
                ]
            else:
                unmatched += 1
            
            # Write back
            with open(api_path, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)
    
    # Also update the calendar.json files with English troparion previews
    for month in range(1, 13):
        mm = f"{month:02d}"
        cal_path = os.path.join(API_DIR, mm, "calendar.json")
        if not os.path.exists(cal_path):
            continue
        
        with open(cal_path, 'r', encoding='utf-8') as f:
            cal_data = json.load(f)
        
        for day_entry in cal_data.get("days", []):
            date = day_entry.get("date", "")
            if not date:
                continue
            parts = date.split("-")
            if len(parts) != 3:
                continue
            dd = parts[2]
            
            day_path = os.path.join(API_DIR, mm, f"{dd}.json")
            if os.path.exists(day_path):
                with open(day_path, 'r', encoding='utf-8') as f:
                    day_data = json.load(f)
                if day_data.get("troparion_en"):
                    day_entry["troparion_en"] = day_data["troparion_en"]["text"][:200]
        
        with open(cal_path, 'w', encoding='utf-8') as f:
            json.dump(cal_data, f, ensure_ascii=False, indent=2)
    
    print(f"Total days: {total}")
    print(f"Matched: {matched}")
    print(f"Unmatched: {unmatched}")
    print(f"Match rate: {matched/total*100:.1f}%")

if __name__ == "__main__":
    main()
