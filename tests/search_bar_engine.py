def levenstein(str_1, str_2):
    # Скопировано с https://habr.com/ru/articles/676858/
    # Чё это за фигня
    n, m = len(str_1), len(str_2)
    if n > m:
        str_1, str_2 = str_2, str_1
        n, m = m, n
    current_row = range(n + 1)
    for i in range(1, m + 1):
        previous_row, current_row = current_row, [i] + [0] * n
        for j in range(1, n + 1):
            add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
            if str_1[j - 1] != str_2[i - 1]:
                change += 1
            current_row[j] = min(add, delete, change)
    return current_row[n]


# ==========================================
def is_key_close(char1, char2):
    # Зона обнаружения:
    # +
    # +++
    # +
    x1, y1 = get_key_coords(char1)
    x2, y2 = get_key_coords(char2)
    if x1 is None or x2 is None: return False
    if y1 == y2 and abs(x1 - x2) <= 1:
        return True
    if abs(y1 - y2) <= 1 and x1 == x2:
        return True
    return False


def get_key_coords(char: str):
    target = char.lower()
    if ord("а") <= ord(target) <= ord("я"):
        keyboard_layout = [
            "йцукенгшщзхъ",
            "фывапролджэ",
            "ячсмитьбю"
        ]
    elif ord("a") <= ord(target) <= ord("z"):
        keyboard_layout = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm"
        ]
    else:
        return None, None
    for y, keyboard_line in enumerate(keyboard_layout):
        x = keyboard_line.find(target)
        if x != -1: return x, y
    return None, None


def keyboard_distance(str1, str2,
                      cost_insert=1.0,
                      cost_delete=1.0,
                      cost_replace=2,
                      cost_nearby=2,
                      cost_transpose=0.5):
    # Приводим к нижнему регистру для сравнения
    str1 = str1.lower()
    str2 = str2.lower()
    if len(str1) > len(str2):
        str1, str2 = str2, str1
    n, m = len(str1), len(str2)  # теперь str1 всегда ≤ str2 по длине
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] + cost_delete
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + cost_insert
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str2[i - 1] == str1[j - 1]:
                replace_cost = 0.0
            elif is_key_close(str2[i - 1], str1[j - 1]):
                replace_cost = cost_nearby
            else:
                replace_cost = cost_replace
            dp[i][j] = min(
                dp[i - 1][j] + cost_delete,
                dp[i][j - 1] + cost_insert,
                dp[i - 1][j - 1] + replace_cost
            )
            # Транспозиция
            if i > 1 and j > 1 and str2[i - 1] == str1[j - 2] and str2[i - 2] == str1[j - 1]:
                dp[i][j] = min(dp[i][j], dp[i - 2][j - 2] + cost_transpose)
    return dp[m][n]


def create_demo_settings():
    """Создание демонстрационных настроек для тестирования"""
    return [
        {
            'name': 'Яркость экрана',
            'description': 'Регулировка уровня яркости дисплея для комфортного использования',
            'category': 'Экран',
            'path': 'Экран/Яркость',
            'keywords': ['дисплей', 'подсветка', 'освещение', 'свет']
        },
        {
            'name': 'Громкость звука',
            'description': 'Настройка уровня громкости системы и приложений',
            'category': 'Звук',
            'path': 'Звук/Громкость',
            'keywords': ["звук", 'аудио', 'звучание', 'динамики', 'тишина', 'громко']
        },
        {
            'name': 'Язык интерфейса',
            'description': 'Выбор языка меню и системных сообщений',
            'category': 'Система',
            'path': 'Система/Язык',
            'keywords': ['локализация', 'перевод', 'мультиязычность', 'русский']
        },
        {
            'name': 'Энергосбережение',
            'description': 'Оптимизация расхода заряда батареи',
            'category': 'Система',
            'path': 'Система/Батарея',
            'keywords': ['аккумулятор', 'заряд', 'автономность', 'экономия', "питание"]
        },
        {
            'name': 'Темная тема',
            'description': 'Включение темного режима оформления интерфейса',
            'category': 'Внешний вид',
            'path': 'Внешний вид/Тема',
            'keywords': ['оформление', 'ночной режим', 'скин', 'внешний вид']
        },
        {
            'name': 'Уведомления',
            'description': 'Управление системными оповещениями и алертами',
            'category': 'Система',
            'path': 'Система/Оповещения',
            'keywords': ['оповещения', 'алерты', 'сообщения', 'звук уведомлений']
        },
        {
            'name': 'Автозапуск программ',
            'description': 'Управление программами, запускаемыми при старте системы',
            'category': 'Система',
            'path': 'Система/Автозагрузка',
            'keywords': ['запуск при старте', 'инициализация', 'автозагрузка', 'стартап']
        },
        {
            'name': 'Безопасность и приватность',
            'description': 'Настройки конфиденциальности и защиты данных',
            'category': 'Безопасность',
            'path': 'Безопасность/Приватность',
            'keywords': ['конфиденциальность', 'защита', 'данные', 'отслеживание']
        },
        {
            'name': 'Настройки сети Wi-Fi',
            'description': 'Управление беспроводными подключениями к интернету',
            'category': 'Сеть',
            'path': 'Сеть/Wi-Fi',
            'keywords': ['интернет', 'сеть', 'подключение', 'роутер']
        },
        {
            'name': 'Резервное копирование',
            'description': 'Настройка автоматического сохранения важных данных',
            'category': 'Безопасность',
            'path': 'Безопасность/Бэкап',
            'keywords': ['бэкап', 'сохранение данных', 'восстановление', 'копия']
        }
    ]


options = create_demo_settings()

while True:
    for i, option in enumerate(options, start=1):
        print(f"{i}. {option['name']}")
    print("\n")
    search_for = input("Ищем: ").strip()
    if not search_for:
        continue

    ranked_list = []
    for option in options:
        # Список всех кандидатов для сравнения
        candidates = ([('name', word) for word in option['name'].split(" ")] +
                      [('keyword', kw) for kw in option['keywords']])

        best_score = float('inf')
        best_match_text = None
        best_match_source = None  # 'name' или 'keyword'

        for source, text in candidates:
            score = keyboard_distance(search_for, text)
            if score < best_score:
                best_score = score
                best_match_text = text
                best_match_source = source

        ranked_list.append((best_score, option, best_match_text, best_match_source))

    print("\nЛучшие совпадения:")
    for score, option, matched_text, source in sorted(ranked_list, key=lambda x: x[0]):
        source_label = "название" if source == 'name' else "ключевое слово"
        print(f"{score:.1f} → {option['name']}  (ближайшее: \"{matched_text}\" из {source_label})")