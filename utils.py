from time import time


def word_case(num, for1, for2, for5, pref=None):
    if pref is None: pref = f'{num} '
    if 10 <= num <= 20: return f'{pref}{for5}'
    rem = num % 10
    if rem == 1:    return f'{pref}{for1}'
    if 1 < rem < 5: return f'{pref}{for2}'
    return f'{pref}{for5}'


def tuple_range_to_str(v: tuple | list, replacer=None, sep=', '):
    """
    Возвращает строку с объединёнными соседними промежутками из кортежа\n
    Пример: (1,2,3,5) -> "1-3, 5"
    :param v: Кортеж чисел
    :param replacer: Эта функция будет применена к каждому числу при вставке его в результат
    :param sep: Разделитель в строке, по умолчанию запятая
    """
    if not v: return ""
    if replacer is None: replacer = lambda x: x
    if len(v) == 1: return str(replacer(v[0]))

    arr = sorted(v)
    res = [[arr[0]]]
    for i in range(1, len(v)):
        if arr[i] - arr[i-1] <= 1:
            if len(res[-1]) == 1:
                res[-1] = [res[-1][0], arr[i]]
            else:
                res[-1][1] = arr[i]
        else:
            res.append([arr[i]])

    return sep.join([str(replacer(a[0])) if len(a) == 1 else f'{replacer(a[0])}-{replacer(a[1])}' for a in res])


class DebugTimer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.st = time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f'Time for "{self.name}" - {time() - self.st:.2f}s')
