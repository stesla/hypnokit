import math
import threading

import pygame

from typing import Iterable, Iterator
from .types import Size


class Spiral:
    size: Size

    alpha: int = 127
    color: str = "white"
    range: int = 90
    scale: int = 3
    step: int = 1

    __frames: Iterable[pygame.Surface] = None
    __iter: Iterator[pygame.Surface] = None
    __thread: threading.Thread = None

    def __init__(self, size: Size, **kwargs):
        self.size = size
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.__thread = threading.Thread(
            target=self.__init_frames,
            daemon=True,
        )
        self.__thread.start()

    def __init_frames(self):
        spiral = self.__init_spiral()
        frames = []
        for t in range(0, int(self.range/self.step)):
            frame = pygame.transform.rotate(spiral, -t * self.step)
            frame.set_alpha(self.alpha)
            frame.set_colorkey(0)
            frames.append(frame)
        self.__frames = frames

    def __init_spiral(self) -> pygame.Surface:
        size = int(1.2 * max(*self.size))
        offset = size/2.0
        spiral = pygame.Surface((size, size)).convert()
        dots = []
        for t in range(1, size * self.scale):
            t *= 0.5 / self.scale
            x = t * t * math.cos(t)
            y = t * t * math.sin(t)
            dots.append((int(x + offset), int(y + offset)))
        pygame.draw.lines(spiral, self.color, False, dots, 4)
        spiral.set_colorkey(0)
        a = pygame.transform.rotate(spiral, 90)
        b = pygame.transform.rotate(spiral, 180)
        c = pygame.transform.rotate(spiral, 270)
        spiral.blits(((a, (0, 0)), (b, (0, 0)), (c, (0, 0))))
        spiral.set_colorkey(None)
        return spiral

    def __iter__(self) -> Iterator[pygame.Surface]:
        return self

    def __next__(self) -> pygame.Surface:
        if self.__iter is None:
            self.__thread.join()
            self.__iter = iter(self.__frames)
        try:
            return next(self.__iter)
        except StopIteration:
            self.__iter = None
            return next(self)
