import os
import json
import librosa
import torch
from datasets import Dataset, Audio, DatasetDict
from transformers import WhisperProcessor

# Configuration
DATA_DIR = "../data"
OUTPUT_DIR = "../hf_dataset"
MODEL_NAME = "openai/whisper-large-v3"
LANGUAGE = "English"

def load_jw_data(data_dir):
    """
    Expects a data layout:
    data/audio_01.mp3
    data/audio_01.json -> {"text": "..."}
    """
    audio_paths = []
    transcripts = []
    
    for filename in os.listdir(data_dir):
        if filename.endswith(".mp3"):
            basename = os.path.splitext(filename)[0]
            json_path = os.path.join(data_dir, f"{basename}.json")
            
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    audio_paths.append(os.path.join(data_dir, filename))
                    transcripts.append(meta.get("text", ""))
                    
    return audio_paths, transcripts

def prepare_dataset():
    processor = WhisperProcessor.from_pretrained(MODEL_NAME)
    audio_paths, transcripts = load_jw_data(DATA_DIR)
    
    dataset = Dataset.from_dict({
        "audio": audio_paths,
        "sentence": transcripts
    })
    
    # Cast audio column to Audio feature with 16kHz
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    
    def prepare_item(batch):
        # Load and compute input features
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"], 
            sampling_rate=audio["sampling_rate"]
        ).input_features[0]
        
        # Tokenize transcripts
        batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
        return batch

    print(f"Loaded {len(dataset)} items. Processing...")
    
    # We apply the transformation
    # Note: For large datasets, use .map() with num_proc
    dataset = dataset.map(prepare_item, remove_columns=dataset.column_names)
    
    # Split into train/test
    ds_split = dataset.train_test_split(test_size=0.1)
    
    ds_split.save_to_disk(OUTPUT_DIR)
    print(f"Dataset saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Please put your .mp3 and .json files in {DATA_DIR}")
    else:
        prepare_dataset()
