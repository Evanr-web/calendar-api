#!/usr/bin/env python3
"""
Extract scripture readings from ustav files and add English references to API.
Parses the Ап. (Apostol/Epistle) and Єв. (Gospel) references from the Літургія section.
"""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(BASE_DIR, "api", "2026")
RAW_DIR = os.path.join(BASE_DIR, "raw")

DAYS_IN_MONTH = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

# Ukrainian book abbreviations → English
BOOK_MAP = {
    # Gospels
    'Мт': 'Matthew', 'Мт.': 'Matthew',
    'Мр': 'Mark', 'Мр.': 'Mark',
    'Лк': 'Luke', 'Лк.': 'Luke',
    'Ів': 'John', 'Ів.': 'John',
    'Йн': 'John', 'Йн.': 'John',
    # Acts
    'Ді': 'Acts', 'Ді.': 'Acts', 'Діян': 'Acts',
    # Pauline Epistles
    'Рим': 'Romans', 'Рим.': 'Romans',
    '1 Кор': '1 Corinthians', 'І Кор': '1 Corinthians',
    '2 Кор': '2 Corinthians', 'ІІ Кор': '2 Corinthians',
    'Гал': 'Galatians', 'Гал.': 'Galatians',
    'Еф': 'Ephesians', 'Еф.': 'Ephesians',
    'Фил': 'Philippians', 'Фил.': 'Philippians', 'Филип': 'Philippians',
    'Кол': 'Colossians', 'Кол.': 'Colossians',
    '1 Сол': '1 Thessalonians', 'І Сол': '1 Thessalonians',
    '2 Сол': '2 Thessalonians', 'ІІ Сол': '2 Thessalonians',
    '1 Тим': '1 Timothy', 'І Тим': '1 Timothy',
    '2 Тим': '2 Timothy', 'ІІ Тим': '2 Timothy',
    'Тит': 'Titus', 'Тит.': 'Titus',
    'Флм': 'Philemon',
    'Флп': 'Philippians', 'Флп.': 'Philippians',
    'Євр': 'Hebrews', 'Євр.': 'Hebrews',
    # Catholic Epistles
    'Як': 'James', 'Як.': 'James',
    '1 Пт': '1 Peter', 'І Пт': '1 Peter', '1 Петр': '1 Peter',
    '2 Пт': '2 Peter', 'ІІ Пт': '2 Peter', '2 Петр': '2 Peter',
    '1 Ів': '1 John', 'І Ів': '1 John', '1 Йн': '1 John',
    '2 Ів': '2 John', 'ІІ Ів': '2 John',
    '3 Ів': '3 John', 'ІІІ Ів': '3 John',
    'Юд': 'Jude', 'Юд.': 'Jude',
    # Revelation
    'Об': 'Revelation', 'Об.': 'Revelation', 'Откр': 'Revelation',
    # OT books (for readings/paremia)
    'Бт': 'Genesis', 'Бт.': 'Genesis',
    'Вих': 'Exodus', 'Вих.': 'Exodus',
    'Чис': 'Numbers',
    'Іс': 'Isaiah', 'Іс.': 'Isaiah',
    'Єр': 'Jeremiah',
    'Прит': 'Proverbs', 'Притч': 'Proverbs',
    'Прем': 'Wisdom',
}

def translate_book(uk_book):
    """Translate Ukrainian book abbreviation to English."""
    uk_book = uk_book.strip().rstrip('.')
    # Try exact match first
    if uk_book in BOOK_MAP:
        return BOOK_MAP[uk_book]
    if uk_book + '.' in BOOK_MAP:
        return BOOK_MAP[uk_book + '.']
    # Try with period
    for key, val in BOOK_MAP.items():
        if uk_book.startswith(key.rstrip('.')):
            return val
    return uk_book  # Return original if no match

def parse_reading(text):
    """
    Parse a reading reference like 'Ді. 27 зач.; 10, 44-11,10'
    Returns dict with book, pericope, chapter_verse, and English reference.
    """
    if not text:
        return None
    
    text = text.strip().rstrip('.')
    
    # Pattern: Book [pericope] зач.; chapter, verses
    # Examples:
    #   Ді. 27 зач.; 10, 44-11,10
    #   Рим. 83 зач.; 2, 28 – 3, 18
    #   Мт. 19 зач.; 6, 31-34; 7, 9-11
    #   1 Кор. 143 зач.; 9, 19 – 27
    
    # Extract book name (may start with number like "1 Кор")
    book_match = re.match(r'^((?:\d\s+|І{1,3}\s+)?[А-ЯІЇЄҐа-яіїєґ]+\.?)\s*', text)
    if not book_match:
        return None
    
    uk_book = book_match.group(1).strip()
    en_book = translate_book(uk_book)
    remainder = text[book_match.end():]
    
    # Extract pericope number
    pericope = None
    pericope_match = re.match(r'(\d+)\s*зач\.?\s*;?\s*', remainder)
    if pericope_match:
        pericope = int(pericope_match.group(1))
        remainder = remainder[pericope_match.end():]
    
    # The rest is chapter:verse reference
    chapter_verse = remainder.strip().rstrip('.').strip()
    # Clean up spaces around dashes and commas
    chapter_verse = re.sub(r'\s*[–—-]\s*', '-', chapter_verse)
    
    # Clean chapter_verse: remove trailing noise
    chapter_verse = re.sub(r'\s*[ЄА][вп]\..*$', '', chapter_verse)  # Remove trailing Єв./Ап. refs
    chapter_verse = re.sub(r'\s*Замість.*$', '', chapter_verse)
    chapter_verse = re.sub(r'\s*Причасн.*$', '', chapter_verse)
    chapter_verse = re.sub(r'\s*зач\.\s*', '', chapter_verse)  # Remove stray зач.
    chapter_verse = chapter_verse.strip().rstrip(';.,').strip()
    
    # Build English reference
    en_ref = f"{en_book} {chapter_verse}" if chapter_verse else en_book
    
    return {
        "book_uk": uk_book,
        "book_en": en_book,
        "pericope": pericope,
        "reference": chapter_verse,
        "display": en_ref
    }

def extract_readings_from_ustav(html):
    """Extract Apostol and Gospel readings from ustav HTML."""
    if not html:
        return None
    
    readings = {}
    
    # Find the Літургія section
    lit_match = re.search(r'(?:Літургія|Літ\.)[^:]*:(.*?)(?:<p><i>(?!Літ)|$)', html, re.DOTALL | re.IGNORECASE)
    if not lit_match:
        lit_match = re.search(r'(?:Літургія|Літ\.)(.*?)$', html, re.DOTALL | re.IGNORECASE)
    
    if not lit_match:
        return None
    
    lit_text = lit_match.group(1)
    # Strip HTML tags for easier parsing
    lit_text = re.sub(r'<[^>]+>', ' ', lit_text)
    lit_text = re.sub(r'\s+', ' ', lit_text).strip()
    
    # Find Apostol reading: Ап. – [Book] [pericope] зач.; [ch:vs]
    ap_match = re.search(r'\bАп\.?\s*[–—\-]\s*([\wЀ-ӿ]+\.?\s*(?:зач\.?\s*)?\d[^;]*;[^.]*\.?)', lit_text)
    if not ap_match:
        # Fallback: looser match
        ap_match = re.search(r'\bАп\.?\s*[–—\-]\s*(.*?)(?=\s*Єв\b|$)', lit_text)
    if ap_match:
        ap_text = ap_match.group(1).strip().rstrip('.;').strip()
        reading = parse_reading(ap_text)
        if reading:
            readings["epistle"] = reading
    
    # Find Gospel reading: Єв. – [Book] [pericope] зач.; [ch:vs]
    ev_match = re.search(r'\bЄв\.?\s*[–—\-]\s*([\wЀ-ӿ]+\.?\s*(?:зач\.?\s*)?\d[^;]*;[^.]*\.?)', lit_text)
    if not ev_match:
        # Fallback: looser match up to sentence boundary keywords
        ev_match = re.search(r'\bЄв\.?\s*[–—\-]\s*(.*?)(?=\s*Замість|\s*Причасний|\s*По відпусті|$)', lit_text)
    if ev_match:
        ev_text = ev_match.group(1).strip().rstrip('.;').strip()
        reading = parse_reading(ev_text)
        if reading:
            readings["gospel"] = reading
    
    return readings if readings else None

def main():
    total = 0
    with_readings = 0
    
    for month in range(1, 13):
        mm = f"{month:02d}"
        month_count = 0
        
        for day in range(1, DAYS_IN_MONTH[month] + 1):
            dd = f"{day:02d}"
            total += 1
            
            # Read ustav
            ustav_path = os.path.join(RAW_DIR, mm, f"u{dd}.html")
            if not os.path.exists(ustav_path):
                continue
            
            with open(ustav_path, 'r', encoding='utf-8') as f:
                ustav_html = f.read()
            
            readings = extract_readings_from_ustav(ustav_html)
            
            if readings:
                with_readings += 1
                month_count += 1
                
                # Update the API day file
                api_path = os.path.join(API_DIR, mm, f"{dd}.json")
                if os.path.exists(api_path):
                    with open(api_path, 'r', encoding='utf-8') as f:
                        api_data = json.load(f)
                    
                    api_data["readings"] = readings
                    
                    with open(api_path, 'w', encoding='utf-8') as f:
                        json.dump(api_data, f, ensure_ascii=False, indent=2)
        
        print(f"  Month {mm}: {month_count} days with readings")
    
    print(f"\nTotal: {with_readings}/{total} days with scripture readings extracted")

if __name__ == "__main__":
    main()
