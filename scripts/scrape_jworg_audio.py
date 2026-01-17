#!/usr/bin/env python3
"""
JW.org Audio Scraper
Scrapes audio content from JW.org for STT/TTS training.
Creates audio-text parallel datasets for fine-tuning Whisper and TTS models.
"""

import json
import os
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple
from urllib.parse import urljoin

# Configuration
OUTPUT_DIR = Path("training_audio")
MANIFEST_FILE = OUTPUT_DIR / "manifest.jsonl"
CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/json,audio/*",
}

# JW.org audio API endpoints
JW_API_BASE = "https://b.jw-cdn.org/apis/mediator/v1"
JW_SITE_BASE = "https://www.jw.org"


def load_languages() -> list:
    """Load languages from jw_languages.js"""
    js_file = Path("jw_languages.js")
    if not js_file.exists():
        js_file = Path("../jw_languages.js")
    
    content = js_file.read_text(encoding="utf-8")
    match = re.search(r'const JW_LANGUAGES = (\[.*\]);', content, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return []


def get_audio_publications(lang_code: str) -> list:
    """Get list of audio publications available in a language."""
    # JW.org media API for audio publications
    url = f"{JW_API_BASE}/categories/{lang_code}/AudioBooks"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            publications = []
            
            if "category" in data and "subcategories" in data["category"]:
                for subcat in data["category"]["subcategories"]:
                    publications.append({
                        "key": subcat.get("key"),
                        "name": subcat.get("name"),
                        "description": subcat.get("description", "")
                    })
            
            return publications
    except Exception as e:
        print(f"  Error fetching publications for {lang_code}: {e}")
    
    return []


def get_bible_audio(lang_code: str, book_num: int = 43, chapter: int = 3) -> Optional[dict]:
    """
    Get Bible audio for a specific chapter.
    Default: John 3 (book 43 in JW numbering)
    
    Returns dict with audio_url, transcript, duration
    """
    # JW.org Bible audio endpoint
    url = f"https://www.jw.org/{lang_code}/library/bible/study-bible/books/"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find audio player data
        audio_player = soup.find('div', class_='jsAudioPlayer')
        if audio_player:
            audio_url = audio_player.get('data-jsonurl')
            
            if audio_url:
                # Fetch audio metadata
                audio_response = requests.get(audio_url, headers=HEADERS, timeout=30)
                if audio_response.status_code == 200:
                    audio_data = audio_response.json()
                    
                    return {
                        "language": lang_code,
                        "source": "bible",
                        "audio_url": audio_data.get("files", [{}])[0].get("progressiveDownloadURL"),
                        "duration_sec": audio_data.get("duration", 0),
                        "book": book_num,
                        "chapter": chapter
                    }
    except Exception as e:
        pass
    
    return None


def download_audio(url: str, output_path: Path) -> bool:
    """Download audio file."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"  Download error: {e}")
    return False


def extract_text_from_page(url: str) -> str:
    """Extract text content from a JW.org page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove non-content elements
            for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                elem.decompose()
            
            # Get article content
            article = soup.find('article') or soup.find('div', class_='article')
            if article:
                paragraphs = article.find_all('p')
                return " ".join([p.get_text(strip=True) for p in paragraphs])
    except:
        pass
    return ""


def fetch_daily_text_audio(lang_code: str, date_str: str = None) -> Optional[dict]:
    """
    Fetch Daily Text with audio.
    Daily texts have aligned audio and text - perfect for training!
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y/%m/%d")
    
    # Daily text URL pattern
    url = f"https://wol.jw.org/{lang_code}/wol/dt/r1/lp-e/{date_str}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get text content
        text_elem = soup.find('div', class_='bodyTxt')
        if not text_elem:
            return None
        
        text = text_elem.get_text(strip=True)
        
        # Look for audio link
        audio_link = soup.find('a', class_='jsAudioLink')
        audio_url = None
        if audio_link:
            audio_url = audio_link.get('href')
        
        return {
            "language": lang_code,
            "source": "daily_text",
            "date": date_str,
            "text": text,
            "audio_url": audio_url
        }
    except Exception as e:
        pass
    
    return None


def process_language(lang: dict, output_dir: Path) -> dict:
    """Process a single language - fetch available audio content."""
    code = lang['code']
    jw_code = lang['jwCode']
    name = lang['name']
    
    # Skip sign languages for audio
    if 'Sign' in name:
        return {"code": code, "status": "skipped", "reason": "sign_language"}
    
    result = {
        "code": code,
        "jwCode": jw_code,
        "name": name,
        "audio_files": [],
        "status": "processing"
    }
    
    lang_dir = output_dir / code
    lang_dir.mkdir(parents=True, exist_ok=True)
    
    # Try to get Daily Text (best alignment)
    daily = fetch_daily_text_audio(code)
    if daily and daily.get("audio_url"):
        audio_path = lang_dir / f"daily_text_{datetime.now().strftime('%Y%m%d')}.mp3"
        if download_audio(daily["audio_url"], audio_path):
            result["audio_files"].append({
                "type": "daily_text",
                "audio": str(audio_path),
                "text": daily.get("text", ""),
                "duration": 60  # Approximate
            })
    
    # Try to get Bible audio
    bible = get_bible_audio(code)
    if bible and bible.get("audio_url"):
        audio_path = lang_dir / f"john_3.mp3"
        if download_audio(bible["audio_url"], audio_path):
            result["audio_files"].append({
                "type": "bible",
                "audio": str(audio_path),
                "book": 43,
                "chapter": 3,
                "duration": bible.get("duration_sec", 0)
            })
    
    result["status"] = "success" if result["audio_files"] else "no_audio"
    return result


def create_training_manifest(results: list, output_file: Path):
    """Create a training manifest in JSONL format."""
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            if result["status"] != "success":
                continue
            
            for audio_file in result["audio_files"]:
                entry = {
                    "audio_filepath": audio_file["audio"],
                    "text": audio_file.get("text", ""),
                    "duration": audio_file.get("duration", 0),
                    "language": result["code"],
                    "language_name": result["name"],
                    "source": audio_file.get("type", "unknown")
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    print("=" * 70)
    print("JW.org Audio Scraper for STT/TTS Training")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Load languages
    languages = load_languages()
    print(f"\nTotal languages: {len(languages)}")
    
    # Filter non-sign languages
    audio_languages = [l for l in languages if 'Sign' not in l.get('name', '')]
    print(f"Languages with potential audio: {len(audio_languages)}")
    
    # Load checkpoint if exists
    start_idx = 0
    results = []
    if CHECKPOINT_FILE.exists():
        checkpoint = json.loads(CHECKPOINT_FILE.read_text())
        start_idx = checkpoint.get("last_index", 0) + 1
        results = checkpoint.get("results", [])
        print(f"Resuming from checkpoint: index {start_idx}")
    
    print(f"\n[Scraping Audio Content]")
    print("-" * 50)
    
    successful = len([r for r in results if r.get("status") == "success"])
    
    for i, lang in enumerate(audio_languages[start_idx:], start=start_idx):
        try:
            result = process_language(lang, OUTPUT_DIR)
            results.append(result)
            
            if result["status"] == "success":
                successful += 1
                print(f"  [{i+1}/{len(audio_languages)}] ✓ {lang['name']} - {len(result['audio_files'])} files")
            else:
                print(f"  [{i+1}/{len(audio_languages)}] ✗ {lang['name']} - {result['status']}")
            
            # Rate limiting
            time.sleep(0.5)
            
            # Save checkpoint every 50 languages
            if (i + 1) % 50 == 0:
                checkpoint = {"last_index": i, "results": results}
                CHECKPOINT_FILE.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
                print(f"  → Checkpoint saved at {i+1}")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted! Saving checkpoint...")
            checkpoint = {"last_index": i - 1, "results": results}
            CHECKPOINT_FILE.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
            break
        except Exception as e:
            print(f"  Error processing {lang['name']}: {e}")
            continue
    
    # Create training manifest
    print(f"\n[Creating Training Manifest]")
    create_training_manifest(results, MANIFEST_FILE)
    print(f"✓ Manifest saved: {MANIFEST_FILE}")
    
    # Summary
    print(f"\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f"  Languages processed: {len(results)}")
    print(f"  Languages with audio: {successful}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"  Finished: {datetime.now().isoformat()}")
    
    return results


if __name__ == "__main__":
    main()
