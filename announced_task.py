import json
import subprocess

from PyQt6.QtWidgets import QSystemTrayIcon
import pyautogui as pgui


class AnnouncedTask:
    all_actions_dict: dict

    def __init__(self, file, display_name, delay_minutes: int, actions = None, params_scheme=None):
        self.file = file
        self.display_name = display_name
        self.delay = delay_minutes
        self.do_expire = False
        self._actions: list[AnnouncedTask._ClickerAction] = actions or []

        self.app = None

        self._index = 0
        self._finished = False

        self.params = {}
        self.params_scheme = params_scheme or {}

        self.on_finished = None

    def add_action(self, action):
        if self.app: action.on_app_connect(self.app)
        self._actions.append(action)

    @classmethod
    def from_json(cls, file, data: dict, inputs: dict = None):
        o = cls(file, data.get("name", file), 0, [], data.get("params"))

        for action in data["actions"]:
            o.add_action(cls.all_actions_dict[action["_type"]](
                **o.parse_args(action)
            ))

        for k in data.get("params", ()):
            o.params[k] = (inputs or {}).get(k)

        return o

    def to_json(self):
        obj = {
            'name': self.display_name,
            'params': self.params_scheme,
            'actions': []
        }
        for action in self._actions:
            o = {"_type": action.__class__.__name__}
            for k, param in action.params().items():
                o[k] = param.to_json()
            obj['actions'].append(o)
        return obj

    @classmethod
    def from_file(cls, data: dict):
        file = data['file']
        with open(f"announced_tasks/{file}", "r", encoding="UTF-8") as f:
            o = cls.from_json(file, json.load(f), data.get('params', {}))
            o.delay     = data.get('delay',     0)
            o.do_expire = data.get('do_expire', False)
            return o

    def to_file(self):
        obj = {'file': self.file, 'params': self.params, 'delay': self.delay}

        if self.do_expire: obj['do_expire'] = True

        return obj

    def parse_args(self, args: dict):
        res = {}
        for k, v in args.items():
            if k.startswith("_"): continue
            value = ActionParam.from_json(v)
            value.set_task(self)
            res[k] = value
        return res

    def connect_app(self, app):
        self.app = app
        for action in self._actions:
            action.on_app_connect(app)

    def run(self):
        if len(self._actions) <= 1: return self.execute_loop()

        # Отдаём управление кликеру
        subprocess.run(['.venv\Scripts\python', 'autoclicker.py',
                        json.dumps(self.to_file(), separators=(",","=")).replace('"',"'")], shell=True)

    def execute_loop(self):
        if self._finished: return
        if not (0 <= self._index < len(self._actions)):
            if self.on_finished: self.on_finished()
            return
        a = self._actions[self._index]
        self._index += 1

        a.run()
        return a

    def get_index(self):   return self._index
    def is_finished(self): return self._finished

    def finish(self): self._finished = True

    def __eq__(self, other): return self.delay == other.delay
    def __lt__(self, other): return self.delay <  other.delay
    def __gt__(self, other): return self.delay >  other.delay

    def __str__(self):
        return self.display_name

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

        def run(self):            raise NotImplementedError
        def params(self) -> dict: raise NotImplementedError


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

        def params(self): return {'title': self.tit, 'message': self.msg}


    class SendAlarm(_ClickerAction):
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
                self.tray.showMessage(self.tit(), self.msg(), QSystemTrayIcon.MessageIcon.Critical, 999999)
            else:
                print(f"Предупреждение: {self.tit()}\n{self.msg()}\n=============")

        def params(self): return {'title': self.tit, 'message': self.msg}


    class PressHotKey(_ClickerAction):
        delay = .5

        def get_title(self):
            return self.hotkey()

        def __init__(self, hotkey, **kwargs):
            super().__init__(**kwargs)
            self.hotkey = hotkey

        def run(self):
            pgui.hotkey(*[
                i.lower() if len(i) == 1 and i.isalpha() else i
                for i in self.hotkey().split("+")], interval=.1)

        def params(self): return {'hotkey': self.hotkey}


    class TypeText(_ClickerAction):
        delay = .5

        def get_title(self):
            return "Печатаем текст..."

        def __init__(self, text, **kwargs):
            super().__init__(**kwargs)
            self.text = text

        def run(self):
            pgui.typewrite(self.text(), interval=.03)

        def params(self): return {'text': self.text}


    class WaitTime(_ClickerAction):
        delay = 1

        def get_title(self):
            return f"Ждать {self.delay} сек."

        def __init__(self, time, **kwargs):
            super().__init__(**kwargs)
            self.time  = time
            self.delay = time()

        def run(self):
            pass

        def params(self): return {'time': self.time}


AnnouncedTask.all_actions_dict = {name: value
                                  for name, value in AnnouncedTask.__dict__.items()
                                  if not name.startswith("_") and isinstance(value, type)}


class ActionParam:
    def __init__(self, formula, default=None, frozen=False, name=""):
        self.name    = name
        self.default = default
        self.formula = formula
        self._frozen = frozen
        self.task: AnnouncedTask = None

        self.do_parse = False

    def set_task(self, task):
        self.task = task

    @classmethod
    def from_json(cls, v: [str | dict]):
        # "123"
        # {"parameter": "message"}
        # {"parameter": "title", "default": "Сообщение"}
        if isinstance(v, dict) and "parameter" in v:
            return cls(lambda x: x.params.get(v["parameter"]), default=v.get("default"), name=v["parameter"])
        o = cls(v, frozen=True)
        if isinstance(v, str) and "{" in v and "}" in v:
            o.do_parse = True
        return o

    def to_json(self):
        if self._frozen: return self.formula
        obj = {"parameter": self.name}
        if self.default is not None: obj["default"] = self.default
        return obj

    def __repr__(self):
        return f'Action<{self()}>'

    def __call__(self):
        if self.task is None:
            return '???'
        if self.do_parse:
            s = self.formula
            for k, v in self.task.params_pairs(): s = s.replace(f'{{{k}}}', str(v))
            return s
        return self.formula if self._frozen else (self.formula(self.task) or self.default)


if __name__ == '__main__':
    t = AnnouncedTask.from_file({"file": "ifmo_connect.json"})
    t.run()