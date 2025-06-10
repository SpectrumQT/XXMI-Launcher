import sys
import logging
import time
import tkinter
import re
# import cv2
# import math

from typing import Union, Tuple, List, Dict, Optional, Callable
from pathlib import Path

from tkinter import Menu, INSERT, font
from customtkinter import CTkBaseClass, CTkButton, CTkImage, CTkLabel, CTkProgressBar, CTkEntry, CTkCheckBox, CTkTextbox, CTkOptionMenu, CTkRadioButton, StringVar
from customtkinter import END, CURRENT
from customtkinter import ThemeManager, CTkFont
from PIL import Image, ImageTk

import core.config_manager as Config

from gui.classes.element import UIElementBase
from gui.classes.windows import UIWindow

logging.getLogger('PIL').setLevel(logging.INFO)


class UIWidget(UIElementBase):
    def __init__(self, master, **kwargs):
        UIElementBase.__init__(self, **kwargs)
        self.master = master
        # CTkBaseClass.__init__(self, master=master)


class UICanvasWidget(UIWidget):
    def winfo_rootx(self):
        x = self.winfo_x()
        if self._anchor in ['center', 'n', 's']:
            return self.canvas.winfo_rootx() + x - int(self.winfo_width() / 2)
        return self.canvas.winfo_rootx() + x

    def winfo_rooty(self):
        y = self.winfo_y()
        if self._anchor in ['center', 'w', 'e']:
            return self.canvas.winfo_rooty() + y - int(self.winfo_height() / 2)
        return self.canvas.winfo_rooty() + y

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height

    def winfo_x(self):
        return self._x

    def winfo_y(self):
        return self._y


class UIText(UICanvasWidget, CTkBaseClass):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 font: str,
                 fill: str = 'black',
                 activefill: str = 'black',
                 disabledfill: str = 'black',
                 justify: str = 'left',
                 state: str = '',
                 tags: str = '',
                 width: int = 0,
                 text: str = '',
                 x: int = 0,
                 y: int = 0,
                 canvas=None,
                 anchor=None,
                 **kwargs):
        if 'Asap' in font:
            y -= 1
        self.master = master
        self.canvas = canvas or master.canvas
        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master,  **kwargs)
        self.fill = fill
        self.activefill = activefill
        self.disabledfill = disabledfill
        self._x = None
        self._y = None
        self._width = None
        self._height = None
        self._font_obj = None
        self._anchor = anchor

        if isinstance(font, str):
            font_pattern = re.compile(r'(?P<family>.*)\s(?P<size>\d+)\s*(?P<weight>.*)?')
            result = list(re.finditer(font_pattern, font))
            if len(result) != 1:
                raise ValueError(f'Failed to parse font from {font}!')
            font = result[0].groupdict()
            if font['weight']:
                font = (font['family'], int(font['size']), font['weight'])
            else:
                font = (font['family'], int(font['size']))

        self._font = CTkFont() if font is None else self._check_font_type(font)

        self._text_id = self.canvas.create_text(0, 0)

        self.configure(fill=fill, activefill=activefill, disabledfill=disabledfill, justify=justify, state=state,
                       tags=tags, width=width, font=self._font, text=text, anchor=anchor, **kwargs)
        self.set(text)

        self._apply_theme()

        self.move(x, y)

    def configure(self, require_redraw=False, **kwargs):
        if "font" in kwargs:
            self._font = self._apply_font_scaling(tuple(kwargs.pop("font")))
            self._font_obj = font.Font(family=self._font[0], size=self._font[1])
            self._height = self._font_obj.metrics('linespace')
            self.canvas.itemconfig(self._text_id, font=self._font)

        self.canvas.itemconfig(self._text_id, **kwargs)

    def move(self, x, y):
        self._x = int(self._apply_widget_scaling(x))
        self._y = int(self._apply_widget_scaling(y))
        self.canvas.coords(self._text_id, self._x, self._y)

    def set(self, text: str):
        self.canvas.itemconfigure(self._text_id, text=text)
        self._width = self._font_obj.measure(text)

    def _show(self):
        self.canvas.itemconfigure(self._text_id, state='normal')

    def _hide(self):
        self.canvas.itemconfigure(self._text_id, state='hidden')

    def force_normal(self):
        self.canvas.itemconfigure(self._text_id, fill=self.fill)

    def force_active(self):
        self.canvas.itemconfigure(self._text_id, fill=self.activefill, activefill=self.activefill)

    def force_disabled(self):
        self.canvas.itemconfigure(self._text_id, fill=self.disabledfill, activefill=self.disabledfill)

    def bind(self, *args, **kwargs):
        self.canvas.tag_bind(self._text_id, *args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.canvas.tag_unbind(self._text_id, *args, **kwargs)

    def destroy(self):
        try:
            self.canvas.delete(self._text_id)
        except:
            pass
        super().destroy()


class UIImage(UICanvasWidget, CTkBaseClass):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 canvas=None,
                 image_path: Optional[Path] = None,
                 x: int = 0,
                 y: int = 0,
                 width: int = 64,
                 height: int = 64,
                 anchor: str = 'center',
                 opacity: float = 1,
                 brightness: float = 1,
                 **kwargs):
        self.master = master
        self.canvas = canvas or master.canvas
        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master,  **kwargs)

        self._x = None
        self._y = None
        self._width = None
        self._height = None
        self._anchor = None
        self.opacity = None
        self.brightness = None

        self._image = None
        self.image = None
        self.image_path = None
        self.image_tag = None

        # self._supported_extensions = ['.mp4', '.mkv', '.avi', '.gif', '.webp', '.jpeg', '.png', '.jpg']
        self._supported_extensions = ['.webp', '.jpeg', '.png', '.jpg']

        # self._video = None
        # self._video_fps = None
        # self._video_frame_time = None
        # self._video_last_frame_time = 0
        # self._video_buffer = []
        # self._video_buffering_time = 0
        # self._video_rendering_active = False
        # self._video_frame_counter = []

        self.configure(image_path=image_path, x=x, y=y, width=width, height=height, anchor=anchor,
                       opacity=opacity, brightness=brightness, **kwargs)

        self._apply_theme()

    def configure(self, **kwargs):
        if self._update_attrs(['image_path'], kwargs):
            path = Path(self.image_path)

            # Resolve relative path from active theme
            # Also search for files with same name but different extension to support advanced themes
            if not path.is_absolute():
                path = Config.get_resource_path(self, path, self._supported_extensions)

            # if path.suffix in ['.mp4', '.gif', '.mkv', '.avi']:
            #     self._update_attrs(list(kwargs.keys()), kwargs)
            #
            #     self._video = cv2.VideoCapture(str(path))
            #
            #     self._video_fps = int(self._video.get(cv2.CAP_PROP_FPS))
            #     self._video_frame_time = 1000 / self._video_fps / 1000
            #
            #     if self.image_tag is None:
            #         self.image_tag = self.canvas.create_image(self._x, self._y, anchor=self.anchor, **kwargs)
            #
            #     # Start async video renderer
            #     if not self._video_rendering_active:
            #         self._video_rendering_active = True
            #         self._buffer_frame()
            #         self._render_frame()
            #         # self.print_fps()
            #
            # else:
            # Signal async video renderer to stop if it's active
            #     if self._video_rendering_active:
            #         self._video_rendering_active = False

            self._image = Image.open(str(path))

        if self._update_attrs(['width', 'height', 'opacity', 'brightness'], kwargs):
            self.image = self.create_image(self._image, self._width, self._height, self.opacity, self.brightness)
            if self.image_tag is None:
                self._update_attrs(['x', 'y', 'anchor'], kwargs)
                self.image_tag = self.canvas.create_image(self._x, self._y, anchor=self._anchor, **kwargs)
            self.set_image(self.image)

        if self._update_attrs(['x', 'y'], kwargs):
            self.move(self._x, self._y)

        if self._update_attrs(['anchor'], kwargs):
            self.canvas.itemconfigure(self.image_tag, anchor=self._anchor)

    # def _buffer_frame(self):
    #     if not self._video_rendering_active:
    #         if self._video is not None:
    #             self._video.release()
    #             self._video = None
    #         return
    #
    #     if len(self._video_buffer) > 2:
    #         return
    #
    #     t = time.time()
    #
    #     ret, frame = self._video.read()
    #
    #     if not ret:
    #         self._video.set(cv2.CAP_PROP_POS_FRAMES, 0)
    #         self._buffer_frame()
    #         return
    #
    #     frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    #
    #     frame_height, frame_width, channels = frame.shape
    #     width = int(self._apply_widget_scaling(self.width))
    #     height = int(self._apply_widget_scaling(self.height))
    #     if frame_width != width or frame_height != height:
    #         frame = cv2.resize(frame, (width, height))
    #
    #     # self._video_buffer.append(self.create_image(image, self.width, self.height, self.opacity, self.brightness))
    #     self._video_buffer.append(ImageTk.PhotoImage(Image.fromarray(frame)))
    #
    #     self._video_buffering_time = time.time()-t
    #
    #     self.after(5, self._buffer_frame)
    #
    # def _render_frame(self):
    #     if not self._video_rendering_active:
    #         return
    #
    #     render_time = time.time() - self._video_last_frame_time
    #
    #     # t = time.time()
    #
    #     # self.count_fps()
    #
    #     # Buffer few frames ahead in async way so rendering wouldn't have to wait for frame image extraction
    #     self.after(5, self._buffer_frame)
    #
    #     delay = self._video_frame_time
    #
    #     if len(self._video_buffer) != 0:
    #
    #         self.image = self._video_buffer.pop(0)
    #         self.set_image(self.image)
    #
    #         # print(t - self._last_frame_time)
    #         # self._last_frame_time = t
    #
    #         # render_time = time.time() - t
    #
    #         if render_time + self._video_buffering_time > self._video_frame_time:
    #             delay *= math.ceil((render_time + self._video_buffering_time) / self._video_frame_time)
    #
    #         delay -= render_time
    #
    #         # print(render_time, self._video_buffering_time, delay)
    #         self._video_last_frame_time = time.time()
    #
    #     self.after(int(delay*1000), self._render_frame)
    #
    # def count_fps(self):
    #     t = time.time()
    #     for x in range(len(self._video_frame_counter)):
    #         if t - self._video_frame_counter[0] > 1:
    #             del self._video_frame_counter[0]
    #         else:
    #             break
    #     self._video_frame_counter.append(t)
    #
    # def print_fps(self, interval=250):
    #     print(len(self._video_frame_counter), len(self._video_buffer))
    #     self.after(interval, self.print_fps)

    def _update_attrs(self, attrs, kwargs):
        attrs_updated = False
        for arg in attrs:
            if arg in kwargs:
                value = kwargs.pop(arg)
                if arg in ['x', 'y']:
                    arg = '_' + arg
                    value = int(self._apply_widget_scaling(value))
                if arg in ['width', 'height', 'anchor']:
                    arg = '_' + arg
                setattr(self, arg, value)
                attrs_updated = True
        return attrs_updated

    def set_image(self, image):
        self.canvas.itemconfig(self.image_tag, image=image)

    def create_image(self, image: Image, width, height, opacity: float, brightness: float):
        # Modify opacity and/or brightness
        if opacity != 1 or brightness != 1:
            channels = image.split()
            output = []
            for channel_id, channel in enumerate(channels):
                # RGB
                if channel_id <= 2 and brightness != 1:
                    channel = channel.point(lambda p: p * brightness)
                # Alpha
                elif channel_id == 3 and opacity != 1:
                    channel = channel.point(lambda p: p * opacity)
                output.append(channel)
            image = Image.merge(image.mode, output)
        # Modify size and/or brightness
        width = int(self._apply_widget_scaling(width))
        height = int(self._apply_widget_scaling(height))
        if image.width != width or image.height != height:
            image = image.resize((width, height))

        return ImageTk.PhotoImage(image)

    def move(self, x, y):
        self._x = int(self._apply_widget_scaling(x))
        self._y = int(self._apply_widget_scaling(y))
        self.canvas.coords(self.image_tag, self._x, self._y)

    def _show(self):
        self.canvas.itemconfigure(self.image_tag, state='normal')

    def _hide(self):
        self.canvas.itemconfigure(self.image_tag, state='hidden')

    def bind(self, *args, **kwargs):
        self.canvas.tag_bind(self.image_tag, *args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.canvas.tag_unbind(self.image_tag, *args, **kwargs)

    def destroy(self):
        try:
            self.canvas.delete(self.image_tag)
        except:
            pass
        self.image = None
        super().destroy()


class UIImageButton(UICanvasWidget, CTkBaseClass):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 x: int = 40,
                 y: int = 40,
                 width: int = 48,
                 height: int = 48,
                 anchor: str = 'center',
                 command: Callable = None,
                 disabled: bool = False,
                 # Background Image
                 bg_image_path: Optional[Path] = None,
                 bg_width: int = 64,
                 bg_height: int = 64,
                 bg_normal_opacity: float = 1,
                 bg_hover_opacity: float = 1,
                 bg_selected_opacity: float = 1,
                 bg_disabled_opacity: float = 1,
                 bg_normal_brightness: float = 1,
                 bg_hover_brightness: float = 1,
                 bg_selected_brightness: float = 1,
                 bg_disabled_brightness: float = 1,
                 # Button Image
                 button_image_path: Optional[Path] = None,
                 button_x_offset: int = 0,
                 button_y_offset: int = 0,
                 button_normal_opacity: float = 1,
                 button_hover_opacity: float = 1,
                 button_selected_opacity: float = 1,
                 button_disabled_opacity: float = 1,
                 button_normal_brightness: float = 1,
                 button_hover_brightness: float = 1,
                 button_selected_brightness: float = 1,
                 button_disabled_brightness: float = 1,
                 # Text
                 text: str = None,
                 font: str = 'Roboto 14',
                 justify: str = 'left',
                 text_x_offset: int = 0,
                 text_y_offset: int = 0,
                 text_anchor: str = None,
                 fill: str = 'black',
                 activefill: str = 'black',
                 disabledfill: str = 'black',
                 canvas=None,
                 **kwargs):

        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master,  **kwargs)

        self.master = master
        self.canvas = canvas or master.canvas
        self.command = command
        self.disabled = disabled

        self._x = x
        self._y = y
        self._anchor = anchor
        self._button_x_offset = button_x_offset
        self._button_y_offset = button_y_offset
        self._text_x_offset = text_x_offset
        self._text_y_offset = text_y_offset

        self._bg_image = None
        if bg_image_path is not None:
            self._bg_image = self.put(UIImage(master=master, image_path=bg_image_path, width=bg_width, height=bg_height,
                                      x=x, y=y, anchor=anchor,
                                      opacity=bg_normal_opacity, brightness=bg_normal_brightness))
            self.bg_apply_normal = lambda: self._bg_image.configure(opacity=bg_normal_opacity, brightness=bg_normal_brightness)
            self.bg_apply_hover = lambda: self._bg_image.configure(opacity=bg_hover_opacity, brightness=bg_hover_brightness)
            self.bg_apply_select = lambda: self._bg_image.configure(opacity=bg_selected_opacity, brightness=bg_selected_brightness)
            self.bg_apply_disable = lambda: self._bg_image.configure(opacity=bg_disabled_opacity, brightness=bg_disabled_brightness)

        self._button_image = None
        if button_image_path is not None:
            self._button_image = self.put(UIImage(master=master, image_path=button_image_path, width=width, height=height,
                                                  x=button_x_offset+x, y=button_y_offset+y, anchor=anchor,
                                                  opacity=button_normal_opacity, brightness=button_normal_brightness))
            self.button_apply_normal = lambda: self._button_image.configure(opacity=button_normal_opacity, brightness=button_normal_brightness)
            self.button_apply_hover = lambda: self._button_image.configure(opacity=button_hover_opacity, brightness=button_hover_brightness)
            self.button_apply_select = lambda: self._button_image.configure(opacity=button_selected_opacity, brightness=button_selected_brightness)
            self.button_apply_disable = lambda: self._button_image.configure(opacity=button_disabled_opacity, brightness=button_disabled_brightness)

        self._text_image = None
        if text is not None:
            self._text_image = self.put(UIText(master=master, canvas=self.canvas, text=text, font=font, width=0, justify=justify,
                                        x=text_x_offset+x, y=text_y_offset+y, anchor=text_anchor or anchor,
                                        fill=fill, activefill=activefill, disabledfill=disabledfill))

        self.update_dimensions()

        self.hovered = False
        self.selected = False

        self._apply_theme()
        
        self.bind("<ButtonPress-1>", self._handle_button_press)
        self.bind("<ButtonRelease-1>", self._handle_button_release)
        self.bind("<Enter>", self._handle_enter)
        self.bind("<Leave>", self._handle_leave)

    def move(self, x=None, y=None):
        x = x or self._x
        y = y or self._y
        self._x = x
        self._y = y
        if self._bg_image is not None:
            self._bg_image.move(x, y)
        if self._button_image is not None:
            self._button_image.move(self._button_x_offset+x, self._button_y_offset+y)
        if self._text_image is not None:
            self._text_image.move(self._text_x_offset+x, self._text_y_offset+y)
        self.update_dimensions()

    def update_dimensions(self):
        x0, y0, x1, y1 = None, None, None, None

        for widget in [self._bg_image, self._button_image, self._text_image]:
            if widget is None:
                continue
            x0 = widget._x if x0 is None else min(x0, widget._x)
            y0 = widget._y if y0 is None else min(y0, widget._y)
            x1 = widget._x + widget._width if x1 is None else max(x1, widget._x + widget._width)
            y1 = widget._y + widget._height if y1 is None else max(y1, widget._y + widget._height)

        self._width = x1 - x0
        self._height = y1 - y0

    def set_text(self, text):
        self._text_image.set(text)
        self.update_dimensions()

    def bind(self, *args, **kwargs):
        for element in self.elements.values():
            element.bind(*args, **kwargs)

    def unbind(self, *args, **kwargs):
        for element in self.elements.values():
            element.unbind(*args, **kwargs)

    def _handle_button_press(self, event):
        if self.disabled:
            return
        self.set_selected(True)

    def _handle_button_release(self, event):
        if self.disabled:
            return
        self.set_selected(False)
        if self.hovered:
            self.command()

    def _handle_enter(self, event):
        self.hovered = True
        if self.disabled:
            self.set_disabled(self.disabled)
            return
        self.canvas.config(cursor="hand2")
        if self.selected:
            self.set_selected(self.selected)
        else:
            if self._bg_image:
                self.bg_apply_hover()
            if self._button_image:
                self.button_apply_hover()
        if self._text_image:
            self._text_image.force_active()

    def _handle_leave(self, event):
        self.hovered = False
        if self.disabled:
            self.set_disabled(self.disabled)
            return
        self.canvas.config(cursor="")
        if self.selected:
            self.set_selected(self.selected)
        else:
            if self._bg_image:
                self.bg_apply_normal()
            if self._button_image:
                self.button_apply_normal()
        if self._text_image:
            self._text_image.force_normal()

    def set_selected(self, selected: bool = False):
        self.selected = selected
        if selected:
            self.disabled = False
            if self._bg_image:
                self.bg_apply_select()
            if self._button_image:
                self.button_apply_select()
        else:
            if self.hovered:
                self._handle_enter(None)
            else:
                self._handle_leave(None)

    def set_disabled(self, disabled: bool = False):
        self.disabled = disabled
        if disabled:
            if self._bg_image:
                self.bg_apply_disable()
            if self._button_image:
                self.button_apply_disable()
            if self._text_image:
                self._text_image.force_disabled()
        else:
            if self.hovered:
                self._handle_enter(None)
            else:
                self._handle_leave(None)

    def _show(self):
        pass

    def _hide(self):
        pass

    def winfo_x(self):
        return int(self._apply_widget_scaling(self._x))

    def winfo_y(self):
        return int(self._apply_widget_scaling(self._y))

    def winfo_width(self):
        return int(self._apply_widget_scaling(self._width))

    def winfo_height(self):
        return int(self._apply_widget_scaling(self._height))


class UILabel(UIWidget, CTkLabel):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 image_path: Optional[Path] = None,
                 state: str = tkinter.NORMAL,
                 text_color_disabled: Optional[Union[str, Tuple[str, str]]] = None,
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        self._state = state
        self.image: Optional[CTkImage] = None
        if image_path is not None:
            self._supported_extensions = ['.webp', '.jpeg', '.png', '.jpg']
            self.image = CTkImage(Image.open(str(Config.get_resource_path(self, image_path, self._supported_extensions))))
        CTkLabel.__init__(self, master, image=self.image, **kwargs)

        if text_color_disabled is None:
            if "text_color_disabled" in ThemeManager.theme["CTkLabel"]:
                self._text_color_disabled = ThemeManager.theme["CTkLabel"]["text_color_disabled"]
            else:
                self._text_color_disabled = self._text_color
        else:
            self._text_color_disabled = self._check_color_type(text_color_disabled)

        self._apply_theme()

    def set(self, value):
        self.configure(text=value)

    def configure(self, require_redraw=False, **kwargs):
        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            require_redraw = True

        super().configure(require_redraw, **kwargs)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._current_width),
                                                                              self._apply_widget_scaling(self._current_height),
                                                                              self._apply_widget_scaling(self._corner_radius),
                                                                              0)
        if self._state == tkinter.DISABLED:
            text_color = self._text_color_disabled
        else:
            text_color = self._text_color

        if no_color_updates is False or requires_recoloring:
            if self._apply_appearance_mode(self._fg_color) == "transparent":
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._bg_color),
                                        outline=self._apply_appearance_mode(self._bg_color))

                self._label.configure(fg=self._apply_appearance_mode(text_color),
                                      disabledforeground=self._apply_appearance_mode(self._text_color_disabled),
                                      bg=self._apply_appearance_mode(self._bg_color))
            else:
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._fg_color),
                                        outline=self._apply_appearance_mode(self._fg_color))

                self._label.configure(fg=self._apply_appearance_mode(text_color),
                                      disabledforeground=self._apply_appearance_mode(self._text_color_disabled),
                                      bg=self._apply_appearance_mode(self._fg_color))

            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))


class UIButton(UIWidget, CTkButton):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 image_path: Optional[Path] = None,
                 select_color: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color_hovered: Optional[Union[str, Tuple[str, str]]] = None,
                 text_color_selected: Optional[Union[str, Tuple[str, str]]] = None,
                 auto_width: bool = False,
                 padx: int = 12,
                 **kwargs):

        UIWidget.__init__(self, master,  **kwargs)

        self._auto_width = auto_width
        self._padx = padx
        self.image: Optional[CTkImage] = None
        if image_path is not None:
            self._supported_extensions = ['.webp', '.jpeg', '.png', '.jpg']
            self.image = CTkImage(Image.open(str(Config.get_resource_path(self, image_path, self._supported_extensions))))

        self.is_hovered = False
        self.is_selected = False

        self._select_color: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["select_color"] if select_color is None else self._check_color_type(select_color)
        self._text_color_hovered: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["text_color_hovered"] if text_color_hovered is None else self._check_color_type(text_color_hovered)
        self._text_color_selected: Union[str, Tuple[str, str]] = ThemeManager.theme["CTkButton"]["text_color_selected"] if text_color_selected is None else self._check_color_type(text_color_selected)

        CTkButton.__init__(self, master, image=self.image, **kwargs)

        self._apply_theme()

        if self._auto_width:
            self._set_auto_width()
        
        self.unbind('<Button-1>')

    def configure(self, require_redraw=False, **kwargs):
        if 'select_color' in kwargs:
            self._select_color = self._check_color_type(kwargs.pop('select_color'))
            require_redraw = True
        if 'text_color_hovered' in kwargs:
            self._text_color_hovered = self._check_color_type(kwargs.pop('text_color_hovered'))
            require_redraw = True
        if 'text_color_selected' in kwargs:
            self._text_color_selected = self._check_color_type(kwargs.pop('text_color_selected'))
            require_redraw = True

        require_auto_width = False

        if 'padx' in kwargs:
            self._padx = kwargs.pop('padx')
            require_auto_width = True

        if self._auto_width:
            if 'font' in kwargs or 'text' in kwargs:
                require_auto_width = True

        text_font = kwargs.get('font', None)
        if text_font is not None:
            kwargs['font'] = tuple(text_font)

        super().configure(require_redraw, **kwargs)

        if require_auto_width:
            self._set_auto_width()

    def _set_auto_width(self):
        scaling = self._apply_widget_scaling(1)
        offset = self._padx * 2
        text_width = int(self._text_label.winfo_reqwidth()/scaling)
        if scaling != 1:
            offset += self._apply_widget_scaling(2)
        self.configure(width=text_width+offset)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        if self._background_corner_colors is not None:
            self._draw_engine.draw_background_corners(self._apply_widget_scaling(self._current_width),
                                                      self._apply_widget_scaling(self._current_height))
            self._canvas.itemconfig("background_corner_top_left",
                                    fill=self._apply_appearance_mode(self._background_corner_colors[0]))
            self._canvas.itemconfig("background_corner_top_right",
                                    fill=self._apply_appearance_mode(self._background_corner_colors[1]))
            self._canvas.itemconfig("background_corner_bottom_right",
                                    fill=self._apply_appearance_mode(self._background_corner_colors[2]))
            self._canvas.itemconfig("background_corner_bottom_left",
                                    fill=self._apply_appearance_mode(self._background_corner_colors[3]))
        else:
            self._canvas.delete("background_parts")

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(
            self._apply_widget_scaling(self._current_width),
            self._apply_widget_scaling(self._current_height),
            self._apply_widget_scaling(self._corner_radius),
            self._apply_widget_scaling(self._border_width))

        if no_color_updates is False or requires_recoloring:

            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            # set color for the button border parts (outline)
            self._canvas.itemconfig("border_parts",
                                    outline=self._apply_appearance_mode(self._border_color),
                                    fill=self._apply_appearance_mode(self._border_color))

            # set color for inner button parts
            if self._fg_color == "transparent":
                self._canvas.itemconfig("inner_parts",
                                        outline=self._apply_appearance_mode(self._bg_color),
                                        fill=self._apply_appearance_mode(self._bg_color))
            else:
                self._canvas.itemconfig("inner_parts",
                                        outline=self._apply_appearance_mode(self._fg_color),
                                        fill=self._apply_appearance_mode(self._fg_color))

        # create text label if text given
        if self._text is not None and self._text != "":

            if self._text_label is None:
                self._text_label = tkinter.Label(master=self,
                                                 font=self._apply_font_scaling(self._font),
                                                 text=self._text,
                                                 padx=0,
                                                 pady=0,
                                                 borderwidth=1,
                                                 textvariable=self._textvariable)
                self._create_grid()

                self._text_label.bind("<Enter>", self._on_enter)
                self._text_label.bind("<Leave>", self._on_leave)
                self._text_label.bind("<Button-1>", self._clicked)
                self._text_label.bind("<Button-1>", self._clicked)

            if no_color_updates is False:
                # set text_label fg color (text color)

                if self.is_selected:
                    self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_selected)))
                elif self.is_hovered:
                    self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_hovered)))
                elif self._state == tkinter.DISABLED:
                    self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_disabled)))
                else:
                    self._text_label.configure(fg=self._apply_appearance_mode(self._text_color))

                if self._apply_appearance_mode(self._fg_color) == "transparent":
                    self._text_label.configure(bg=self._apply_appearance_mode(self._bg_color))
                else:
                    self._text_label.configure(bg=self._apply_appearance_mode(self._fg_color))

        else:
            # delete text_label if no text given
            if self._text_label is not None:
                self._text_label.destroy()
                self._text_label = None
                self._create_grid()

        # create image label if image given
        if self._image is not None:

            if self._image_label is None:
                self._image_label = tkinter.Label(master=self)
                self._update_image()  # set image
                self._create_grid()

                self._image_label.bind("<Enter>", self._on_enter)
                self._image_label.bind("<Leave>", self._on_leave)
                self._image_label.bind("<Button-1>", self._clicked)
                self._image_label.bind("<Button-1>", self._clicked)

            if no_color_updates is False:
                # set image_label bg color (background color of label)
                if self._apply_appearance_mode(self._fg_color) == "transparent":
                    self._image_label.configure(bg=self._apply_appearance_mode(self._bg_color))
                else:
                    self._image_label.configure(bg=self._apply_appearance_mode(self._fg_color))

        else:
            # delete text_label if no text given
            if self._image_label is not None:
                self._image_label.destroy()
                self._image_label = None
                self._create_grid()

    def _on_enter(self, event=None):
        self.is_hovered = True

        if self.is_hovered:
            self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_hovered)))
        elif self._state == tkinter.DISABLED:
            self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_disabled)))

        if self._hover is True and self._state == "normal" or self.is_selected:
            if self.is_selected:
                inner_parts_color = self._select_color
                self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_selected)))
            else:
                if self._hover_color is None:
                    inner_parts_color = self._fg_color
                else:
                    inner_parts_color = self._hover_color

                if self._state != tkinter.DISABLED:
                    self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_hovered)))
                else:
                    self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_disabled)))

            # set color of inner button parts to hover color
            self._canvas.itemconfig("inner_parts",
                                    outline=self._apply_appearance_mode(inner_parts_color),
                                    fill=self._apply_appearance_mode(inner_parts_color))

            # set text_label bg color to button hover color
            if self._text_label is not None:
                self._text_label.configure(bg=self._apply_appearance_mode(inner_parts_color))

            # set image_label bg color to button hover color
            if self._image_label is not None:
                self._image_label.configure(bg=self._apply_appearance_mode(inner_parts_color))

        self._set_cursor()

    def _on_leave(self, event=None):
        self.is_hovered = False

        self._click_animation_running = False

        self._set_cursor()

        if self.is_selected:
            return

        if self._fg_color == "transparent":
            inner_parts_color = self._bg_color
        else:
            inner_parts_color = self._fg_color

        # set color of inner button parts
        self._canvas.itemconfig("inner_parts",
                                outline=self._apply_appearance_mode(inner_parts_color),
                                fill=self._apply_appearance_mode(inner_parts_color))

        # set text_label bg color (label color)
        if self._text_label is not None:
            self._text_label.configure(bg=self._apply_appearance_mode(inner_parts_color))

        # set image_label bg color (image bg color)
        if self._image_label is not None:
            self._image_label.configure(bg=self._apply_appearance_mode(inner_parts_color))

        self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color)))

    def _clicked(self, event=None):
        if not self.is_hovered:
            return
        super()._clicked(event)

    def _create_bindings(self, sequence: Optional[str] = None):
        if sequence == "<Button-1>":
            self.bind('<ButtonRelease-1>', self._clicked)
            return
        super()._create_bindings(sequence)

    def _set_cursor(self):
        if self._cursor_manipulation_enabled:
            if self._state == tkinter.DISABLED or not self.is_hovered:
                if sys.platform == "darwin" and self._command is not None:
                    self.configure(cursor="arrow")
                elif sys.platform.startswith("win") and self._command is not None:
                    self.configure(cursor="arrow")

            elif self._state == tkinter.NORMAL:
                if sys.platform == "darwin" and self._command is not None:
                    self.configure(cursor="pointinghand")
                elif sys.platform.startswith("win") and self._command is not None:
                    self.configure(cursor="hand2")

    def set_selected(self, selected: bool = False):
        self.is_selected = selected
        if selected:
            self._on_enter()
        else:
            self._on_leave()


class UIRadioButton(UIWidget, CTkRadioButton):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):

        UIWidget.__init__(self, master,  **kwargs)

        CTkRadioButton.__init__(self, master, **kwargs)

        self._apply_theme()


class UIProgressBar(UIWidget, CTkProgressBar):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        CTkProgressBar.__init__(self, master, **kwargs)

        self._apply_theme()


class UIEntry(CTkEntry, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):

        # Original tkEntry fails with empty string for IntVar and behaves poorly with input filtering overall
        # Here we solve it via creating proxy StringVar and updating original IntVar with filtered input (r'-*\d*')
        # TODO: Refactor
        # TODO: Add float support
        self._original_textvariable = None
        textvariable = kwargs.get('textvariable', None)
        if textvariable is not None:
            value = textvariable.get()
            if isinstance(value, int):
                self._original_textvariable = textvariable
                proxy_var = StringVar(master=master, value=f'{value}')
                proxy_var.trace_add('write', self.handle_proxy_var_update)
                kwargs['textvariable'] = proxy_var

        UIWidget.__init__(self, master,  **kwargs)
        self._fg_color_disabled = ThemeManager.theme["CTkEntry"].get("fg_color_disabled", None)
        self._border_color_disabled = ThemeManager.theme["CTkEntry"].get("border_color_disabled", None)
        self._text_color_disabled = ThemeManager.theme["CTkEntry"].get("text_color_disabled", None)
        CTkEntry.__init__(self, master, **kwargs)

        if self._original_textvariable is not None:
            self.trace_write(self._original_textvariable, self.handle_original_var_update)

        self.state_log = [('', 0)]
        self.state_id = -1

        self.bind("<Key>", self.initialize_state_log)
        self.bind("<Control-KeyPress>", self.handle_key_press)
        self.bind("<KeyRelease>", self.add_state)
        self.bind("<<Cut>>", lambda event: self.after(200, self.add_state))
        self.bind("<Button-3>", self.handle_button3)
        self.bind("<<Paste>>", self.paste_to_selection)
        self.bind("<Return>", self.handle_return)

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.config(font=self._apply_font_scaling(('Asap', 14)))
        self.context_menu.add_command(label="Cut")
        self.context_menu.add_command(label="Copy")
        self.context_menu.add_command(label="Paste")

        self._apply_theme()

    def handle_original_var_update(self, var, val):
        if self._textvariable.get() != str(val):
            self._textvariable.set(str(val))

    def handle_proxy_var_update(self, varname=None, index=None, mode=None):
        value = self._textvariable.get().strip()
        if value == '' or value == '-':
            return
        result = re.search(r'-?\d+', value)
        if result:
            filtered_value = result.group()
            if filtered_value == '' or filtered_value == '-':
                if filtered_value != value:
                    self.set(filtered_value)
                return
            self._original_textvariable.set(int(filtered_value))
            if filtered_value != value:
                self.set(filtered_value)
        else:
            self.set('')

    def _entry_focus_out(self, event=None):
        if self._original_textvariable is not None and self._textvariable.get().strip() == '':
            self.set('0')
        super()._entry_focus_out(event)

    def configure(self, require_redraw=False, **kwargs):
        if "state" in kwargs:
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw=require_redraw, **kwargs)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._current_width),
                                                                              self._apply_widget_scaling(self._current_height),
                                                                              self._apply_widget_scaling(self._corner_radius),
                                                                              self._apply_widget_scaling(self._border_width))

        if requires_recoloring or no_color_updates is False:
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            if self._apply_appearance_mode(self._fg_color) == "transparent":
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._bg_color),
                                        outline=self._apply_appearance_mode(self._bg_color))
                self._entry.configure(bg=self._apply_appearance_mode(self._bg_color),
                                      disabledbackground=self._apply_appearance_mode(self._bg_color),
                                      readonlybackground=self._apply_appearance_mode(self._bg_color),
                                      highlightcolor=self._apply_appearance_mode(self._bg_color))
            else:
                fg_color = self._fg_color
                if self._state == tkinter.DISABLED and self._fg_color_disabled:
                    fg_color = self._fg_color_disabled
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(fg_color),
                                        outline=self._apply_appearance_mode(fg_color))
                self._entry.configure(bg=self._apply_appearance_mode(fg_color),
                                      disabledbackground=self._apply_appearance_mode(fg_color),
                                      readonlybackground=self._apply_appearance_mode(fg_color),
                                      highlightcolor=self._apply_appearance_mode(fg_color))

            border_color = self._border_color
            if self._state == tkinter.DISABLED and self._border_color_disabled:
                border_color = self._border_color_disabled

            self._canvas.itemconfig("border_parts",
                                    fill=self._apply_appearance_mode(border_color),
                                    outline=self._apply_appearance_mode(border_color))

            if self._placeholder_text_active:
                self._entry.config(fg=self._apply_appearance_mode(self._placeholder_text_color),
                                   disabledforeground=self._apply_appearance_mode(self._placeholder_text_color),
                                   insertbackground=self._apply_appearance_mode(self._placeholder_text_color))
            else:
                text_color = self._text_color
                if self._state == tkinter.DISABLED and self._text_color_disabled:
                    text_color = self._text_color_disabled

                self._entry.config(fg=self._apply_appearance_mode(text_color),
                                   disabledforeground=self._apply_appearance_mode(text_color),
                                   insertbackground=self._apply_appearance_mode(text_color))

    def event_generate(self, *args, **kwargs):
        self._entry.event_generate(*args, **kwargs)

    def handle_key_press(self, event):
        if event.keycode == 65 and event.keysym.lower() != 'a':
            event.widget.event_generate("<<SelectAll>>")
        elif event.keycode == 67 and event.keysym.lower() != 'c':
            event.widget.event_generate("<<Copy>>")
        elif event.keycode == 86 and event.keysym.lower() != 'v':
            event.widget.event_generate("<<Paste>>")
        elif event.keycode == 88 and event.keysym.lower() != 'x':
            event.widget.event_generate("<<Cut>>")
        elif event.keycode == 89:
            self.redo()
        elif event.keycode == 90:
            self.undo()
        elif event.keycode == 65535:
            event.widget.event_generate("<<Clear>>")

    def destroy(self):
        # Remove default write-trace callback for textvariable if exists
        if not (self._textvariable is None or self._textvariable == ""):
            self._textvariable.trace_vdelete('w', self._textvariable_callback_name)
        super().destroy()

    def set(self, value):
        self.delete(0, END)
        self.insert(0, value)

    def handle_button3(self, event=None):
        self.initialize_state_log()
        self.show_context_menu(event)

    def handle_return(self, event):
        self.master.focus_set()
        
    def initialize_state_log(self, event=None):
        if len(self.state_log) == 1:
            self.state_log[0] = (self.get(), self.index(INSERT))
            self.state_id = 0
            # print(f'INIT STATE: {self.state_log}')
        else:
            self.set_state(self.state_id, None, self.index(INSERT))

    def get_state(self, state_id: int = None):
        if state_id is None:
            state_id = self.state_id
        return self.state_log[state_id][0]

    def get_index_after_state(self, state_id: int = None):
        if state_id is None:
            state_id = self.state_id
        return self.state_log[state_id][1]

    def set_state(self, state_id, value=None, index=None):
        if state_id < len(self.state_log):
            state = self.state_log[state_id]
            self.state_log[state_id] = (value or state[0], index or state[1])
        else:
            self.state_log.append((value, index))

    def add_state(self, event=None):
        if len(self.state_log) > 0:
            if self.get() == self.get_state():
                # print(f'NO CHANGES: {self.state_log}')
                return

            old_states = self.state_log[self.state_id:]
            # print(f'REMOVE: {old_states}  STATES: {self.state_log}')
            self.state_log = self.state_log[:self.state_id+1]

        self.state_id = len(self.state_log)
        self.set_state(self.state_id, self.get(), self.index(INSERT))
        # print(f'ADD State {self.state_id} ({self.get_state()}) STATES: {self.state_log}')

    def paste_to_selection(self, event):
        clipboard = ''
        try:
            clipboard = event.widget.clipboard_get()
        except:
            pass
        if not clipboard:
            return 'break'
        self.initialize_state_log()
        try:
            event.widget.delete('sel.first', 'sel.last')
        except:
            pass
        event.widget.insert('insert', clipboard)
        self.add_state()
        return 'break'

    def undo(self, event=None):
        new_state_id = self.state_id - 1
        # print(f'UNDO: State {self.state_id} -> {new_state_id} / {len(self.state_log)} ({self.get_state()} -> {self.get_state(new_state_id)})')
        if new_state_id >= 0:
            # print(f'SET: {self.get_state(new_state_id)} INDEX {self.get_index_after_state(new_state_id)}')
            self.set(self.get_state(new_state_id))
            self.icursor(self.get_index_after_state(new_state_id))
            self.state_id = new_state_id

    def redo(self, event=None):
        new_state_id = self.state_id + 1
        # print(f'REDO: State {self.state_id} -> {new_state_id} / {len(self.state_log)} ({self.get_state()})')
        if new_state_id < len(self.state_log):
            # print(f'SET: {self.get_state(new_state_id)} INDEX {self.get_index_after_state(new_state_id)}')
            self.set(self.get_state(new_state_id))
            self.icursor(self.get_index_after_state(new_state_id))
            self.state_id = new_state_id

    def show_context_menu(self, event):
        if self._state != tkinter.DISABLED:
            self.context_menu.post(event.x_root, event.y_root)
            self.context_menu.entryconfigure('Cut', command=lambda: self.event_generate('<<Cut>>'))
            self.context_menu.entryconfigure('Copy', command=lambda: self.event_generate('<<Copy>>'))
            self.context_menu.entryconfigure('Paste', command=lambda: self.event_generate('<<Paste>>'))


class UICheckbox(CTkCheckBox, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)

        self._fg_color_disabled = ThemeManager.theme["CTkCheckBox"].get("fg_color_disabled", None)
        self._checkmark_color_disabled = ThemeManager.theme["CTkCheckBox"].get("checkmark_color_disabled", None)
        self._border_color_disabled = ThemeManager.theme["CTkCheckBox"].get("border_color_disabled", None)

        self.is_hovered = False

        self._text_color_hovered = None
        if 'text_color_hovered' in kwargs:
            self._text_color_hovered = kwargs.pop('text_color_hovered')

        CTkCheckBox.__init__(self, master, **kwargs)

        if not self._text_color_hovered:
            self._text_color_hovered = self._text_color

        self._apply_theme()

        self.unbind('<Button-1>')

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        requires_recoloring_1 = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._checkbox_width),
                                                                                self._apply_widget_scaling(self._checkbox_height),
                                                                                self._apply_widget_scaling(self._corner_radius),
                                                                                self._apply_widget_scaling(self._border_width))

        if self._check_state is True:
            requires_recoloring_2 = self._draw_engine.draw_checkmark(self._apply_widget_scaling(self._checkbox_width),
                                                                     self._apply_widget_scaling(self._checkbox_height),
                                                                     self._apply_widget_scaling(self._checkbox_height * 0.5))
        else:
            requires_recoloring_2 = False
            self._canvas.delete("checkmark")

        if no_color_updates is False or requires_recoloring_1 or requires_recoloring_2:
            self._bg_canvas.configure(bg=self._apply_appearance_mode(self._bg_color))
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            if self._check_state is True:
                fg_color = self._fg_color
                if self._state == tkinter.DISABLED and self._fg_color_disabled:
                    fg_color = self._fg_color_disabled
                if self.is_hovered:
                    self._canvas.itemconfig("inner_parts",
                                            outline=self._apply_appearance_mode(self._hover_color),
                                            fill=self._apply_appearance_mode(self._hover_color))
                else:
                    self._canvas.itemconfig("inner_parts",
                                            outline=self._apply_appearance_mode(fg_color),
                                            fill=self._apply_appearance_mode(fg_color))
                # self._canvas.itemconfig("border_parts",
                #                         outline=self._apply_appearance_mode(fg_color),
                #                         fill=self._apply_appearance_mode(fg_color))
                if self._state == tkinter.DISABLED:
                    self._canvas.itemconfig("checkmark", fill=self._apply_appearance_mode(self._checkmark_color_disabled))
                else:
                    self._canvas.itemconfig("checkmark", fill=self._apply_appearance_mode(self._checkmark_color))
            else:
                self._canvas.itemconfig("inner_parts",
                                        outline=self._apply_appearance_mode(self._bg_color),
                                        fill=self._apply_appearance_mode(self._bg_color))

            if self._state == tkinter.DISABLED:
                border_color = self._border_color_disabled
            else:
                border_color = self._border_color
            self._canvas.itemconfig("border_parts",
                                    outline=self._apply_appearance_mode(border_color),
                                    fill=self._apply_appearance_mode(border_color))

            if self._state == tkinter.DISABLED:
                self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_disabled)))
            else:
                self._text_label.configure(fg=self._apply_appearance_mode(self._text_color))

            self._text_label.configure(bg=self._apply_appearance_mode(self._bg_color))

    def set(self, value):
        if value == self._onvalue:
            self.select()
        elif value == self._offvalue:
            self.deselect()
        else:
            raise ValueError(f'Failed to set checkbox to unknown value {value}!')

        self.unbind('<Button-1>')

    def configure(self, require_redraw=False, **kwargs):
        if 'text_color_hovered' in kwargs:
            self._text_color_hovered = self._check_color_type(kwargs.pop('text_color_hovered'))
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw, **kwargs)

    def _on_enter(self, event=None):
        self.is_hovered = True
        self._set_cursor()
        if self._state == tkinter.DISABLED:
            return
        super()._on_enter(event)
        self._text_label.configure(fg=self._apply_appearance_mode(self._text_color_hovered))
        self._canvas.itemconfig("border_parts",
                                outline=self._apply_appearance_mode(self._border_color),
                                fill=self._apply_appearance_mode(self._border_color))

    def _on_leave(self, event=None):
        self.is_hovered = False
        self._set_cursor()
        if self._state == tkinter.DISABLED:
            return
        super()._on_leave(event)
        self._text_label.configure(fg=self._apply_appearance_mode(self._text_color))
        self._canvas.itemconfig("border_parts",
                                outline=self._apply_appearance_mode(self._border_color),
                                fill=self._apply_appearance_mode(self._border_color))

    def toggle(self, event=0):
        if not self.is_hovered:
            return
        super().toggle(event)

    def _create_bindings(self, sequence: Optional[str] = None):
        if sequence == "<Button-1>":
            self.bind('<ButtonRelease-1>', self.toggle)
            return
        super()._create_bindings(sequence)

    def _set_cursor(self):
        if self._cursor_manipulation_enabled:
            if not self.is_hovered:
                if sys.platform == "darwin":
                    self._canvas.configure(cursor="arrow")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="arrow")
                elif sys.platform.startswith("win"):
                    self._canvas.configure(cursor="arrow")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="arrow")

            else:
                if sys.platform == "darwin":
                    self._canvas.configure(cursor="pointinghand")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="pointinghand")
                elif sys.platform.startswith("win"):
                    self._canvas.configure(cursor="hand2")
                    if self._text_label is not None:
                        self._text_label.configure(cursor="hand2")


class UIOptionMenu(CTkOptionMenu, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        self._border_width = ThemeManager.theme["CTkTextbox"].get("border_width", 2)
        self._button_color_disabled = ThemeManager.theme["CTkOptionMenu"].get("button_color_disabled", None)
        CTkOptionMenu.__init__(self, master, **kwargs)
        self.dropdown_menu_opened = False
        self.dropdown_menu_close_time = 0

        self._apply_theme()

    def configure(self, require_redraw=False, **kwargs):
        if 'border_width' in kwargs:
            self._border_width = self._check_color_type(kwargs.pop('border_width'))
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw, **kwargs)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        left_section_width = self._current_width - self._current_height
        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border_vertical_split(self._apply_widget_scaling(self._current_width),
                                                                                             self._apply_widget_scaling(self._current_height),
                                                                                             self._apply_widget_scaling(self._corner_radius),
                                                                                             self._apply_widget_scaling(self._border_width),
                                                                                             self._apply_widget_scaling(left_section_width))

        # Drawing Y with CustomTkinter_shapes_font bugs out for some reason, lets hardcode ▼ for now
        requires_recoloring_2 = False

        x_position = self._apply_widget_scaling(self._current_width - (self._current_height / 2))
        y_position = self._apply_widget_scaling(self._current_height / 2)
        size = self._apply_widget_scaling(self._current_height / 3)

        x_position, y_position, size = round(x_position), round(y_position), round(size)

        if not self._canvas.find_withtag("dropdown_arrow"):
            self._canvas.create_text(0, 0, text="▼", font=("Arial", -size), tags="dropdown_arrow",
                                     anchor=tkinter.CENTER)
            self._canvas.tag_raise("dropdown_arrow")
            requires_recoloring = True

        self._canvas.itemconfigure("dropdown_arrow", font=("Arial", -size))
        self._canvas.coords("dropdown_arrow", x_position, y_position)

        if no_color_updates is False or requires_recoloring or requires_recoloring_2:
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

            self._canvas.itemconfig("inner_parts_left",
                                    outline=self._apply_appearance_mode(self._fg_color),
                                    fill=self._apply_appearance_mode(self._fg_color))

            self._text_label.configure(fg=self._apply_appearance_mode(self._text_color))

            if self._state == tkinter.DISABLED:
                self._canvas.itemconfig("inner_parts_right",
                                        outline=self._apply_appearance_mode(self._button_color_disabled or self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color_disabled or self._button_color))
                self._text_label.configure(fg=(self._apply_appearance_mode(self._text_color_disabled)))
                self._canvas.itemconfig("dropdown_arrow",
                                        fill=self._apply_appearance_mode(self._fg_color))
                self._canvas.itemconfig("border_parts",
                                        outline=self._apply_appearance_mode(self._button_color_disabled or self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color_disabled or self._button_color))
            else:
                self._canvas.itemconfig("inner_parts_right",
                                        outline=self._apply_appearance_mode(self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color))
                self._text_label.configure(fg=self._apply_appearance_mode(self._text_color))
                self._canvas.itemconfig("dropdown_arrow",
                                        fill=self._apply_appearance_mode(self._fg_color))
                self._canvas.itemconfig("border_parts",
                                        outline=self._apply_appearance_mode(self._button_color),
                                        fill=self._apply_appearance_mode(self._button_color))

            self._text_label.configure(bg=self._apply_appearance_mode(self._fg_color))


        self._canvas.update_idletasks()

    def _on_leave(self, event=0):
        # set color of inner button parts
        if self._state == tkinter.DISABLED:
            self._canvas.itemconfig("inner_parts_right",
                                    outline=self._apply_appearance_mode(self._button_color_disabled),
                                    fill=self._apply_appearance_mode(self._button_color_disabled))
        else:
            self._canvas.itemconfig("inner_parts_right",
                                    outline=self._apply_appearance_mode(self._button_color),
                                    fill=self._apply_appearance_mode(self._button_color))

    def _clicked(self, event=0):
        if self._state is not tkinter.DISABLED and len(self._values) > 0:
            if not self.dropdown_menu_opened:
                # Adding toggle behaviour to dropdown button is a bit tricky
                # By default, the same click that closes the menu will open it again if dropdown button is clicked
                # Also, as _open_dropdown_menu() is blocking, we can't directly check if menu is shown
                # So we'll use a timer to distinguish closing clicks from opening ones
                # World record is less than 20 CPS (~0.05 between clicks), so 5 times smaller interval should be fine
                if time.time() - self.dropdown_menu_close_time < 0.01:
                    return
                self._open_dropdown_menu()
            else:
                self._close_dropdown_menu()

    def _open_dropdown_menu(self):
        self.dropdown_menu_opened = True
        # Following call is blocking until the menu is closed
        super()._open_dropdown_menu()
        self.dropdown_menu_opened = False
        self.dropdown_menu_close_time = time.time()

    def _close_dropdown_menu(self):
        self._dropdown_menu.unpost()

    def _dropdown_callback(self, value: str):
        super()._dropdown_callback(value)


class UITextbox(CTkTextbox, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 text_variable,
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)

        self._state = tkinter.NORMAL

        self._fg_color_disabled = ThemeManager.theme["CTkTextbox"].get("fg_color_disabled", None)
        self._border_color_disabled = ThemeManager.theme["CTkTextbox"].get("border_color_disabled", None)
        self._text_color_disabled = ThemeManager.theme["CTkTextbox"].get("text_color_disabled", None)

        CTkTextbox.__init__(self, master, **kwargs)

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.config(font=self._apply_font_scaling(('Asap', 14)))
        self.context_menu.add_command(label="Cut")
        self.context_menu.add_command(label="Copy")
        self.context_menu.add_command(label="Paste")

        self.text_variable = text_variable

        self._apply_theme()

        self.trace_write(text_variable, self.handle_text_variable_update)
        self.bind("<Control-KeyPress>", self.handle_key_press)
        self.bind('<KeyRelease>', self.handle_on_widget_change)
        self.bind("<Button-3>", self.handle_button3)

    def configure(self, require_redraw=False, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            self._textbox.configure(state=self._state)
            require_redraw = True

        font = kwargs.get('font', None)
        if font is not None:
            kwargs['font'] = tuple(font)

        super().configure(require_redraw=require_redraw, **kwargs)

    def _draw(self, no_color_updates=False):
        CTkBaseClass._draw(self, no_color_updates)

        if not self._canvas.winfo_exists():
            return

        requires_recoloring = self._draw_engine.draw_rounded_rect_with_border(self._apply_widget_scaling(self._current_width),
                                                                              self._apply_widget_scaling(self._current_height),
                                                                              self._apply_widget_scaling(self._corner_radius),
                                                                              self._apply_widget_scaling(self._border_width))

        if no_color_updates is False or requires_recoloring:
            text_color = self._text_color
            if self._state == tkinter.DISABLED and self._text_color_disabled:
                text_color = self._text_color_disabled

            if self._fg_color == "transparent":
                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(self._bg_color),
                                        outline=self._apply_appearance_mode(self._bg_color))
                self._textbox.configure(fg=self._apply_appearance_mode(text_color),
                                        bg=self._apply_appearance_mode(self._bg_color),
                                        insertbackground=self._apply_appearance_mode(text_color))
                self._x_scrollbar.configure(fg_color=self._bg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)
                self._y_scrollbar.configure(fg_color=self._bg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)
            else:
                fg_color = self._fg_color
                if self._state == tkinter.DISABLED and self._fg_color_disabled:
                    fg_color = self._fg_color_disabled

                self._canvas.itemconfig("inner_parts",
                                        fill=self._apply_appearance_mode(fg_color),
                                        outline=self._apply_appearance_mode(fg_color))
                self._textbox.configure(fg=self._apply_appearance_mode(text_color),
                                        bg=self._apply_appearance_mode(fg_color),
                                        insertbackground=self._apply_appearance_mode(text_color))
                self._x_scrollbar.configure(fg_color=fg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)
                self._y_scrollbar.configure(fg_color=fg_color, button_color=self._scrollbar_button_color,
                                            button_hover_color=self._scrollbar_button_hover_color)

            border_color = self._border_color
            if self._state == tkinter.DISABLED and self._border_color_disabled:
                border_color = self._border_color_disabled

            self._canvas.itemconfig("border_parts",
                                    fill=self._apply_appearance_mode(border_color),
                                    outline=self._apply_appearance_mode(border_color))
            self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))

        self._canvas.tag_lower("inner_parts")
        self._canvas.tag_lower("border_parts")

    def set(self, value):
        self.delete(1.0, END)
        self.insert(END, value)

    def handle_on_widget_change(self, event=None):
        self.text_variable.set(self.get(0.0, END))

    def handle_text_variable_update(self, var, val):
        if val != self.get(0.0, END):
            self.set(val)

    def handle_key_press(self, event):
        if event.keycode == 65 and event.keysym.lower() != 'a':
            event.widget.event_generate("<<SelectAll>>")
        elif event.keycode == 67 and event.keysym.lower() != 'c':
            event.widget.event_generate("<<Copy>>")
        elif event.keycode == 86 and event.keysym.lower() != 'v':
            event.widget.event_generate("<<Paste>>")
        elif event.keycode == 88 and event.keysym.lower() != 'x':
            event.widget.event_generate("<<Cut>>")
        elif event.keycode == 89 and event.keysym.lower() != 'y':
            event.widget.event_generate("<<Redo>>")
        elif event.keycode == 90 and event.keysym.lower() != 'z':
            event.widget.event_generate("<<Undo>>")
        elif event.keycode == 65535:
            event.widget.event_generate("<<Clear>>")

    def handle_button3(self, event=None):
        self.show_context_menu(event)

    def show_context_menu(self, event):
        if self._state != tkinter.DISABLED:
            self.context_menu.post(event.x_root, event.y_root)
            self.context_menu.entryconfigure('Cut', command=lambda: self._textbox.event_generate('<<Cut>>'))
            self.context_menu.entryconfigure('Copy', command=lambda: self._textbox.event_generate('<<Copy>>'))
            self.context_menu.entryconfigure('Paste', command=lambda: self._textbox.event_generate('<<Paste>>'))
