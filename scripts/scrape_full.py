#!/usr/bin/env python3
"""
JW.org Full Training Data Scraper
Scrapes all 1,139 languages and creates parallel text training data.
"""

import json
import os
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

OUTPUT_DIR = Path("training_data")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/json",
}

def load_languages():
    """Load languages from jw_languages.js"""
    js_file = Path("jw_languages.js")
    content = js_file.read_text(encoding="utf-8")
    match = re.search(r'const JW_LANGUAGES = (\[.*\]);', content, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return []

def fetch_page_content(url: str) -> str:
    """Fetch and extract text from a URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get main content
            main = soup.find('main') or soup.find('article') or soup.find('body')
            if main:
                return main.get_text(separator=' ', strip=True)
        return ""
    except:
        return ""

def fetch_language_content(lang: dict) -> dict:
    """Fetch content for a single language."""
    code = lang['code']
    jw_code = lang['jwCode']
    name = lang['name']
    
    # Skip sign languages
    if 'Sign' in name and 'Language' in name:
        return None
    
    # Fetch homepage
    home_url = f"https://www.jw.org/{code.lower()}/"
    home_text = fetch_page_content(home_url)
    
    if not home_text or len(home_text) < 100:
        return None
    
    # Try to fetch a known publication (Good News brochure)
    pub_url = f"https://www.jw.org/{code.lower()}/library/books/good-news-from-god/"
    pub_text = fetch_page_content(pub_url)
    
    return {
        "code": code,
        "jwCode": jw_code,
        "name": name,
        "home_text": home_text[:3000],
        "pub_text": pub_text[:5000] if pub_text else ""
    }

def create_training_pairs(data: list) -> list:
    """Create parallel training pairs with English as source."""
    # Find English data
    english = next((d for d in data if d and d['code'] == 'en'), None)
    
    if not english:
        print("WARNING: English not found in data!")
        # Use first available as reference
        english = next((d for d in data if d), None)
    
    if not english:
        return []
    
    pairs = []
    for lang_data in data:
        if lang_data and lang_data['code'] != english['code']:
            # Create instruction-style training format
            pairs.append({
                "instruction": f"Translate the following text to {lang_data['name']}",
                "input": english['home_text'][:500],
                "output": lang_data['home_text'][:500],
                "source_lang": english['code'],
                "target_lang": lang_data['code'],
                "target_name": lang_data['name']
            })
            
            # Add reverse pair (target -> English)
            pairs.append({
                "instruction": f"Translate the following {lang_data['name']} text to English",
                "input": lang_data['home_text'][:500],
                "output": english['home_text'][:500],
                "source_lang": lang_data['code'],
                "target_lang": english['code'],
                "target_name": "English"
            })
    
    return pairs

def main():
    print("=" * 70)
    print("JW.org Full Training Data Scraper")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    
    languages = load_languages()
    # Filter out sign languages for text scraping
    text_languages = [l for l in languages if 'Sign' not in l['name']]
    
    print(f"\nTotal languages: {len(languages)}")
    print(f"Text languages (non-sign): {len(text_languages)}")
    
    print(f"\n[Phase 1] Scraping content from all languages...")
    print("-" * 50)
    
    successful_data = []
    failed = 0
    
    for i, lang in enumerate(text_languages):
        result = fetch_language_content(lang)
        
        if result:
            successful_data.append(result)
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(text_languages)}] ✓ {lang['name']} - Total: {len(successful_data)}")
        else:
            failed += 1
        
        # Rate limiting
        time.sleep(0.3)
        
        # Save checkpoint every 100 languages
        if (i + 1) % 100 == 0:
            checkpoint = OUTPUT_DIR / f"raw_data_checkpoint_{i+1}.json"
            with open(checkpoint, "w", encoding="utf-8") as f:
                json.dump(successful_data, f, ensure_ascii=False, indent=2)
            print(f"  → Checkpoint: {checkpoint} ({len(successful_data)} languages)")
    
    # Save raw data
    raw_file = OUTPUT_DIR / "jw_raw_content.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump({
            "scraped_at": datetime.now().isoformat(),
            "total_successful": len(successful_data),
            "total_failed": failed,
            "data": successful_data
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Raw data saved: {raw_file}")
    
    print(f"\n[Phase 2] Creating training pairs...")
    print("-" * 50)
    
    training_pairs = create_training_pairs(successful_data)
    
    # Save training data in MLX format
    train_file = OUTPUT_DIR / "jw_training_pairs.jsonl"
    with open(train_file, "w", encoding="utf-8") as f:
        for pair in training_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    
    print(f"✓ Training pairs saved: {train_file}")
    print(f"  Total pairs: {len(training_pairs)}")
    
    # Create summary
    print(f"\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f"  Languages scraped: {len(successful_data)}")
    print(f"  Failed: {failed}")
    print(f"  Training pairs: {len(training_pairs)}")
    print(f"  Finished: {datetime.now().isoformat()}")
    
    return successful_data, training_pairs

if __name__ == "__main__":
    main()
