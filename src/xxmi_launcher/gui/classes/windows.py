import logging
import ctypes

from typing import Union, Tuple, List, Dict, Optional
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from ctypes import wintypes, windll, pointer

from customtkinter import CTk, CTkToplevel
from customtkinter import set_widget_scaling, set_window_scaling, ScalingTracker

from gui.classes.tooltip import UIToolTipEngine
from gui.classes.element import UIElement

import win32gui

log = logging.getLogger(__name__)


@dataclass
class ThemeMode(Enum):
    System = 'System'
    Light = 'Light'
    Dark = 'Dark'


@dataclass
class UIWindowConfig:
    title: str = 'UIWindow'
    icon_path: Optional[Path] = None
    theme_mode: ThemeMode = field(default_factory=lambda: ThemeMode.System)
    width: int = 800
    height: int = 600
    locked_width: bool = True
    locked_height: bool = True
    no_titlebar: bool = False


def limit_scaling(fit_width, fit_height):
    DPI100pc = 96  # DPI 96 is 100% scaling
    DPI_type = 0  # MDT_EFFECTIVE_DPI = 0, MDT_ANGULAR_DPI = 1, MDT_RAW_DPI = 2
    monitor_handle = windll.user32.MonitorFromPoint(wintypes.POINT(0, 0), 0)
    x_dpi, y_dpi = wintypes.UINT(), wintypes.UINT()
    windll.shcore.GetDpiForMonitor(monitor_handle, DPI_type, pointer(x_dpi), pointer(y_dpi))
    scaling_factor = (x_dpi.value + y_dpi.value) / (2 * DPI100pc)

    scaling_factor *= ScalingTracker.window_scaling

    scaled_width = fit_width * scaling_factor
    scaled_height = fit_height * scaling_factor

    max_width = ctypes.windll.user32.GetSystemMetrics(0)
    max_height = ctypes.windll.user32.GetSystemMetrics(1) * 0.8

    width_factor = 1
    if scaled_width > max_width:
        width_factor = round(max_width / scaled_width, 1)

    height_factor = 1
    if scaled_height > max_height:
        height_factor = round(max_height / scaled_height, 1)

    limit_factor = width_factor if width_factor < height_factor else height_factor

    if limit_factor != 1:
        set_widget_scaling(scaling_factor * limit_factor)
        set_window_scaling(scaling_factor * limit_factor)


class UIWindow(UIElement):
    def __init__(self, cfg: UIWindowConfig, **kwargs):
        super().__init__(**kwargs)
        self.exists = True
        self.cfg = cfg
        self.top_levels: List[Union['UIWindow', 'UIToplevel']] = [self]
        self.tooltip_engine: UIToolTipEngine

    def add_top_level(self, top_level: 'UIToplevel'):
        self.top_levels.append(top_level)

    def remove_top_level(self, top_level: 'UIToplevel'):
        for window_id in reversed(range(len(self.top_levels))):
            window = self.top_levels[window_id]
            if window == top_level:
                del self.top_levels[window_id]
                break

    def get_top_level(self, locking=False):
        if locking:
            for window_id in reversed(range(len(self.top_levels))):
                window = self.top_levels[window_id]
                if hasattr(window, 'lock_master') and window.lock_master:
                    return window
        return self.top_levels[-1]

    def move(self, x_offset: int = 0, y_offset: int = 0):
        x = self.winfo_pointerx() - x_offset
        y = self.winfo_pointery() - y_offset
        self.geometry('+{x}+{y}'.format(x=x, y=y))

    def close(self):
        self.unsubscribe()
        self.untrace_write()
        self.untrace_save()
        self.exists = False
        self._close()

    def _close(self):
        raise NotImplementedError


class UIMainWindow(UIWindow, CTk):
    def __init__(self):
        UIWindow.__init__(self, cfg=UIWindowConfig())
        CTk.__init__(self)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.overrideredirect(True)
        self.minimized = False
        self.bind("<Map>", self.on_deiconify_main_window)
        self.tooltip_engine = UIToolTipEngine()
        # self.bind("<Unmap>", self.on_iconify_main_window)
        # self.bind('<FocusIn>', self.on_focus_main_window)
        # self.bind('<FocusOut>', self.on_unfocus_main_window)

    def apply_config(self):
        self.title(self.cfg.title)
        if self.cfg.icon_path is not None:
            self.iconbitmap(self.cfg.icon_path, self.cfg.icon_path)
        self.resizable(not self.cfg.locked_width, not self.cfg.locked_height)
        self.geometry(f'{self.cfg.width}x{self.cfg.height}')
        # Configure window to have taskbar icon via Windows API
        GWL_EXSTYLE = -20
        hwnd = windll.user32.GetParent(self.winfo_id())
        stylew = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        stylew = stylew & ~WS_EX_TOOLWINDOW
        stylew = stylew | WS_EX_APPWINDOW
        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, stylew)
        # self.update()

    def center_window(self, window: Optional[CTk] = None):
        if window is None:
            window = self
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        x = int(screen_width / 2 - self._apply_window_scaling(self.cfg.width) / 2)
        y = int(screen_height / 2 - self._apply_window_scaling(self.cfg.height) / 2 - 16)
        # y -= y + self._apply_window_scaling(self.cfg.height)
        window.geometry(f'{self.cfg.width}x{self.cfg.height}+{x}+{y}')
        window.update()

    def on_deiconify_main_window(self, event=None):
        self.minimized = False

    def minimize(self):
        # hwnd = win32gui.GetForegroundWindow()
        hwnd = windll.user32.GetParent(self.winfo_id())
        SW_MINIMIZE = 6
        self.after(0, win32gui.ShowWindow, hwnd, SW_MINIMIZE)
        self.minimized = True

    def open(self):
        self.mainloop()

    def hide(self, hide=True):
        self.withdraw()

    def show(self, hide=True):
        self.deiconify()

    def _close(self):
        self.after(0, self.destroy)
        log.debug('GUI stopped')

    def is_shown(self):
        try:
            return self.state() == 'normal'
        except Exception as e:
            return False

    def get_resource_path(self, resource_path: str = ''):
        return f'{str(self.__class__.__qualname__)}'


class UIToplevel(UIWindow, CTkToplevel):
    def __init__(self, master: Union[UIWindow, 'UIToplevel'], lock_master=True, **kwargs):
        UIWindow.__init__(self, cfg=UIWindowConfig())
        CTkToplevel.__init__(self, master=master, **kwargs)
        self.master: Union[UIWindow, 'UIToplevel'] = master
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.lock_master = lock_master
        self.hide()
        self.tooltip_engine = UIToolTipEngine()

    def apply_config(self):
        if self.cfg.no_titlebar:
            self.overrideredirect(True)
        self.title(self.cfg.title)
        if self.cfg.icon_path is not None:
            self.after(200, lambda: self.iconbitmap(self.cfg.icon_path))
        # self.resizable(not self.cfg.locked_width, not self.cfg.locked_height)
        self.geometry(f'{self.cfg.width}x{self.cfg.height}')

    def center_window(self, window: Optional[CTkToplevel] = None, anchor_to_master=True):
        if window is None:
            window = self
        if anchor_to_master:
            x = int(self.master.winfo_rootx() + self.master.winfo_width() / 2 - self._apply_window_scaling(self.cfg.width) / 2)
            y = int(self.master.winfo_rooty() + self.master.winfo_height() / 2 - self._apply_window_scaling(self.cfg.height) / 2 - 16)
        else:
            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            screen_height = ctypes.windll.user32.GetSystemMetrics(1)
            x = int(screen_width / 2 - self._apply_window_scaling(self.cfg.width) / 2)
            y = int(screen_height / 2 - self._apply_window_scaling(self.cfg.height) / 2 - 16)
            # y -= y + self._apply_window_scaling(self.cfg.height)
        window.geometry(f'{self.cfg.width}x{self.cfg.height}+{x}+{y}')

    def hide(self, hide=True):
        self.withdraw()

    def show(self, hide=True):
        self.deiconify()

    def _close(self):
        self.master.remove_top_level(self)
        if self.lock_master:
            top_level = self.master.get_top_level(locking=True)
            top_level.attributes('-disabled', 0)
        self.destroy()
        log.debug('TopLevel closed')

    def open(self):
        if self.lock_master:
            top_level = self.master.get_top_level(locking=True)
            top_level.attributes('-disabled', 1)
            # self.transient(top_level)
        self.master.add_top_level(self)
        self.show()

    def is_shown(self):
        try:
            return self.state() == 'normal'
        except Exception as e:
            return False

    def get_resource_path(self, resource_path: str = ''):
        if self.resource_override is not None:
            return self.resource_override
        return f'{str(self.__class__.__qualname__)}'
