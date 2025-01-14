from typing import Union, Tuple, List, Dict, Optional
from pathlib import Path

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

    def set_background_image(self, image_path: Optional[Path], width: int = 0, height: int = 0,
                             brightness: float = 1, opacity: float = 1, anchor: str = 'nw',
                             x: int = 0, y: int = 0):
        if image_path is not None:
            width, height = width or self.master.winfo_width(), height or self.master.winfo_height()
            if self.background_image is None:
                self.background_image = self.put(UIImage(
                    master=self, image_path=image_path, x=x, y=y, anchor=anchor,
                    width=width, height=height, brightness=brightness, opacity=opacity)
                )
            else:
                self.background_image.configure(image_path=image_path, width=width, height=height)
        elif self.background_image is not None:
            self.background_image.destroy()
            self.background_image = None
        # self.canvas.update()

    def _hide(self):
        if self.background_image is not None:
            self.background_image.hide()
        super()._hide()

    def _show(self):
        if self.background_image is not None:
            self.background_image.show()
        super()._show()

    def get_resource_path(self, resource_path: str = ''):
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


class UIScrollableFrame(CTkScrollableFrame, UIElementBase):
    def __init__(self, master: Union[CTk, CTkToplevel], height, hide_scrollbar=False, **kwargs):
        UIElementBase.__init__(self, **kwargs)
        CTkScrollableFrame.__init__(self, master, height=height, **kwargs)
        # Fix customtkinter bug to allow launcher_frame with less than 200 px height
        self._scrollbar.configure(height=0)
        # Scrollbar auto-hiding
        self.hide_scrollbar = hide_scrollbar
        self.height = height

        self._apply_theme()

    def update(self):
        CTkScrollableFrame.update(self)
        # Automatically hide scrollbar if content fits the height
        if self.hide_scrollbar:
            total_content_height = sum(widget.winfo_height() for widget in self.winfo_children())
            if total_content_height <= round(self._apply_widget_scaling(self.height)):
                self._scrollbar.grid_forget()
            else:
                self._scrollbar.grid()
