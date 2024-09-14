import logging

from typing import Union, Tuple, List, Dict, Optional, Callable
from pathlib import Path

from tkinter import Menu, INSERT
from customtkinter import CTkBaseClass, CTkButton, CTkImage, CTkLabel, CTkProgressBar, CTkEntry, CTkCheckBox, CTkTextbox
from customtkinter import END, CURRENT
from PIL import Image, ImageTk

import core.config_manager as Config

from gui.classes.element import UIElementBase
from gui.classes.windows import UIWindow
from gui.classes.tooltip import UIToolTip

logging.getLogger('PIL').setLevel(logging.INFO)


class UIWidget(UIElementBase):
    def __init__(self, master, **kwargs):
        UIElementBase.__init__(self, **kwargs)
        self.master = master
        # CTkBaseClass.__init__(self, master=master)


class UIText(UIWidget, CTkBaseClass):
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
                 x: int = 0,
                 y: int = 0,
                 **kwargs):
        if 'Asap' in font:
            y -= 1
        self.master = master
        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master,  **kwargs)
        self.fill = fill
        self.activefill = activefill
        self.disabledfill = disabledfill
        self._text_id = master.canvas.create_text(0, 0, fill=fill, activefill=activefill, disabledfill=disabledfill,
                                                     justify=justify, state=state, tags=tags, width=width, font=font, **kwargs)
        self.move(x, y)

    def move(self, x, y):
        x = int(self._apply_widget_scaling(x))
        y = int(self._apply_widget_scaling(y))
        self.master.canvas.coords(self._text_id, x, y)

    def set(self, text: str):
        self.master.canvas.itemconfigure(self._text_id, text=text)

    def _show(self):
        self.master.canvas.itemconfigure(self._text_id, state='normal')

    def _hide(self):
        self.master.canvas.itemconfigure(self._text_id, state='hidden')

    def force_normal(self):
        self.master.canvas.itemconfigure(self._text_id, fill=self.fill)

    def force_active(self):
        self.master.canvas.itemconfigure(self._text_id, fill=self.activefill, activefill=self.activefill)

    def force_disabled(self):
        self.master.canvas.itemconfigure(self._text_id, fill=self.disabledfill, activefill=self.disabledfill)

    def bind(self, *args, **kwargs):
        self.master.canvas.tag_bind(self._text_id, *args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.master.canvas.tag_unbind(self._text_id, *args, **kwargs)


class UIImage(UIWidget, CTkBaseClass):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
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
        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master,  **kwargs)

        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.opacity = None
        self.brightness = None
        self.anchor = None

        self._original_image = None
        self.image = None
        self.image_path = None
        self.image_tag = None

        self.configure(image_path=image_path, x=x, y=y, width=width, height=height, anchor=anchor, opacity=opacity,
                       brightness=brightness, **kwargs)

    def configure(self, **kwargs):
        if self._update_attrs(['image_path'], kwargs):
            self._original_image = Image.open(str(Config.get_resource_path(self) / self.image_path))

        if self._update_attrs(['width', 'height', 'opacity', 'brightness'], kwargs):
            self.image = self.create_image(self._original_image, self.width, self.height, self.opacity, self.brightness)
            if self.image_tag is None:
                self._update_attrs(['x', 'y', 'anchor'], kwargs)
                self.image_tag = self.master.canvas.create_image(self.x, self.y, image=self.image, anchor=self.anchor, **kwargs)
            self.set_image(self.image)

        if self._update_attrs(['x', 'y'], kwargs):
            self.move(self.x, self.y)

        if self._update_attrs(['anchor'], kwargs):
            self.master.canvas.itemconfigure(self.image_tag, anchor=self.anchor)

    def _update_attrs(self, attrs, kwargs):
        attrs_updated = False
        for arg in attrs:
            if arg in kwargs:
                value = kwargs.pop(arg)
                if arg in ['x', 'y']:
                    value = int(self._apply_widget_scaling(value))
                setattr(self, arg,value)
                attrs_updated = True
        return attrs_updated

    def set_image(self, image):
        self.master.canvas.itemconfig(self.image_tag, image=image)

    def create_image(self, image: Image, width, height, opacity: float, brightness: float):
        width = int(self._apply_widget_scaling(width))
        height = int(self._apply_widget_scaling(height))
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
        image = Image.merge(image.mode, output).resize((width, height))
        return ImageTk.PhotoImage(image)

    def move(self, x, y):
        self.master.canvas.coords(self.image_tag, x, y)

    def _show(self):
        self.master.canvas.itemconfigure(self.image_tag, state='normal')

    def _hide(self):
        self.master.canvas.itemconfigure(self.image_tag, state='hidden')

    def bind(self, *args, **kwargs):
        self.master.canvas.tag_bind(self.image_tag, *args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.master.canvas.tag_unbind(self.image_tag, *args, **kwargs)


class UIImageButton(UIWidget, CTkBaseClass):
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
                 **kwargs):

        CTkBaseClass.__init__(self, master=master)
        UIWidget.__init__(self, master,  **kwargs)

        self.master = master
        self.canvas = master.canvas
        self.command = command
        self.disabled = disabled

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
            self._text_image = self.put(UIText(master=master, text=text, font=font, width=0, justify=justify,
                                        x=text_x_offset+x, y=text_y_offset+y, anchor=text_anchor or anchor,
                                        fill=fill, activefill=activefill, disabledfill=disabledfill))

        self.hovered = False
        self.selected = False

        self.bind("<ButtonPress-1>", self._handle_button_press)
        self.bind("<ButtonRelease-1>", self._handle_button_release)
        self.bind("<Enter>", self._handle_enter)
        self.bind("<Leave>", self._handle_leave)

    def set_text(self, text):
        self._text_image.set(text)

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
        self.master.canvas.config(cursor="hand2")
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
        self.master.canvas.config(cursor="")
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


class UILabel(UIWidget, CTkLabel):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 image_path: Optional[Path] = None,
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        self.image: Optional[CTkImage] = None
        if image_path is not None:
            self.image = CTkImage(Image.open(str(Config.get_resource_path(self) / image_path)))
        CTkLabel.__init__(self, master, image=self.image, **kwargs)

    def set(self, value):
        self.configure(text=value)


class UIButton(UIWidget, CTkButton):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 image_path: Optional[Path] = None,
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        self.image: Optional[CTkImage] = None
        if image_path is not None:
            self.image = CTkImage(Image.open(str(Config.get_resource_path(self) / image_path)))
        CTkButton.__init__(self, master, image=self.image, **kwargs)


class UIProgressBar(UIWidget, CTkProgressBar):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        CTkProgressBar.__init__(self, master, **kwargs)


class UIEntry(CTkEntry, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        CTkEntry.__init__(self, master, **kwargs)

        self.state_log = [('', 0)]
        self.state_id = -1

        self.bind("<Key>", self.initialize_state_log)
        self.bind("<KeyRelease>", self.add_state)
        self.bind("<<Cut>>", lambda event: self.after(200, self.add_state))
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Button-3>", self.handle_button3)
        self.bind("<<Paste>>", self.paste_to_selection)

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Cut")
        self.context_menu.add_command(label="Copy")
        self.context_menu.add_command(label="Paste")

    def event_generate(self, *args, **kwargs):
        self._entry.event_generate(*args, **kwargs)

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
        self.initialize_state_log()
        try:
            event.widget.delete('sel.first', 'sel.last')
        except:
            pass
        event.widget.insert('insert', event.widget.clipboard_get())
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
        self.context_menu.post(event.x_root, event.y_root)
        self.context_menu.entryconfigure('Cut', command=lambda: self.event_generate('<<Cut>>'))
        self.context_menu.entryconfigure('Copy', command=lambda: self.event_generate('<<Copy>>'))
        self.context_menu.entryconfigure('Paste', command=lambda: self.event_generate('<<Paste>>'))


class UICheckbox(CTkCheckBox, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        CTkCheckBox.__init__(self, master, **kwargs)

    def set(self, value):
        if value == self._onvalue:
            self.select()
        elif value == self._offvalue:
            self.deselect()
        else:
            raise ValueError(f'Failed to set checkbox to unknown value {value}!')


class UITextbox(CTkTextbox, UIWidget):
    def __init__(self,
                 master: Union[UIWindow, 'UIFrame'],
                 text_variable,
                 **kwargs):
        UIWidget.__init__(self, master,  **kwargs)
        CTkTextbox.__init__(self, master, **kwargs)
        self.text_variable = text_variable
        self.trace_write(text_variable, self.handle_extra_libraries_update)
        self.bind('<KeyRelease>', self.handle_on_widget_change)

    def set(self, value):
        self.delete(1.0, END)
        self.insert(END, value)

    def handle_on_widget_change(self, event=None):
        self.text_variable.set(self.get(0.0, END))

    def handle_extra_libraries_update(self, var, val):
        if val != self.get(0.0, END):
            self.set(val)
