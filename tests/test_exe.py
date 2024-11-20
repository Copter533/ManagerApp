#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os
import sys

cmd_name, args = sys.argv[0], tuple(sys.argv[1:])
args = ('1', '2222', '333333333333')

if len(args) < 2:
    print(f"Использование: {cmd_name} что_клеить1 что_клеить2 ... куда_клеить")
    exit()

content = ""
messages = {}

for file in args[:-1]:
    if not os.path.exists(file):
        messages[file] = "[❓] Файл не существует"
        continue
    try:
        with open(file, 'r') as f:
            content += f.read()
    except Exception as ex:
        messages[file] = f'[❌] {ex}'
    else:
        messages[file] = '[✅] Успешно!'

print("Файлы для склеиванья:")
max_len = max(map(len, messages))
for name, msg in messages.items():
    print(f' - {name}{" " * (max_len - len(name))} : {msg}')

print("\nРезультат")
try:
    with open(args[-1], 'w') as f:
        f.write(content)
except Exception as ex:
    print(f' - [❌] {ex}')
else:
    print( ' - [✅] Успешно!')
