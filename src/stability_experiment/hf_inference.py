import os
import csv
import torch
import gc
from PIL import Image
from tqdm import tqdm
from transformers import AutoProcessor, AutoModelForCausalLM, AutoTokenizer
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
from transformers import BitsAndBytesConfig

# Configuration
LAB_NAME = 'OpenGVLab'
MODELS = ['InternVL3-1B', 'InternVL3-2B', 'InternVL3-8B']
IMAGES_DIR = "data/raw2"
GROUND_TRUTH_CSV = "data/ground_truth/raw2/raw2_manual_ocr_ground_truth.csv"
OUTPUT_DIR = "data/results/stability_experiment/hf_outputs"
N_ROUNDS = 100

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio

def dynamic_preprocess(image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height
    target_ratios = set(
        (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])
    target_aspect_ratio = find_closest_aspect_ratio(
        aspect_ratio, target_ratios, orig_width, orig_height, image_size)
    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]
    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        split_img = resized_img.crop(box)
        processed_images.append(split_img)
    assert len(processed_images) == blocks
    if use_thumbnail and len(processed_images) != 1:
        thumbnail_img = image.resize((image_size, image_size))
        processed_images.append(thumbnail_img)
    return processed_images

def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform

def load_image(image_file, input_size=448, max_num=12):
    image = Image.open(image_file).convert('RGB')
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(image) for image in images]
    pixel_values = torch.stack(pixel_values)
    return pixel_values.to(torch.bfloat16).cuda()

def extrair_ocr(image_path, model, tokenizer):
    pixel_values = load_image(image_path, max_num=12)
    num_patches_list = [pixel_values.size(0)]
    question = "<image>\n    You are a specialized OCR engine. Your task is to transcribe the text from the image exactly as it appears.\n    Rules:\n    1. Output ONLY the text found in the image.\n    2. Do not interpret, summarize, or translate the text.\n    3. Do not add any introductory or concluding sentences (like \"Here is the text\").\n    4. Preserve the original line breaks."
    generation_config = dict(max_new_tokens=4096, do_sample=True)
    response, _ = model.chat(tokenizer, pixel_values, question, generation_config,
                             num_patches_list=num_patches_list, history=None, return_history=True)
    return response

def load_model_by_name(model_name):
    model_path = f"{LAB_NAME}/{model_name}"
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        quantization_config=quantization_config
    ).eval()
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=False)
    return model, tokenizer

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load ground truth list
    ground_truth_images = []
    if os.path.exists(GROUND_TRUTH_CSV):
        with open(GROUND_TRUTH_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ground_truth_images = [row['filename'] for row in reader]
    
    if not ground_truth_images:
        print("No ground truth found. Ensure extract_ground_truth.py was run.")
        return

    for model_name in MODELS:
        print(f"\n{'='*50}\nStarting HF Model: {model_name}\n{'='*50}")
        model_output_dir = os.path.join(OUTPUT_DIR, model_name)
        os.makedirs(model_output_dir, exist_ok=True)
        
        try:
            model = None
            tokenizer = None
            model, tokenizer = load_model_by_name(model_name)
            
            for img in ground_truth_images:
                img_path = os.path.join(IMAGES_DIR, img)
                if not os.path.exists(img_path):
                    continue
                
                print(f"Processing {img} (100 rounds)...")
                for i in tqdm(range(N_ROUNDS), desc=f"{img} ({model_name})"):
                    base_name = os.path.splitext(img)[0]
                    filename = os.path.join(model_output_dir, f"{base_name}_round_{i+1}.txt")
                    
                    # Skip if already processed
                    if os.path.exists(filename):
                        continue
                        
                    pred = extrair_ocr(img_path, model, tokenizer)
                    
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(pred)
            
        except Exception as e:
            print(f"Error processing {model_name}: {e}")
        finally:
            if model is not None:
                del model
            if tokenizer is not None:
                del tokenizer
            gc.collect()
            torch.cuda.empty_cache()
            
            # Delete model from Hugging Face cache to save disk space
            print(f"Cleaning up {model_name} from cache...")
            cache_dir = os.path.expanduser(f"~/.cache/huggingface/hub/models--{LAB_NAME}--{model_name}")
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir)
                print(f"Deleted cache: {cache_dir}")

if __name__ == "__main__":
    main()
