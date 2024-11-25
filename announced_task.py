from PyQt6.QtWidgets import QSystemTrayIcon
import pyautogui as pgui


class AnnouncedTask:
    all_actions: dict

    def __init__(self, delay_minutes: int, actions):
        self.delay = delay_minutes
        self.actions: list[AnnouncedTask._ClickerAction] = actions

        self._index = 0
        self._finished = False

        self.params = {}

        self.on_finished = None

    @classmethod
    def from_json(cls, data: dict, params: dict = None):
        variables = {
            'time_left'
        }

        return cls(data["delay"], [
            cls.all_actions[action["_type"]](
                **cls.parse_args(data, action, params)
            )
        for action in data["actions"]])

    @staticmethod
    def parse_args(variables: dict, args: dict, params: dict = None):
        if params is None: params = {}

        res = {}
        for k, v in args.items():
            if k.startswith("_"): continue

            value = ActionParam.from_json()
            if isinstance(value, str):
                for var_name, var_val in variables.items():
                    value = value.replace(f'{{{var_name}}}', var_val)

            res[k] = value
        return res

    def run(self):
        if len(self.actions) <= 1: return self.execute_loop()

    def execute_loop(self):
        if self._finished: return
        if not (0 <= self._index < len(self.actions)):
            if self.on_finished: self.on_finished()
            return
        a = self.actions[self._index]
        self._index += 1

        a.run()
        return a

    def get_index(self): return self._index
    def is_finished(self): return self._finished

    def finish(self): self._finished = True

    def __eq__(self, other): return self.delay == other.delay
    def __lt__(self, other): return self.delay <  other.delay
    def __gt__(self, other): return self.delay >  other.delay

    def default_params(self):
        return {
            "time_left": 42,
            "delay": self.delay
        }

    def get_param(self, key: str):
        return self.default_params().get(key, self.params.get(key))

    def params_pairs(self):
        for k, v in self.default_params().items():
            yield k, v
        for k, v in self.params.items():
            yield k, v

    # Классы действий
    class _ClickerAction:
        title: str
        delay = 0

        def __init__(self, delay=None):
            if delay: self.delay = delay

        def get_title(self):
            return self.title

        def on_app_connect(self, app): pass
        def run(self): raise NotImplemented


    class SendNotification(_ClickerAction):
        title = "Отправка сообщения"

        def __init__(self, title, message, **kwargs):
            super().__init__(**kwargs)
            self.tray = None
            self.tit = title
            self.msg = message

        def on_app_connect(self, app):
            self.tray: QSystemTrayIcon = app.tray_icon

        def run(self):
            if self.tray:
                self.tray.showMessage(self.tit(), self.msg())
            else:
                print(f"Сообщение: {self.tit()}\n{self.msg()}\n=============")


    class PressHotKey(_ClickerAction):
        delay = .5

        def get_title(self):
            return " + ".join(self.hotkey)

        def __init__(self, hotkey, **kwargs):
            super().__init__(**kwargs)
            self.hotkey = hotkey

        def run(self):
            pgui.hotkey(*[
                i.lower() if len(i) == 1 and i.isalpha() else i
                for i in self.hotkey().split("+")], interval=.1)


AnnouncedTask.all_actions = {name: value
                             for name, value in AnnouncedTask.__dict__.items()
                             if not name.startswith("_") and isinstance(value, type)}


class ActionParam:
    def __init__(self, formula, frozen=False):
        self.formula = formula
        self._frozen = frozen
        self.task: AnnouncedTask = None

        self.do_parse = False

    def set_task(self, task):
        self.task = task

    @classmethod
    def frozen(cls, value): return cls(value, True)

    @classmethod
    def from_json(cls, v: [str | dict]):
        # "123"
        # {"parameter": "message"}
        # {"parameter": "title", "default": "Сообщение"}
        if isinstance(v, dict) and "parameter" in v:
            return cls(lambda x: x.params.get(v["parameter"], v.get("default")))
        o = cls.frozen(v)
        if isinstance(v, str) and "{" in v and "}" in v:
            o.do_parse = True
        return o

    def __call__(self):
        if self.do_parse:
            s = self.formula
            for k, v in self.task.params_pairs(): s = s.replace(f'{{{k}}}', str(v))
            return s
        return self.formula if self._frozen else self.formula(self.task)

t = AnnouncedTask(6, [])
a = ActionParam.from_json("Кончается через {delay} минут!")
a.set_task(t)
print(a())