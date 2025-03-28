from __future__ import annotations

import logging
import time
import tkinter as tk
import markdown

from textwrap import dedent
from enum import Enum, auto
from typing import Any, Callable, Union
from tkinterweb import HtmlLabel
from mdx_gfm import GithubFlavoredMarkdownExtension


class ToolTipStatus(Enum):
    OUTSIDE = auto()
    INSIDE = auto()
    VISIBLE = auto()


class UIToolTip:
    def __init__(
            self,
            widget: tk.Widget,
            engine: UIToolTipEngine,
            msg: str | list[str] | Callable[[], str | list[str]],
            delay: float = 0.5,
            follow: bool = False,
            refresh: float = 0.0,
            x_offset: int = +0,
            y_offset: int = +10,
            width: int = 800,
            height: int = 600,
            style: str = dedent("""
                <style>
                    html { background-color: #eeeeee;}
                    body { font-size: 14px;}
                    p { font-family: Asap; margin: 5px;}
                    ul { margin: 10px 5px;}
                    li { margin: 10px 5px;}
                    h1 { font-size: 18px; margin: 10px 5px;}
                    h2 { font-size: 16px; margin: 10px 5px;}
                </style>
            """),
    ):
        """Create a ToolTip. Allows for `**kwargs` to be passed on both
            the parent frame and the ToolTip message

        Parameters
        ----------
        widget : tk.Widget
            The widget this ToolTip is assigned to
        msg : `Union[str, Callable]`, optional
            A string message (can be dynamic) assigned to the ToolTip.
            Alternatively, it can be set to a function thatreturns a string,
            by default None
        delay : `float`, optional
            Delay in seconds before the ToolTip appears, by default 0.0
        follow : `bool`, optional
            ToolTip follows motion, otherwise hides, by default True
        refresh : `float`, optional
            Refresh rate in seconds for strings and functions when mouse is
            stationary and inside the widget, by default 1.0
        x_offset : `int`, optional
            x-coordinate offset for the ToolTip, by default +10
        y_offset : `int`, optional
            y-coordinate offset for the ToolTip, by default +10
        """
        self.engine = engine
        self.widget = widget

        self.msg = msg
        self.delay = delay
        self.follow = follow
        self.refresh = refresh
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.style = style
        self.width = width
        self.height = height
        self.scaling = self.widget._apply_widget_scaling(1.0)

        # Visibility status (inside|outside|visible)
        self.status = ToolTipStatus.OUTSIDE
        self.last_moved = 0.0
        self.text = ''

        self.bindings = self._init_bindings()

    def _on_enter(self, event: tk.Event) -> None:
        """
        Processes motion within the widget including entering and moving.
        """
        self.last_moved = time.perf_counter()
        self.status = ToolTipStatus.INSIDE
        self._update_message()
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty()
        # x, y = event.x_root, event.y_root
        self.widget.after(int(self.delay * 1000), self.engine.show, self, x, y)

    def _on_leave(self, event: tk.Event | None = None) -> None:
        """
        Hides the ToolTip.
        """
        self.status = ToolTipStatus.OUTSIDE
        self.engine.hide(self)

    def _on_motion(self, event: tk.Event) -> None:
        """
        Follow the mouse cursor.
        """
        self.engine.move(self, event.x_root, event.y_root)

    def _update_message(self) -> None:
        """
        Update the message displayed in the tooltip.
        """
        if callable(self.msg):
            msg = self.msg()
            if isinstance(msg, list):
                msg = "\n".join(msg)
            else:
                msg = str(msg)
        elif isinstance(self.msg, str):
            msg = self.msg
        elif isinstance(self.msg, list):
            msg = "\n".join(self.msg)
        else:
            msg = str(self.msg)
        self.text = self.engine.markdown_parser.convert(msg)
        # html += '<br/><br/>' + self.engine.markdown_parser.convert(f'```\n{html}\n```')

    def _init_bindings(self) -> list[Binding]:
        """
        Initialize the bindings.
        """
        bindings = [
            Binding(self.widget, "<Enter>", self._on_enter),
            Binding(self.widget, "<Leave>", self._on_leave),
            Binding(self.widget, "<ButtonPress>", self._on_leave),
        ]
        if self.follow:
            bindings.append(
                Binding(self.widget, "<Motion>", self._on_motion)
            )
        return bindings

    # def destroy(self) -> None:
    #     """Destroy the ToolTip and unbind all the bindings."""
    #     with suppress(tk.TclError):
    #         for b in self.bindings:
    #             b.unbind()
    #         self.bindings.clear()
    #         self.widget.destroy()


class Binding:
    def __init__(self, widget: tk.Widget, binding_name: str, functor: Callable) -> None:
        self._widget = widget
        self._name: str = binding_name
        self._id: str = self._widget.bind(binding_name, functor, add="+")

    def unbind(self) -> None:
        self._widget.unbind(self._name, self._id)


class UIToolTipEngine(tk.Toplevel):
    def __init__(self, parent_kwargs: dict | None = None):
        # ToolTip should have the same parent as the widget unless stated otherwise in the `parent_kwargs`
        tk.Toplevel.__init__(self, **(parent_kwargs or {"bg": "black", "padx": 1, "pady": 1}))

        # Hide window until there's tooltip to display
        self.withdraw()
        # Hide title bar
        self.overrideredirect(True)
        # Hide from taskbar
        self.wm_attributes("-toolwindow", True)

        self.markdown_parser = markdown.Markdown(extensions=[GithubFlavoredMarkdownExtension()])

        self.tooltip: Union['UIToolTip', None] = None

        self.message_widget = None
        self.message_text = ''

        self.ready = False

    def clamp_to_root(self, x, y):
        x += int(self.tooltip.x_offset * self.tooltip.scaling)
        y += int(self.tooltip.y_offset * self.tooltip.scaling)
        y += self.tooltip.widget.winfo_height()

        # Clamp tooltip to the root window area
        master_left_edge = self.master.winfo_x()
        master_right_edge = master_left_edge + self.master.winfo_width()
        master_top_edge = self.master.winfo_y()
        master_bottom_edge = master_top_edge + self.master.winfo_height()

        edge_offset = int(10 * self.tooltip.scaling)

        if x < master_left_edge:
            # Do not let tooltip touch the left edge of the root window
            x += master_left_edge - x + edge_offset
        elif x + self.winfo_width() > master_right_edge:
            # Do not let tooltip touch the right edge of the root window
            x -= x + self.winfo_width() - master_right_edge + edge_offset

        tooltip_height = self.winfo_height()

        tooltip_top_edge = y
        # tooltip_bottom_edge = y + tooltip_height

        # Calculate
        available_height = master_bottom_edge - edge_offset - tooltip_top_edge

        if tooltip_height <= available_height:
            # Tooltip fits the space below the widget
            pass
        else:
            # Tooltip doesn't fit the space below the widget
            # Lets place it above the widget instead
            y -= tooltip_height + int(self.tooltip.y_offset * self.tooltip.scaling)
            y -= self.tooltip.widget.winfo_height() + int(self.tooltip.y_offset * self.tooltip.scaling)

        return x, y

    def create_message_widget(self):
        self.ready = False

        # Unfortunately, HtmlLabel cannot be re-used, as it fails to expand to content width
        # Once it's shrunk to some width, it can only be forced to container width, but in breaks auto-shrinking
        # So we'll have to dispose of it and re-create each time
        if self.message_widget is not None:
            self.message_widget.destroy()
            self.message_widget = None
        self.message_widget = HtmlLabel(
            master=self,
            messages_enabled=False,
            caches_enabled=False,
            fontscale=1.2 * self.tooltip.scaling)
        self.message_widget.html.config(
            # Set max width for word wrapping
            width=int(self.tooltip.width * self.tooltip.scaling),
            # Setting height doesn't seem to have any effect
            # height=int(self.tooltip.height * self.tooltip.scaling),
        )
        self.message_widget.load_html(self.message_text)
        self.message_widget.pack()

        # Update tkinter metadata to make message_widget dimensions readable
        self.update()

        self.ready = True

    def show(self, tooltip: 'UIToolTip', x: int, y: int) -> None:
        """
        Displays the ToolTip.
        """
        if tooltip != self.tooltip:
            if self.tooltip is not None:
                self.tooltip.status = ToolTipStatus.OUTSIDE

        self.tooltip = tooltip

        if self.tooltip.status == ToolTipStatus.INSIDE and time.perf_counter() - self.tooltip.last_moved >= self.tooltip.delay:
            self.tooltip.status = ToolTipStatus.VISIBLE

        if self.tooltip.status == ToolTipStatus.VISIBLE:
            # Window must be deiconified if we want to work with dimensions
            # Lets make it transparent for a while instead
            self.wm_attributes('-alpha', 0.0)
            self.deiconify()

            message_text = self.tooltip.style + self.tooltip.text

            # Redraw text widget if message is updated
            if self.message_text != message_text:
                self.message_text = message_text
                self.create_message_widget()
            elif not self.ready:
                return

            # Move window to target location
            self.move(self.tooltip, x, y)

            # Window is ready to be displayed
            self.wm_attributes('-alpha', 1.0)

            # Recursively call _show to update ToolTip with the newest value of msg
            # This is a race condition which only exits when upon a binding change
            # that in turn changes the `status` to outside
            if self.tooltip.refresh > 0:
                self.after(int(self.tooltip.refresh * 1000), self.show, tooltip, x, y)

    def hide(self, tooltip: 'UIToolTip'):
        self.after(100, self._hide)

    def _hide(self):
        if self.tooltip is not None and self.tooltip.status == ToolTipStatus.OUTSIDE:
            self.withdraw()

    def move(self, tooltip: 'UIToolTip', x: int, y: int) -> None:
        """
        Updates the ToolTip's position.
        """
        if tooltip != self.tooltip:
            return
        x, y = self.clamp_to_root(x, y)
        self.geometry(f"+{x}+{y}")
