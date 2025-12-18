class Tag:
    def __init__(self, name, payload: dict = None, active_scheme='blue'):
        self.active_scheme = active_scheme
        self.name  = name
        self.group = None
        self.payload = payload or {}

    def __eq__(self, other):
        if other is None: return False
        return self.name == other.name and self.group == other.group

    def __repr__(self):
        return f'<Tag "{self.name}">'

class Tags:
    name: str = None
    # TODO: не реализовано
    hint: str = None

    class WHERE:
        name = "Место"
        NOV    = Tag("Новгород",   payload={'icon': 'home.svg'})
        LOMO   = Tag("Ломоносова", payload={'icon': 'lomo.svg'})
        CRON   = Tag("Кронва",     payload={'icon': 'cron.svg'})
        ONLINE = Tag("Онлайн",     payload={'icon': 'wifi.svg'})
        SPORT  = Tag("Спорт зал",  payload={'icon': 'sword.svg'})

    class LABOR:
        name = "Деятельность"
        LESSON = Tag("Пара")
        REST   = Tag("Отдых")
        SPORT  = Tag("Спорт", active_scheme='yellow')

    class IMPORTANT:
        name = "Важно"
        YES = Tag("Да",  active_scheme='green')
        NO  = Tag("Нет", active_scheme='red')

    class TRANSPARENT:
        name = "Прозрачное"
        YES = Tag("Да",  active_scheme='green')
        NO  = Tag("Нет", active_scheme='red')

    class REPLACER:
        name = "Заменяющее"
        YES = Tag("Да",  active_scheme='green')
        NO  = Tag("Нет", active_scheme='red')

    class TRACKING:
        name = "Отслеживание"
        YES = Tag("Да",  active_scheme='green')
        NO  = Tag("Нет", active_scheme='red')

    class HIDDEN:
        name = "Скрытое"
        YES = Tag("Да",  active_scheme='green')
        NO  = Tag("Нет", active_scheme='red')

    # TODO: не реализовано
    class BACKGROUND:
        name = "Задний план"
        hint = "Само событие станет невидимым на графике, но оно поменяет задний фон самой колонки"
        YES = Tag("Да",  active_scheme='red')
        NO  = Tag("Нет", active_scheme='red')

    class _UniversalTag:
        name: str

    @classmethod
    def dict_like(cls) -> dict[_UniversalTag, tuple[Tag]]:
        # noinspection PyTypeChecker
        return {i: tuple(j for j in i.__dict__.values() if isinstance(j, Tag))
                for k, i in cls.__dict__.items() if isinstance(i, type) and not k.startswith('_')}

for tag_group, tags in Tags.dict_like().items():
    for tag in tags:
        tag.group = tag_group


class TagList:
    def __init__(self, *tags):
        self._container = {tag.group.name: tag for tag in tags}

    def __contains__(self, item: Tag):
        return item in self._container.values()

    def __str__(self):
        return f'<TagList [{", ".join([f"{group_name} - {tags.name}" for group_name, tags in self._container.items()])}]>'

    def __bool__(self):
        return bool(self._container)

    def add(self, tag: Tag):
        assert isinstance(tag, Tag)
        self._container[tag.group.name] = tag

    def have(self, item: Tag):
        assert isinstance(item, Tag)
        return item in self._container.values()

    def get(self, group) -> Tag:
        return self._container.get(group.name)

    def have_to_go(self):
        """А нужно ли мне ИДТИ на это занятие?"""
        if Tags.IMPORTANT.YES in self: return True
        if Tags.IMPORTANT.NO in self: return False
        if Tags.TRANSPARENT.YES in self: return False

        if Tags.LABOR.LESSON in self: return True
        return False

    # noinspection PyUnresolvedReferences
    def to_json(self):
        data = {}
        for k, v in Tags.__dict__.items():
            if k.startswith('_'): continue
            if not (isinstance(v, type) and v.name in self._container): continue
            values = tuple(
                (name, value) for name, value in v.__dict__.items()
                if isinstance(value, Tag)
            )
            if len(values) == 0: raise KeyError(k)
            data[k] = next(pair[0] for pair in values if pair[1] == self._container[v.name])
        return data

    @classmethod
    def from_json(cls, data: dict):
        def get_value(value):
            if len(value) == 0:
                raise KeyError
            return value[0]

        return cls(*[
            get_value([value for name, value in k.__dict__.items() if isinstance(value, Tag) and name == data[k.__name__]])
            for k, v in Tags.dict_like().items()
            if not k.__name__.startswith('_') and k.__name__ in data
        ])

if __name__ == '__main__':
    a = TagList.from_json({'WHERE':'NOV','LABOR':'REST','IMPORTANT':'YES'})
    print(a.to_json())
    print(a)