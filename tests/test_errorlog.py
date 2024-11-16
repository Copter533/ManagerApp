import os.path
import traceback
from datetime import datetime
import sys

try:
    # Ваш код, где может произойти ошибка
    1 / 0  # Ошибка для примера
except:

    if not os.path.exists("error_logs"): os.mkdir("error_logs")

    now = datetime.now()
    with open(f"error_logs/{now.date()}_{now.hour}{now.minute}{now.second}.txt", "w", encoding="utf-8") as f:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        __local_vars: dict = exc_traceback.tb_frame.f_locals

        f.write(f"TYPE    : {exc_type.__name__}\n")
        f.write(f"MESSAGE : {exc_value}\n")
        f.write("VALUES:\n")
        __variables: dict = __local_vars.copy()
        for __var_name, __value in __variables.items():
            if __var_name.startswith('__'): continue
            f.write(f" - {__var_name:>15} : {__value}\n")

        f.write("\n\n\n")
        traceback.print_tb(exc_traceback, file=f)

    print("END")
