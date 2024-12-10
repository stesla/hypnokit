from abc import ABCMeta, abstractmethod
import itertools
import os
import yaml

from typing import (
    Any,
    Iterator,
    TYPE_CHECKING,
)
if TYPE_CHECKING:
    from .screen import Screen


class Script:
    __iter: Iterator = None

    actions: list[Any]
    options: dict[str, Any]

    @classmethod
    def load(cls, filename):
        with open(filename, 'r') as f:
            data = yaml.load(f, Loader=yaml.Loader)
        return cls(filename, data)

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data
        self.actions = iter(data.get('actions', []))
        self.options = data.get('options', {})
        self.subroutines = data.get('subroutines', {})

    def __iter__(self):
        return self

    def __next__(self):
        if self.__iter:
            try:
                return next(self.__iter)
            except StopIteration:
                self.__iter = None
                pass

        action = next(self.actions)
        name, arg = next(iter(action.items()))
        fn = getattr(self, name)
        self.__iter = iter(fn(*arg) if isinstance(arg, list) else fn(arg))
        return next(self.__iter)

    def background_text(self, text: str):
        yield BackgroundTextAction(text)

    def binaural(self, enabled: bool):
        yield EnableBinauralAction(enabled)

    def call(self, name):
        actions = self.subroutines[name]
        for action in self.__with_actions(actions):
            yield action

    def group(self, *actions):
        script = self.__with_actions(actions)
        yield GroupAction(script)

    def music(self, enabled: bool):
        yield EnableMusicAction(enabled)

    def relative_path(self, path: str):
        dir = os.path.dirname(self.filename)
        return os.path.normpath(os.path.join(dir, path))

    def rest(self, milliseconds):
        yield RestAction(milliseconds)

    def images(self, enabled: bool):
        yield EnableImagesAction(enabled)

    def repeat(self, opts):
        actions = opts.get('actions', [])
        if 'times' in opts:
            iter = itertools.chain(*(
                self.__with_actions(actions)
                for _ in range(opts['times'])
            ))
        else:
            iter = itertools.cycle(self.__with_actions(actions))
        for action in iter:
            yield action

    def __with_actions(self, actions):
        return Script(
            filename=self.filename,
            data={**self.data, 'actions': actions},
        )

    def speak(self, text: str):
        yield SpeakAction(text)

    def spiral(self, enabled: bool):
        yield EnableSpiralAction(enabled)

    def word(self, word: str, repeat: int = 1):
        for _ in range(repeat):
            yield WordAction(word)
        yield WordAction("")

    def words(self, words: str):
        for word in words.split():
            yield WordAction(word)
        yield WordAction("")


class BackgroundTextAction:
    text: str

    def __init__(self, text: str):
        self.text = text if text is not None else ""

    def __call__(self, screen: 'Screen'):
        screen.set_background_text(self.text)


class EnableAction(metaclass=ABCMeta):
    enabled: bool

    def __init__(self, enabled: bool):
        self.enabled = enabled

    @abstractmethod
    def __call__(self, screen: 'Screen'): ...


class EnableBinauralAction(EnableAction):
    def __call__(self, screen: 'Screen'):
        screen.enable_binaural(self.enabled)


class EnableImagesAction(EnableAction):
    def __call__(self, screen: 'Screen'):
        screen.enable_images = self.enabled


class EnableMusicAction(EnableAction):
    def __call__(self, screen):
        screen.enable_music(self.enabled)


class EnableSpiralAction(EnableAction):
    def __call__(self, screen: 'Screen'):
        screen.enable_spiral = self.enabled


class GroupAction:
    script: Script

    def __init__(self, script):
        self.script = script

    def __call__(self, screen: 'Screen'):
        for action in self.script:
            action(screen)


class RestAction:
    millis: int

    def __init__(self, millis: int):
        self.millis = millis

    def __call__(self, screen: 'Screen'):
        screen.rest(self.millis)


class SpeakAction:
    text: str

    def __init__(self, text: str):
        self.text = text

    def __call__(self, screen: 'Screen'):
        screen.speak(self.text)


class WordAction:
    word: str

    def __init__(self, word: str):
        self.word = word if word is not None else ""

    def __call__(self, screen: 'Screen'):
        screen.text = self.word
