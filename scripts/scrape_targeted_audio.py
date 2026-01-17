#!/usr/bin/env python3
"""
Targeted Audio Scraper for Regional Dialects
Focuses on user-requested languages:
- Dutch (Flemish)
- French (Standard)
- Philippines (Tagalog, Cebuano, Iloko, Hiligaynon)
- Cameroon (Bassa, Pidgin, Fulfulde)
- Ivory Coast (Baoule)
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from scrape_jworg_audio import process_language, create_training_manifest

# Configuration
OUTPUT_DIR = Path("training_audio_regional")
MANIFEST_FILE = OUTPUT_DIR / "manifest_regional.jsonl"

# Targeted Languages List
TARGET_LANGUAGES = [
    {"code": "nl-be", "jwCode": "OBG", "name": "Dutch (Belgium)"},
    {"code": "fr", "jwCode": "F", "name": "French"},
    {"code": "bci", "jwCode": "AO", "name": "Baoule (Ivory Coast)"},
    {"code": "bas", "jwCode": "BS", "name": "Bassa (Cameroon)"},
    {"code": "wes", "jwCode": "PCM", "name": "Pidgin (Cameroon)"},
    {"code": "fub", "jwCode": "FD", "name": "Fulfulde (Cameroon)"},
    {"code": "tl", "jwCode": "TG", "name": "Tagalog (Philippines)"},
    {"code": "ceb", "jwCode": "CV", "name": "Cebuano (Philippines)"},
    {"code": "ilo", "jwCode": "IL", "name": "Iloko (Philippines)"},
    {"code": "hil", "jwCode": "HV", "name": "Hiligaynon (Philippines)"}
]

def main():
    print("=" * 70)
    print("TARGETED REGIONAL TRAINING DATA COLLECTION")
    print("=" * 70)
    print(f"Targeting {len(TARGET_LANGUAGES)} specific regional dialects.")
    print(f"Output: {OUTPUT_DIR}")
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    results = []
    successful = 0
    
    for i, lang in enumerate(TARGET_LANGUAGES):
        print(f"\nProcessing [{i+1}/{len(TARGET_LANGUAGES)}]: {lang['name']} ({lang['code']})...")
        try:
            # Re-using the robust logic from the main scraper
            result = process_language(lang, OUTPUT_DIR)
            results.append(result)
            
            if result["status"] == "success":
                successful += 1
                count = len(result['audio_files'])
                print(f"  ✓ Success: Found {count} aligned audio-text pairs.")
            else:
                print(f"  ✗ No data found (Status: {result['status']})")
                
            time.sleep(1) # Polite delay
            
        except Exception as e:
            print(f"  ! Error: {e}")
            
    # Create Manifest
    if successful > 0:
        print(f"\n[Creating Training Manifest]")
        create_training_manifest(results, MANIFEST_FILE)
        print(f"✓ Manifest saved: {MANIFEST_FILE}")
        print(f"\nNEXT STEPS:")
        print(f"1. Use 'training_audio_regional/' for STT/TTS fine-tuning.")
        print(f"2. Run: 'ct2-transformers-converter --model openai/whisper-large-v3 --output_dir stt_model --quantization float16'")
    else:
        print("\nNo data collected. Check internet connection or JW.org accessibility.")

if __name__ == "__main__":
    main()
