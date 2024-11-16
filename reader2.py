import time
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Замер времени для загрузки модели и токенизатора
start_time = time.time()

# Название модели
model_name = "meta-llama/Llama-2-7b-hf"

print("Loading model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=True)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto", use_auth_token=False)

load_time = time.time() - start_time
print(f"Model and tokenizer loaded in {load_time:.2f} seconds.")

# Пример текста для обработки
text = """
Контрольная работа #1 будет проходить на этой неделе со среды (6 ноября) по субботу (9 ноября).
Каждый день контрольная работа будет открываться с 18:00 до 21:00 на платформе GeoLin.
"""

# Замер времени для генерации вывода
start_generation_time = time.time()

# Токенизация и генерация
inputs = tokenizer("Extract key points from the following message: " + text, return_tensors="pt").to("cuda")
outputs = model.generate(inputs.input_ids, max_length=200, num_return_sequences=1, do_sample=True, top_k=50)

# Декодирование результата
result = tokenizer.decode(outputs[0], skip_special_tokens=True)

generation_time = time.time() - start_generation_time
print(f"Output generated in {generation_time:.2f} seconds.")

print("Result:")
print(result)
