import os
import torch
from datasets import load_from_disk
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Configuration
MODEL_NAME = "openai/whisper-large-v3"
DATASET_DIR = "../hf_dataset"
OUTPUT_DIR = "../output"

@torch.no_grad()
def train():
    # 1. Load Data
    dataset = load_from_disk(DATASET_DIR)
    
    # 2. Load Model & Processor
    processor = WhisperProcessor.from_pretrained(MODEL_NAME)
    model = WhisperForConditionalGeneration.from_pretrained(
        MODEL_NAME, 
        load_in_8bit=True, 
        device_map="auto"
    )
    
    # 3. Prepare for LoRA
    model = prepare_model_for_kbit_training(model)
    
    config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none"
    )
    
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    
    # 4. Data Collator
    class DataCollatorSpeechSeq2SeqWithPadding:
        def __call__(self, features):
            input_features = [{"input_features": feature["input_features"]} for feature in features]
            batch = processor.feature_extractor.pad(input_features, return_tensors="pt")
            
            label_features = [{"input_ids": feature["labels"]} for feature in features]
            labels_batch = processor.tokenizer.pad(label_features, return_tensors="pt")
            
            # replace padding with -100 to ignore loss correctly
            labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
            batch["labels"] = labels
            
            return batch

    data_collator = DataCollatorSpeechSeq2SeqWithPadding()
    
    # 5. Training Arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=2,
        learning_rate=1e-3,
        warmup_steps=50,
        max_steps=500,
        gradient_checkpointing=True,
        fp16=True,
        evaluation_strategy="steps",
        per_device_eval_batch_size=8,
        predict_with_generate=True,
        generation_max_length=225,
        save_steps=100,
        eval_steps=100,
        logging_steps=25,
        report_to=["tensorboard"],
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        greater_is_better=False,
        push_to_hub=False,
        remove_unused_columns=False, # Required for customized data collator
    )
    
    # 6. Trainer
    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        data_collator=data_collator,
        tokenizer=processor.feature_extractor,
    )
    
    # 7. Start Training
    model.config.use_cache = False  # silence the warnings. Please re-enable for inference!
    trainer.train()
    
    # Save the final model
    trainer.save_model(OUTPUT_DIR)
    print(f"Training complete! Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    if not os.path.exists(DATASET_DIR):
        print(f"Dataset not found at {DATASET_DIR}. Run prepare_dataset.py first.")
    else:
        train()
