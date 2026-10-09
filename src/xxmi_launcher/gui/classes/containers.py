from typing import Union, Tuple, List, Dict, Optional
from pathlib import Path

from PIL import Image

from tkinter import TclError
from customtkinter import CTk, CTkToplevel, CTkBaseClass, CTkFrame, CTkCanvas, CTkTabview, CTkScrollableFrame

from gui.classes.element import UIElementBase
from gui.classes.widgets import UIImage


class UIFrame(UIElementBase, CTkFrame):
    def __init__(self, master: Union[CTk, CTkToplevel, CTkFrame], canvas: CTkCanvas = None, width=0, height=0, highlightthickness=0, **kwargs):
        UIElementBase.__init__(self, **kwargs)
        CTkFrame.__init__(self, master, width=width, height=height, **kwargs)

        if canvas is not None:
            self.canvas = canvas
        else:
            width = int(self._apply_widget_scaling(width))
            height = int(self._apply_widget_scaling(height))
            self.canvas = canvas or CTkCanvas(self, width=width, height=height, highlightthickness=highlightthickness)

        self.background_image = None

        self._apply_theme()

    def update(self):
        # CTkFrame.update(self)
        # self.canvas.configure(width=self.master.winfo_width(), height=self.master.winfo_height())
        # cols, rows = self.grid_size()
        # self.canvas.grid(row=0, column=0, columnspan=cols, rowspan=rows, sticky='news')
        pass

    def set_background_image(
        self,
        image_path: Optional[Union[Path, Image]] = None,
        width: int = 0,
        height: int = 0,
        brightness: float = 1,
        opacity: float = 1,
        anchor: str = 'nw',
        x: int = 0,
        y: int = 0,
        fg_color = None,
        border_radius = 0,
        border_width = 0,
        border_color = None,
        dim_opacity: float = 0,
        secondary_fill_color=None,
        split=0.5,
        split_direction="vertical",
        anim_start_delay=0,
    ):

        if image_path is not None or fg_color or border_radius:
            width, height = width or self.master.winfo_width(), height or self.master.winfo_height()
            if self.background_image is None:

                padx, pady = None, None
                if dim_opacity > 0:
                    padx = (self.winfo_toplevel().cfg.width - width) / 2
                    pady = (self.winfo_toplevel().cfg.height - height) / 2

                self.background_image = self.put(UIImage(
                    master=self, image_path=image_path, x=x, y=y, anchor=anchor,
                    width=width, height=height, brightness=brightness, opacity=opacity,
                    fg_color=fg_color, border_radius=border_radius, border_width=border_width, border_color=border_color,
                    padx=padx, pady=pady, bg_opacity=dim_opacity,
                    secondary_fill_color=secondary_fill_color, split=split, split_direction=split_direction,
                    anim_start_delay=anim_start_delay,
                ))
            else:
                self.background_image.configure(image_path=image_path, width=width, height=height)
        elif self.background_image is not None:
            self.background_image.destroy()
            self.background_image = None

    def _hide(self):
        if self.background_image is not None:
            self.background_image.hide()
        super()._hide()

    def _show(self):
        if self.background_image is not None:
            self.background_image.show()
        super()._show()

    def get_resource_path(self, resource_path: str = ''):
        if self.resource_override is not None:
            return self.resource_override
        resource_path = self.master.get_resource_path()
        return f'{resource_path}/{str(self.__class__.__qualname__)}'

    def bind(self, *args, **kwargs):
        if self.background_image is not None:
            self.background_image.bind(*args, **kwargs)
        else:
            super().bind(*args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.background_image.unbind(*args, **kwargs)


class UITabView(UIElementBase, CTkTabview):
    def __init__(self, master: Union[CTk, CTkToplevel, CTkFrame], **kwargs):
        UIElementBase.__init__(self, **kwargs)
        CTkTabview.__init__(self, master, **kwargs)

        self._apply_theme()

    def rename_tab(self, old_name, new_name, keep_old_key=False):
        self._segmented_button._buttons_dict[old_name].configure(text=new_name)
        if not keep_old_key:
            self._segmented_button._buttons_dict[new_name] = self._segmented_button._buttons_dict[new_name]
            del self._segmented_button._buttons_dict[new_name]

_CTK_SCROLLABLE_FRAME_GLOBAL_BINDINGS = {
    "<MouseWheel>",
    "<KeyPress-Shift_L>",
    "<KeyPress-Shift_R>",
    "<KeyRelease-Shift_L>",
    "<KeyRelease-Shift_R>",
}

class UIScrollableFrame(CTkScrollableFrame, UIElementBase):
    def __init__(
        self,
        master: Union[CTk, CTkToplevel],
        height,
        hide_scrollbar: bool = False,
        fix_grid: bool = False,
        scroll_speed: float = 1.0,
        **kwargs
    ):
        UIElementBase.__init__(self, **kwargs)

        # Must exist BEFORE CTkScrollableFrame.__init__(), because
        # CTkScrollableFrame.__init__() calls self.bind_all().
        self._captured_bindings = []
        self._capture_bindings = True

        try:
            CTkScrollableFrame.__init__(self, master, height=height, **kwargs)
        finally:
            self._capture_bindings = False

        # Fix customtkinter bug to allow launcher_frame with less than 200 px height
        self._scrollbar.configure(height=0)
        # Scrollbar auto-hiding
        self.hide_scrollbar = hide_scrollbar
        self.height = height

        self._original_button_color = None
        self._original_button_hover_color = None

        self._scrollbar_hidden = False
        self._scrollbar_hidden_color = None

        self._scroll_speed = scroll_speed

        self._apply_theme()

        # Call grid manager to workaround customtkinter bug that causes content to overlap with scrollbar
        if fix_grid:
            self.grid()

    def bind_all(self, sequence=None, func=None, add=None):
        """
        CUSTOMTKINTER BUGFIX: Capture list of bindings and unbind them later during `destroy` to prevent leaking.
        """
        funcid = super().bind_all(sequence, func, add)

        if getattr(self, "_capture_bindings", False) and sequence in _CTK_SCROLLABLE_FRAME_GLOBAL_BINDINGS:
            self._captured_bindings.append((sequence, funcid))

        return funcid

    def destroy(self):
        """
        CUSTOMTKINTER BUGFIX: Unbind capture list of bindings to prevent leaking.
        Remove CTkScrollableFrame's bind_all() callbacks before destroying the widget hierarchy.
        """
        # root = self._root()
        for sequence, funcid in self._captured_bindings:
            try:
                # bind_all() uses the special Tcl bind tag "all".
                # tkinter has no public API for removing only one bind_all() callback, so use its internal _unbind().
                self._unbind(("bind", "all", sequence), funcid)
                # root.unbind(sequence, funcid)
            except TclError:
                # The Tcl binding may already have disappeared.
                pass

        self._captured_bindings.clear()

        super().destroy()

    def _notify_scroll_activity(self):
        widget = self

        while widget is not None:
            callback = getattr(widget, '_on_scroll_activity', None)

            if callback is not None:
                callback()
                return

            try:
                widget = widget.master
            except Exception:
                return

    def _mouse_wheel_all(self, event):
        self._notify_scroll_activity()
        event.delta = event.delta * self._scroll_speed
        # CUSTOMTKINTER BUG WORKAROUND: Ignore scroll errors.
        # While custom `bind_all` and `destroy` implement bugfix, let's leave it here for safety.
        try:
            super()._mouse_wheel_all(event)
        except Exception:
            pass

    def scroll_y_pixels(self, pixels: int):
        canvas = self._parent_canvas

        first, _ = canvas.yview()
        scrollregion = canvas.cget("scrollregion")

        if not scrollregion:
            return

        _, y1, _, y2 = map(float, scrollregion.split())
        scroll_height = y2 - y1

        if scroll_height <= 0:
            return

        canvas_height = canvas.winfo_height()
        max_scroll = max(0, scroll_height - canvas_height)

        if max_scroll <= 0:
            return

        new_position = first + pixels / max_scroll
        new_position = max(0.0, min(1.0, new_position))

        canvas.yview_moveto(new_position)

    def update(self):
        CTkScrollableFrame.update(self)
        # Automatically hide scrollbar if content fits the height
        if self.hide_scrollbar:
            if not self._parent_frame._fg_color or self._parent_frame._fg_color == 'transparent':
                return
            total_content_height = sum(widget.winfo_height() for widget in self.winfo_children())
            if total_content_height <= round(self._apply_widget_scaling(self.height)):
                # self._scrollbar.grid_forget()
                if self._scrollbar_hidden_color is None:
                    self._scrollbar_hidden_color = self._parent_frame._fg_color
                self._original_button_color = self._scrollbar._button_color
                self._original_button_hover_color = self._scrollbar._button_hover_color
                self._scrollbar.configure(
                    button_color=self._scrollbar_hidden_color,
                    button_hover_color=self._scrollbar_hidden_color,
                )
                self._scrollbar_hidden = True
            else:
                # self._scrollbar.grid()
                if self._original_button_color is not None:
                    self._scrollbar.configure(
                        button_color=self._original_button_color,
                        button_hover_color=self._original_button_hover_color,
                    )
                    self._scrollbar_hidden = False

    def check_if_master_is_canvas(self, widget):
        if widget is None:
            return False
        if isinstance(widget, str):
            return True
        return super().check_if_master_is_canvas(widget)

    def get_resource_path(self, resource_path: str = ''):
        if self.resource_override is not None:
            return self.resource_override
        resource_path = self.master.master.master.get_resource_path()
        return f'{resource_path}/{str(self.__class__.__qualname__)}'

    def _show(self):
        super()._show()

