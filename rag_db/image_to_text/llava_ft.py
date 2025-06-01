import torch
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset
from transformers import LlavaForConditionalGeneration, LlavaProcessor, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from PIL import Image
from datasets import load_dataset
import requests
from io import BytesIO

# 모델과 Processor 로드
model_name = "llava-hf/llava-1.5-7b-hf"
model = LlavaForConditionalGeneration.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype=torch.float16,
    load_in_8bit=True,
)
model = prepare_model_for_kbit_training(model)

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

processor = LlavaProcessor.from_pretrained(model_name)

# GBC10M Dataset 불러오기
ds = load_dataset("graph-based-captions/GBC10M", split="train[:500]")

# 커스텀 데이터셋 클래스 정의
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, ds, processor):
        self.ds = ds
        self.processor = processor

    def __len__(self):
        return len(self.ds)

    def __getitem__(self, idx):
        example = self.ds[idx]
        img_url = example['img_url']
        caption = example['detail_caption']

        # 이미지 로드
        try:
            image = Image.open(requests.get(img_url, stream=True, timeout=5).raw).convert("RGB")
        except Exception as e:
            print(f"Image load failed: {e}")
            image = Image.new("RGB", (336,336), (255,255,255))  # fallback

        prompt = "<image>\n" + caption
        processed = self.processor(
            text=prompt,
            images=image,
            return_tensors="pt",
            padding="max_length",
            max_length=512,
        )

        input_ids = processed["input_ids"].squeeze(0)
        attention_mask = processed["attention_mask"].squeeze(0)
        pixel_values = processed["pixel_values"].squeeze(0)

        labels = input_ids.clone()
        labels[labels == self.processor.tokenizer.pad_token_id] = -100

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "pixel_values": pixel_values,
            "labels": labels,
        }


# Collator 정의
class CustomDataCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, batch):
        input_ids = [item["input_ids"] for item in batch]
        attention_mask = [item["attention_mask"] for item in batch]
        labels = [item["labels"] for item in batch]
        pixel_values = [item["pixel_values"] for item in batch]

        input_ids_padded = pad_sequence(input_ids, batch_first=True, padding_value=self.tokenizer.pad_token_id)
        attention_mask_padded = pad_sequence(attention_mask, batch_first=True, padding_value=0)
        labels_padded = pad_sequence(labels, batch_first=True, padding_value=-100)
        pixel_values_tensor = torch.stack(pixel_values)

        return {
            "input_ids": input_ids_padded,
            "attention_mask": attention_mask_padded,
            "labels": labels_padded,
            "pixel_values": pixel_values_tensor,
        }

# Dataset 인스턴스화
dataset = CustomDataset(ds, processor)

# 훈련 설정
training_args = TrainingArguments(
    output_dir="./llava-lora-finetuned",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-5,
    save_total_limit=2,
    fp16=True,
    logging_dir="./logs",
    logging_steps=10,
    save_steps=500,
)

# Trainer 정의 및 훈련
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    data_collator=CustomDataCollator(processor.tokenizer),
)

trainer.train()

# 모델 저장 
model.save_pretrained("./llava-lora-finetuned/adapter")
processor.save_pretrained("./llava-lora-finetuned/adapter")
