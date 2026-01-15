# core_search_engine.py
# Установите зависимости: pip install sentence-transformers torch numpy scikit-learn

import numpy as np
from sentence_transformers import SentenceTransformer, util
import torch
from typing import List, Dict, Tuple
import time


class SettingsSearchEngine:
    def __init__(self, model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Инициализация поискового движка.

        Выбор модели:
        - 'paraphrase-multilingual-MiniLM-L12-v2': Лучший баланс для русского (рекомендуется)
        - 'sentence-transformers/all-MiniLM-L6-v2': Быстрее и компактнее, немного хуже с русским
        - 'intfloat/multilingual-e5-base': Мощнее, но больше размер
        """
        print(f"🔄 Загрузка модели {model_name}...")
        start_time = time.time()

        self.model = SentenceTransformer(model_name)
        self.settings_data = []  # Оригинальные данные настроек
        self.settings_texts = []  # Тексты для поиска
        self.embeddings = None  # Векторные представления

        load_time = time.time() - start_time
        print(f"✅ Модель загружена за {load_time:.2f} сек")
        print(f"📐 Размерность векторов: {self.model.get_sentence_embedding_dimension()}")

    def index_settings(self, settings: List[Dict]):
        """
        Индексация списка настроек для быстрого поиска.

        Каждая настройка должна быть словарём с ключами:
        - 'name': Название настройки (обязательно)
        - 'description': Описание (обязательно)
        - 'category': Категория
        - 'path': Путь в меню
        - 'keywords': Список ключевых слов
        """
        print(f"📊 Индексация {len(settings)} настроек...")
        self.settings_data = settings
        self.settings_texts = []

        # Создание поискового текста для каждой настройки
        for setting in settings:
            # Комбинируем все текстовые поля для лучшего поиска
            search_parts = [
                setting.get('name', ''),
                setting.get('description', ''),
                setting.get('category', ''),
                ' '.join(setting.get('keywords', []))
            ]
            search_text = ' '.join(filter(None, search_parts))
            self.settings_texts.append(search_text)

        # Векторизация всех настроек
        print("🧮 Создание векторных представлений...")
        index_start = time.time()

        self.embeddings = self.model.encode(
            self.settings_texts,
            convert_to_tensor=True,
            show_progress_bar=True,
            batch_size=32,
            normalize_embeddings=True
        )

        index_time = time.time() - index_start
        print(f"✅ Проиндексировано за {index_time:.2f} сек")
        print(f"💾 Память: ~{self.embeddings.nelement() * self.embeddings.element_size() / 1024 / 1024:.1f} MB")

    def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict]:
        """
        Поиск наиболее релевантных настроек.

        Аргументы:
            query: Поисковый запрос на русском/английском
            top_k: Сколько результатов вернуть
            threshold: Минимальный порог схожести (0.0-1.0)

        Возвращает:
            Список настроек с добавленными полями:
            - relevance_score: Оценка релевантности
            - match_type: Тип совпадения
        """
        if not self.settings_data:
            return []

        # Векторизация запроса
        query_embedding = self.model.encode(query, convert_to_tensor=True, normalize_embeddings=True)

        # Быстрый расчёт сходства на GPU (если доступно)
        cos_scores = util.pytorch_cos_sim(query_embedding, self.embeddings)[0]

        # Получение топ-K результатов
        if top_k < len(cos_scores):
            top_results = torch.topk(cos_scores, k=top_k)
            scores = top_results.values.tolist()
            indices = top_results.indices.tolist()
        else:
            scores = cos_scores.tolist()
            indices = list(range(len(scores)))

        # Формирование результатов
        results = []
        for score, idx in zip(scores, indices):
            if score < threshold:
                continue

            # Копируем исходную настройку
            result = self.settings_data[idx].copy()
            result['relevance_score'] = round(float(score), 4)
            result['match_type'] = self._determine_match_type(query, self.settings_texts[idx])

            # Расширенная информация для отладки
            if 'search_text' not in result:  # Только для отладки
                result['search_text'] = self.settings_texts[idx][:100] + '...'

            results.append(result)

        return results

    def _determine_match_type(self, query: str, setting_text: str) -> str:
        """Определяет тип совпадения для информации"""
        query_lower = query.lower()
        text_lower = setting_text.lower()

        # Проверка точного вхождения
        if query_lower in text_lower:
            return "точное_совпадение"

        # Проверка вхождения отдельных слов
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        if query_words.intersection(text_words):
            return "частичное_совпадение"

        return "семантическое_совпадение"

    def benchmark(self, test_queries: List[str] = None):
        """Тестирование производительности движка"""
        if test_queries is None:
            test_queries = [
                "яркость экрана",
                "как сделать тише",
                "язык интерфейса",
                "сохранение энергии",
                "уведомления и оповещения"
            ]

        print("\n⚡ ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("=" * 40)

        total_time = 0
        for query in test_queries:
            start_time = time.perf_counter()
            results = self.search(query, top_k=3)
            elapsed = (time.perf_counter() - start_time) * 1000  # мс
            total_time += elapsed

            print(f"\n🔍 '{query}': {elapsed:.1f} мс")
            if results:
                for i, r in enumerate(results[:2], 1):
                    print(f"   {i}. {r['name']} ({r['relevance_score']:.3f})")

        avg_time = total_time / len(test_queries)
        print(f"\n📊 Среднее время поиска: {avg_time:.1f} мс")
        print(f"📈 Настроек в индексе: {len(self.settings_data)}")


# ============================================================================
# ИНТЕРАКТИВНЫЙ ДЕМО-РЕЖИМ
# ============================================================================

def create_demo_settings() -> List[Dict]:
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
            'keywords': ['аудио', 'звучание', 'динамики', 'тишина', 'громко']
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
            'keywords': ['аккумулятор', 'заряд', 'автономность', 'экономия']
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
            'keywords': ['интернет', 'беспроводная сеть', 'подключение', 'роутер']
        },
        {
            'name': 'Резервное копирование',
            'description': 'Настройка автоматического сохранения важных данных',
            'category': 'Безопасность',
            'path': 'Безопасность/Бэкап',
            'keywords': ['бэкап', 'сохранение данных', 'восстановление', 'копия']
        }
    ]


def interactive_demo():
    """Интерактивная демонстрация работы поиска"""
    print("🚀 ЗАПУСК ДЕМОНСТРАЦИИ СЕМАНТИЧЕСКОГО ПОИСКА")
    print("=" * 60)

    # 1. Инициализация движка
    search_engine = SettingsSearchEngine()

    # 2. Загрузка демо-настроек
    settings = create_demo_settings()
    search_engine.index_settings(settings)

    # 3. Тест производительности
    search_engine.benchmark()

    print("\n" + "=" * 60)
    print("🎯 ИНТЕРАКТИВНЫЙ РЕЖИМ ПОИСКА")
    print("=" * 60)
    print("Введите запросы на русском языке (пустая строка для выхода)")
    print("Примеры: 'яркость', 'сохранение батареи', 'оповещения'")
    print("-" * 60)

    while True:
        try:
            query = input("\n🔍 Ваш запрос: ").strip()
            if not query:
                print("👋 Выход из демо-режима")
                break

            # Замер времени поиска
            start_time = time.perf_counter()
            results = search_engine.search(query, top_k=3, threshold=0.25)
            search_time = (time.perf_counter() - start_time) * 1000

            # Вывод результатов
            if results:
                print(f"✅ Найдено: {len(results)} результат(ов) за {search_time:.1f} мс")
                print("-" * 40)

                for i, result in enumerate(results, 1):
                    score_bar = "█" * int(result['relevance_score'] * 20)
                    print(f"{i}. {result['name']}")
                    print(f"   📁 {result['category']} → {result['path']}")
                    print(f"   🎯 Релевантность: {result['relevance_score']:.3f} [{score_bar:<20}]")
                    print(f"   📝 {result['description'][:70]}...")
                    if result['match_type'] != 'семантическое_совпадение':
                        print(f"   🔍 Тип: {result['match_type']}")
                    print()
            else:
                print(f"❌ По запросу '{query}' ничего не найдено")
                print("💡 Попробуйте другие формулировки или уменьшите порог поиска")

        except KeyboardInterrupt:
            print("\n\n⚠️ Демонстрация прервана")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    interactive_demo()