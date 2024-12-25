import os

for i in range(1, 40+1):
    file = f"Вопрос {i}.md"
    if os.path.exists(os.path.join(os.getcwd(), file)): continue
    with open(file, "w", encoding="UTF-8") as f:
                      f.write("")
