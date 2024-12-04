from itertools import count
import os
import sys

import pygame
import tones
import tones.mixer

from .images import Images
from .script import Script
from .spiral import Spiral
from .types import Size

from typing import Iterator


os.environ['SDL_VIDEO_CENTERED'] = '1'


AUDIO_END = pygame.USEREVENT+1
pygame.mixer.music.set_endevent(AUDIO_END)
pygame.mixer.pre_init(buffer=4096)

BINAURAL_DEFAULTS = {
    'frequency': 10,  # very low pitch
    'wavelength': 8,  # both theta and alpha wave stimulating
    'volume': 0.75,
}

TICKER_DEFAULTS = {
    'action': 500,
    'image': 1000,
    'spiral': 1,
}


class Screen:
    background_color: str = "black"
    frames_per_second: int = 60
    fullscreen: bool = False
    text_color = (0, 51, 204)
    text_alpha: int = 254
    text_font: pygame.font.Font = None
    windowed_size: Size = Size(1024, 768)
    size: Size = windowed_size
    background_font: pygame.font.Font = None
    background_text: pygame.Surface = None
    enable_images: bool = False
    enable_spiral: bool = False
    running: bool = False
    text: str = ""

    __binaural_channel: pygame.mixer.Channel
    __images: dict[Size, Iterator[pygame.Surface]]
    __script: Script
    __spirals: dict[Size, Iterator[pygame.Surface]]
    __ticker: 'Ticker'

    def __init__(self, script: Script):
        self.__script = script
        self.__binaural_channel = None
        self.__images = {}
        self.__spirals = {}

        for key, value in (script.options.get('screen') or {}).items():
            if key == 'size':
                self.size = self.windowed_size = Size(*value)
            elif hasattr(self, key):
                setattr(self, key, value)

        for key, value in script.options.get('text', {}).items():
            if key == 'alpha':
                self.text_alpha = value
            elif key == 'color':
                self.text_color = pygame.color.Color(value)

        pygame.init()
        self.__init_screen()
        self.__init_fonts()
        self.__loading()
        self.__init_audio()
        self.__init_images()
        self.__init_spirals()
        self.__init_ticker()

    def enable_binaural(self, enabled=True):
        opts = self.__script.options.get('binaural', BINAURAL_DEFAULTS)
        already_enabled = (
            self.__binaural_channel is not None and
            self.__binaural_channel.get_busy()
        )
        if enabled and not already_enabled:
            self.__binaural_channel = self.__binaural.play(loops=-1)
            self.__binaural_channel.set_volume(opts['volume'])
            print(self.__binaural_channel)
        elif not enabled and self.__binaural_channel:
            self.__binaural_channel.stop()
            self.__binaural_channel = None

    def enable_music(self, enabled=True):
        opts = self.__script.options.get('music', {})
        if enabled and not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
            if 'volume' in opts:
                pygame.mixer.music.set_volume(opts['volume'])
        elif not enabled:
            pygame.mixer.music.stop()

    def run(self):
        self.running = True
        c = pygame.time.Clock()

        self.__actions = iter(self.__script)
        self.__current_action = self.__next_action()
        self.__current_spiral = self.__next_spiral()
        self.__current_image = self.__next_image()

        for _ in count():
            elapsed = c.tick(self.frames_per_second)
            self.__process_events()
            if not self.running:
                break
            self.__update(elapsed)
            self.__render()

    def set_background_text(self, text: str):
        lines = text.splitlines()
        width = 0
        height = 0
        for line in lines:
            w, h = self.background_font.size(line)
            width = max(width, w)
            height += h
        img = pygame.Surface((width, height))
        img.set_colorkey(self.background_color)
        height = 0
        for line in lines:
            word = self.background_font.render(
                line, True, color_rotate(self.text_color)
            )
            cx, cy = word.get_rect().center
            x_off = (width/2) - cx
            y_off = height
            height += 2 * cy
            img.blit(word, (int(x_off), int(y_off)))
        img.set_alpha(int(self.text_alpha / 2))
        self.background_text = img.convert()

    def silence(self, millis: int):
        self.__ticker.add_millis('action', millis)

    def __display_text(self, text, alpha=None, delay=False):
        surface = pygame.Surface(self.size)
        surface.set_colorkey(0)
        if alpha is None:
            alpha = self.text_alpha
        surface.set_alpha(alpha)
        text = self.text_font.render(text, True, self.text_color, None)
        text_rect = text.get_rect()
        text_rect.center = (self.size.x / 2, self.size.y / 2)
        surface.blit(text, text_rect)
        self.__draw_surface(surface, delay)

    def __draw_surface(self, surface, delay=False):
        cx, cy = surface.get_rect().center
        x_offset = int((self.size.x/2) - cx)
        y_offset = int((self.size.y/2) - cy)
        self.screen.blit(surface, (x_offset, y_offset))
        if not delay:
            pygame.display.flip()

    def __init_audio(self):
        binaural_opts = {
            **BINAURAL_DEFAULTS,
            **self.__script.options.get('binaural', {}),
        }
        frequency = binaural_opts['frequency']
        wavelength = binaural_opts['wavelength']
        mixer = tones.mixer.Mixer()
        mixer.create_track(0, tones.SINE_WAVE)
        mixer.add_tone(0, frequency=frequency, duration=10)
        mixer.create_track(1, tones.SINE_WAVE)
        mixer.add_tone(1, frequency=frequency+wavelength, duration=10)
        self.__binaural = pygame.mixer.Sound(buffer=mixer.sample_data())

        music_opts = self.__script.options.get('music', {})
        if 'path' in music_opts:
            path = self.__script.relative_path(music_opts['path'])
            pygame.mixer.music.load(path)

    def __init_images(self):
        for size in self.__sizes():
            self.__load_images(size)

    def __init_screen(self):
        if self.fullscreen:
            size = (0, 0)
            flags = pygame.NOFRAME
        else:
            size = self.size
            flags = pygame.RESIZABLE
        pygame.mouse.set_visible(not self.fullscreen)
        self.screen = pygame.display.set_mode(size, flags)
        self.size = Size(*self.screen.get_size())

    def __init_spirals(self):
        for size in self.__sizes():
            self.__load_spiral(size)

    def __init_fonts(self):
        fontsize = int(self.size.x/10)
        self.text_font = pygame.font.SysFont(None, fontsize)
        self.background_font = pygame.font.SysFont(None, 3 * fontsize)

    def __init_ticker(self):
        opts = {
            **TICKER_DEFAULTS,
            **self.__script.options.get('ticker', {}),
        }
        self.__ticker = Ticker(**opts)

    def __load_images(self, size: Size) -> None:
        if size not in self.__images:
            opts = self.__script.options.get('images', {})
            dir = self.__script.relative_path(opts.get('path', './images'))
            self.__images[size] = Images(dir=dir, size=size)

    def __load_spiral(self, size: Size) -> None:
        if size not in self.__spirals:
            kwargs = self.__script.options.get('spiral', {})
            self.__spirals[size] = Spiral(**kwargs, size=size)

    def __loading(self) -> None:
        self.screen.fill(self.background_color)
        self.__display_text(
            'Loading...' if not self.running else 'Reloading...',
            alpha=255,
        )

    def __next_action(self):
        return next(self.__actions)

    def __next_image(self):
        return next(self.__images[self.size])

    def __next_spiral(self):
        return next(self.__spirals[self.size])

    def __process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.__quit()
            if event.type == AUDIO_END:
                self.__quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    self.__toggle_fullscreen()
                elif event.key == pygame.K_q:
                    self.__quit()
            elif event.type == pygame.WINDOWSIZECHANGED:
                self.size = Size(event.x, event.y)
                if not self.fullscreen:
                    self.windowed_size = self.size
                self.screen.fill(self.background_color)
                pygame.display.flip()
                self.__resize()
                self.__ticker.force_ready('image')
                self.__ticker.force_ready('spiral')

    def __quit(self):
        if not self.running:
            pygame.display.quit()
            pygame.quit()
            sys.exit()
        self.running = False

    def __render(self) -> None:
        self.screen.fill(self.background_color)
        if self.enable_images:
            self.__draw_surface(self.__current_image, delay=True)
        if self.background_text:
            self.__draw_surface(self.background_text, delay=True)
        if self.enable_spiral:
            self.__draw_surface(self.__current_spiral, delay=True)
        if self.text:
            self.__display_text(self.text, delay=True)
        pygame.display.flip()

    def __resize(self):
        self.__loading()
        self.__init_fonts()
        self.__load_images(self.size)
        self.__load_spiral(self.size)

    def __sizes(self):
        return (
            self.size,
            self.windowed_size,
            *(Size(*size) for size in pygame.display.get_desktop_sizes()),
        )

    def __toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if not self.fullscreen:
            self.size = self.windowed_size
        self.__init_screen()
        self.__resize()

    def __update(self, millis: int) -> None:
        self.__ticker.update(millis)

        if self.__ticker.is_ready('action'):
            if self.__current_action:
                self.__current_action(screen=self)
            try:
                self.__current_action = self.__next_action()
            except StopIteration:
                self.__current_action = None

        if self.__ticker.is_ready('spiral'):
            self.__current_spiral = self.__next_spiral()

        if self.enable_images and self.__ticker.is_ready('image'):
            self.__current_image = self.__next_image()


class Ticker:
    __frequencies: dict[str, int]
    __counters: dict[str, int]

    def __init__(self, **frequencies: dict[str, int]):
        self.__frequencies = frequencies
        self.__counters = frequencies.copy()

    def update(self, millis: int):
        for k in self.__counters:
            if self.is_ready(k):
                self.__counters[k] = self.__frequencies[k]
            self.__counters[k] -= millis

    def is_ready(self, key: str) -> bool:
        return self.__counters[key] <= 0

    def force_ready(self, key: str):
        self.__counters[key] = 1

    def add_millis(self, key: str, millis: int):
        self.__counters[key] += millis


def color_rotate(color):
    c = pygame.color.Color(color)
    return pygame.color.Color(c.b, c.r, c.g)
