#!/usr/bin/env python3
"""
JW.org Content Scraper v2
Uses jw.org's public media API for parallel content extraction.
"""

import json
import os
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("training_data")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
}

def load_languages():
    """Load languages from jw_languages.js"""
    js_file = Path("jw_languages.js")
    content = js_file.read_text(encoding="utf-8")
    match = re.search(r'const JW_LANGUAGES = (\[.*\]);', content, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return []

def fetch_jw_page(lang_code: str, path: str) -> dict:
    """Fetch a page from jw.org in a specific language."""
    # jw.org uses lowercase lang codes in paths
    url = f"https://www.jw.org/{lang_code.lower()}{path}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main article content
            article = soup.find('article') or soup.find('div', class_='article')
            if article:
                # Get all paragraphs
                paragraphs = article.find_all('p')
                text = " ".join([p.get_text(strip=True) for p in paragraphs])
                return {"url": url, "text": text, "status": "success"}
            
            # Fallback: get body text
            body = soup.find('body')
            if body:
                return {"url": url, "text": body.get_text(strip=True)[:5000], "status": "partial"}
        
        return {"url": url, "status": "failed", "code": response.status_code}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}

def fetch_bible_verse_api(book_num: int, chapter: int, lang_symbol: str) -> dict:
    """Fetch Bible chapter using JW API."""
    # JW.org Bible API
    url = f"https://www.jw.org/en/library/bible/study-bible/books/json/"
    
    try:
        # Try the standard Bible page
        bible_url = f"https://www.jw.org/{lang_symbol.lower()}/library/bible/study-bible/books/"
        response = requests.get(bible_url, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            return {"status": "success", "html": response.text[:10000]}
        return {"status": "failed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def scrape_parallel_publications():
    """Scrape publications that exist in multiple languages."""
    print("=" * 70)
    print("JW.org Parallel Content Scraper v2")
    print("=" * 70)
    
    languages = load_languages()
    print(f"\nLoaded {len(languages)} languages")
    
    # Filter to languages with web content
    web_languages = [l for l in languages if 'Sign' not in l['name']]
    print(f"Languages with potential web content: {len(web_languages)}")
    
    # Known parallel content paths (same content in all languages)
    parallel_paths = [
        "/library/books/good-news-from-god/",  # Tract available in many languages
        "/library/books/listen-to-god/",
        "/library/books/real-faith/",
    ]
    
    results = {
        "languages_tested": 0,
        "successful": 0,
        "data": []
    }
    
    # Test first 50 languages to check availability
    test_languages = web_languages[:50]
    
    print(f"\n[Phase 1] Testing {len(test_languages)} languages for content availability")
    print("-" * 50)
    
    for i, lang in enumerate(test_languages):
        code = lang['code']
        jw_code = lang['jwCode']
        name = lang['name']
        
        # Try to fetch homepage to verify language is accessible
        home_url = f"https://www.jw.org/{code.lower()}/"
        
        try:
            response = requests.get(home_url, headers=HEADERS, timeout=15, allow_redirects=True)
            
            if response.status_code == 200 and len(response.text) > 1000:
                # Extract some text from the page
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find article or main content
                main = soup.find('main') or soup.find('article') or soup.find('body')
                if main:
                    text_content = main.get_text(separator=' ', strip=True)[:2000]
                    
                    results["data"].append({
                        "code": code,
                        "jwCode": jw_code,
                        "name": name,
                        "sample_text": text_content,
                        "url": home_url
                    })
                    results["successful"] += 1
                    print(f"  [{i+1}/{len(test_languages)}] ✓ {name} ({code})")
            else:
                print(f"  [{i+1}/{len(test_languages)}] ✗ {name} - No content")
        
        except Exception as e:
            print(f"  [{i+1}/{len(test_languages)}] ✗ {name} - Error: {str(e)[:50]}")
        
        results["languages_tested"] += 1
        time.sleep(0.5)  # Rate limiting
    
    # Save results
    output_file = OUTPUT_DIR / "jw_content_test.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print(f"  Languages tested: {results['languages_tested']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Output: {output_file}")
    
    return results

if __name__ == "__main__":
    scrape_parallel_publications()
