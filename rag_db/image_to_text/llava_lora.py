import fitz
from PIL import Image
import io
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration
from peft import PeftModel
import os

# === 1. 경로 설정 ===
pdf_path = '/home/gpuadmin/chw/ns-3-manual.pdf'
output_dir = './llava_1.5/output_images3'
adapter_path = './llava_1.5/llava-lora-finetuned3/adapter'  # 파인튜닝된 LoRA adapter 경로
base_model_id = 'llava-hf/llava-1.5-7b-hf'

os.makedirs(output_dir, exist_ok=True)

# === 2. PDF에서 이미지 추출 ===
print("PDF에서 이미지 추출 중...")
doc = fitz.open(pdf_path)
images = []

for page_index in range(len(doc)):
    page = doc[page_index]
    image_list = page.get_images(full=True)
    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")  # 일부 이미지가 RGBA일 수 있으므로 RGB로 변환
        images.append(image)

print(f"총 {len(images)}개의 이미지를 추출했습니다.")

# === 3. 모델 불러오기 (Base + LoRA) ===
print("모델 불러오는 중...")
base_model = LlavaForConditionalGeneration.from_pretrained(
    base_model_id,
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    device_map="auto"  # GPU 자동 분배
)
model = PeftModel.from_pretrained(base_model, adapter_path)
processor = AutoProcessor.from_pretrained(base_model_id)

# === 4. 이미지 처리 및 설명 추출 ===
BATCH_SIZE = 5
for i in range(0, len(images), BATCH_SIZE):
    batch_images = images[i:i+BATCH_SIZE]
    batch_prompts = []
    batch_conversations = []

    for batch_idx, image_in_batch in enumerate(batch_images):
        global_idx = i + batch_idx
        print(f"배치 내 이미지 처리 중: {global_idx+1} / {len(images)}")

        # LLaVA 스타일 대화 형식
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please describe this image in as much detail as possible. The source of this image is NS3 documentation."},
                    {"type": "image"}
                ]
            }
        ]
        batch_conversations.append(conversation)
        prompt_text_only = processor.apply_chat_template(conversation, add_generation_prompt=True)
        batch_prompts.append(prompt_text_only)

    # 입력 준비
    inputs = processor(text=batch_prompts, images=batch_images, return_tensors="pt", padding=True).to(0, torch.float16)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=False
        )

    # 응답 디코딩
    responses = processor.batch_decode(outputs, skip_special_tokens=True)

    # 결과 저장
    for batch_idx, image_in_batch in enumerate(batch_images):
        global_idx = i + batch_idx
        response_text = responses[batch_idx]
        
        img_filename_base = f"img_{global_idx+1:03d}"
        img_path = os.path.join(output_dir, f"{img_filename_base}.png")
        txt_path = os.path.join(output_dir, f"{img_filename_base}.txt")
        
        image_in_batch.save(img_path)

        # "ASSISTANT:" 이후의 텍스트만 저장
        assistant_marker = "ASSISTANT:"
        final_text_to_save = response_text.split(assistant_marker, 1)[-1].strip()

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(final_text_to_save)

    # 메모리 정리
    del inputs, outputs, batch_images, batch_prompts, batch_conversations, responses
    torch.cuda.empty_cache()
