import os
import random

import pygame

from typing import Iterator
from .types import Size


class Images:
    dir: str
    size: Size

    alpha: int = 200

    __iter: Iterator[pygame.Surface] = None

    def __init__(self, size: Size, dir: str, **kwargs):
        self.size = size
        self.dir = os.path.abspath(dir)
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.__filenames = os.listdir(self.dir)

    def __iter__(self) -> Iterator[pygame.Surface]:
        return self

    def __next__(self) -> pygame.Surface:
        if self.__iter is None:
            filenames = random.sample(self.__filenames, len(self.__filenames))
            self.__iter = iter(filenames)
        try:
            filename = next(self.__iter)
            return self.__load_image(filename)
        except StopIteration:
            self.__iter = None
            return next(self)

    def __load_image(self, filename) -> pygame.Surface:
        path = os.path.join(self.dir, filename)
        image = pygame.image.load(path).convert()
        image = self.__scale_image(image)
        image.set_alpha(self.alpha)
        return image

    def __scale_image(self, image: pygame.Surface) -> pygame.Surface:
        width, height = (self.size.x * 1.1, self.size.y * 1.1)
        pic_width, pic_height = image.get_size()
        scale = max(width / pic_width, height / pic_height)
        return pygame.transform.rotozoom(image, 0, scale).convert()
