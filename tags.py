class Tag:
    def __init__(self, name, active_scheme='blue'):
        self.active_scheme = active_scheme
        self.name  = name
        self.group = None

    def __eq__(self, other):
        return self.name == other.name and self.group == other.group

    def __repr__(self):
        return f'<Tag "{self.name}">'

class Tags:
    name: str = None

    class WHERE:
        name = "Место"
        NOV   = Tag("Новгород")
        LOMO  = Tag("Ломоносова")
        CRON  = Tag("Кронва")
        SPORT = Tag("Спорт зал")

    class LABOR:
        name = "Деятельность"
        LESSON = Tag("Пара")
        REST   = Tag("Отдых")
        SPORT  = Tag("Спорт", 'yellow')

    class IMPORTANT:
        name = "Важно"
        NO  = Tag("Нет", 'red')
        YES = Tag("Да",  'green')

    @classmethod
    def dict_like(cls) -> dict[WHERE, tuple[Tag]]:
        # noinspection PyTypeChecker
        return {i: tuple(j for j in i.__dict__.values() if isinstance(j, Tag))
                for i in cls.__dict__.values() if isinstance(i, type)}

for tag_group, tags in Tags.dict_like().items():
    for tag in tags: tag.group = tag_group


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
        self._container[tag.group.name] = tag

    def have(self, item: Tag):
        return item in self._container.values()

    def get(self, group: type[Tags.WHERE | Tags.IMPORTANT]):
        if group.name in self._container: return self._container[group.name]
        for tag in group.__dict__.values():
            if isinstance(tag, Tag):
                return tag
        return None

    # noinspection PyUnresolvedReferences
    def to_json(self):
        data = {}
        for k, v in Tags.__dict__.items():
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
            if k.__name__ in data
        ])

if __name__ == '__main__':
    a = TagList.from_json({'WHERE':'NOV','LABOR':'REST','IMPORTANT':'YES'})
    print(a.to_json())
    print(a)