from __future__ import annotations

import logging
import time
import tkinter as tk
import markdown

from textwrap import dedent
from enum import Enum, auto
from typing import Any, Callable
from contextlib import suppress
from tkinterweb import HtmlLabel
from mdx_gfm import GithubFlavoredMarkdownExtension

markdown_parser = markdown.Markdown(extensions=[GithubFlavoredMarkdownExtension()])


class ToolTipStatus(Enum):
    OUTSIDE = auto()
    INSIDE = auto()
    VISIBLE = auto()


class Binding:
    def __init__(self, widget: tk.Widget, binding_name: str, functor: Callable) -> None:
        self._widget = widget
        self._name: str = binding_name
        self._id: str = self._widget.bind(binding_name, functor, add="+")

    def unbind(self) -> None:
        self._widget.unbind(self._name, self._id)


class ToolTip(tk.Toplevel):
    """
    Creates a ToolTip (pop-up) widget for tkinter
    """

    DEFAULT_PARENT_KWARGS = {"bg": "black", "padx": 1, "pady": 1}
    DEFAULT_MESSAGE_KWARGS = {"aspect": 1000}
    S_TO_MS = 1000

    def __init__(
        self,
        widget: tk.Widget,
        msg: str | list[str] | Callable[[], str | list[str]],
        delay: float = 0.0,
        follow: bool = True,
        refresh: float = 0.0,
        scaling: float = 1.0,
        x_offset: int = +10,
        y_offset: int = +10,
        style: str = '',
        parent_kwargs: dict | None = None,
        anchor: str = 'ne',
        **message_kwargs: Any,
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
        parent_kwargs : `dict`, optional
            Optional kwargs to be passed into the parent frame,
            by default `{"bg": "black", "padx": 1, "pady": 1}`
        **message_kwargs : tkinter `**kwargs` passed directly into the ToolTip
        """
        self.x = 0
        self.y = 0
        self.scaling = scaling or 1.0
        self.widget = widget
        # ToolTip should have the same parent as the widget unless stated
        # otherwise in the `parent_kwargs`
        tk.Toplevel.__init__(self, **(parent_kwargs or self.DEFAULT_PARENT_KWARGS))
        self.withdraw()  # Hide initially in case there is a delay
        # Disable ToolTip's title bar
        self.overrideredirect(True)

        # self.geometry(f'100x50')

        # StringVar instance for msg string|function
        # self.msg_var = tk.StringVar()
        self.msg = msg
        # self._update_message()
        self.delay = delay
        self.follow = follow
        self.refresh = refresh
        self.x_offset = x_offset
        self.y_offset = y_offset
        # visibility status of the ToolTip inside|outside|visible
        self.status = ToolTipStatus.OUTSIDE
        self.last_moved = 0.0
        # use Message widget to host ToolTip
        self.message_kwargs: dict = self.DEFAULT_MESSAGE_KWARGS.copy()
        self.message_kwargs.update(message_kwargs)
        self.style = style
        self.cursor_anchor = anchor

        # self.message_widget = tk.Message(
        #     self,
        #     textvariable=self.msg_var,
        #     **self.message_kwargs,
        # )

        self.message_widget = HtmlLabel(self, messages_enabled=False, height=5)

        # self.message_widget.pack(fill="both", expand=True)

        self.message_widget.grid()

        self.bindigs = self._init_bindings()

    def _init_bindings(self) -> list[Binding]:
        """Initialize the bindings."""
        bindings = [
            Binding(self.widget, "<Enter>", self.on_enter),
            Binding(self.widget, "<Leave>", self.on_leave),
            Binding(self.widget, "<ButtonPress>", self.on_leave),
        ]
        if self.follow:
            bindings.append(
                Binding(self.widget, "<Motion>", self._update_tooltip_coords)
            )
        return bindings

    def destroy(self) -> None:
        """Destroy the ToolTip and unbind all the bindings."""
        with suppress(tk.TclError):
            for b in self.bindigs:
                b.unbind()
            self.bindigs.clear()
            super().destroy()

    def on_enter(self, event: tk.Event) -> None:
        """
        Processes motion within the widget including entering and moving.
        """
        self.last_moved = time.perf_counter()
        self.status = ToolTipStatus.INSIDE
        self._update_tooltip_coords(event)
        self.after(int(self.delay * self.S_TO_MS), self._show)

    def on_leave(self, event: tk.Event | None = None) -> None:
        """
        Hides the ToolTip.
        """
        self.status = ToolTipStatus.OUTSIDE
        self.withdraw()

    def _update_tooltip_coords(self, event: tk.Event) -> None:
        """
        Updates the ToolTip's position.
        """
        x = event.x_root + int(self.x_offset * self.scaling)
        y = event.y_root + int(self.y_offset * self.scaling)
        if self.x == self.y == 0:
            self.geometry(f"+{self.x}+{self.y}")
        self.x = x
        self.y = y

    def place_tooltip(self) -> None:
        x = self.x
        y = self.y
        screen_width = int(self.winfo_screenwidth() * self.scaling)
        screen_height = int(self.winfo_screenheight() * self.scaling)
        if self.cursor_anchor == 'sw':
            y -= self.winfo_height() + int(self.y_offset * self.scaling * 2)
        # Clamp tooltip to screen area
        x_offset = x + self.winfo_width() - screen_width + 42
        if x_offset > 0:
            x -= x_offset
        if self.cursor_anchor == 'nw':
            y_offset = y + self.winfo_height() - screen_height + 42
            if y_offset > 0:
                y -= y_offset
        # Update tooltip coords
        self.geometry(f"+{x}+{y}")

    def _update_message(self) -> None:
        """Update the message displayed in the tooltip."""
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
        html = markdown_parser.convert(msg)
        # html += '<br/><br/>' + markdown_parser.convert(f'```\n{html}\n```')
        self.message_widget.load_html(self.style + html)

    def _show(self) -> None:
        """
        Displays the ToolTip.

        Recursively queues `_show` in the scheduler every `self.refresh` seconds
        """
        if (
            self.status == ToolTipStatus.INSIDE
            and time.perf_counter() - self.last_moved >= self.delay
        ):
            self.status = ToolTipStatus.VISIBLE

        if self.status == ToolTipStatus.VISIBLE:
            self._update_message()
            self.deiconify()
            self.update()
            self.place_tooltip()
            # Recursively call _show to update ToolTip with the newest value of msg
            # This is a race condition which only exits when upon a binding change
            # that in turn changes the `status` to outside
            if self.refresh > 0:
                self.after(int(self.refresh * self.S_TO_MS), self._show)


class UIToolTip(ToolTip):
    def __init__(self, master, **kwargs):
        default = {
            'delay': 0.5,
            'follow': True,
            'y_offset': 20,
            'parent_kwargs': {
                "bg": "black",
                "padx": 1,
                "pady": 1
            },
            'scaling': master._CTkScalingBaseClass__widget_scaling,
            'style': dedent("""
                <style>
                    p { font-family: Asap; margin: 5px;}
                    ul { margin: 10px 5px;}
                    li { margin: 10px 5px;}
                    h1 { font-size: 18px; margin: 10px 5px;}
                    h2 { font-size: 16px; margin: 10px 5px;}
                </style>
            """)
        }
        default.update(kwargs)

        ToolTip.__init__(self, master, **default)
        self.message_widget.set_fontscale(1.2 * master._CTkScalingBaseClass__widget_scaling)
