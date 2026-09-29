import os
import webbrowser
import markdown

from dataclasses import dataclass
from typing import Callable, Any
from enum import Enum
from textwrap import dedent
from pathlib import Path

from customtkinter import ThemeManager, Variable
from tkinterweb import HtmlLabel
from mdx_gfm import GithubFlavoredMarkdownExtension

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import gui.vars as Vars

from core.locale_manager import L, Locale, LocaleString
from core.application import Application

from gui.classes.containers import UIFrame, UIScrollableFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox,  UIOptionMenu, UITextbox


MARKDOWN_PARSER = markdown.Markdown(extensions=[GithubFlavoredMarkdownExtension()])


class OptionWidget(Enum):
    CHECKBOX = 0
    DROPDOWN = 1
    BUTTON = 2
    INPUT_STR = 3
    INPUT_INT = 4
    INPUT_FLOAT = 5
    INPUT_TEXT = 6


@dataclass(frozen=True)
class Condition:
    predicate: Callable[[], bool]
    variables: tuple[str, ...] | None = None


@dataclass(frozen=True)
class SettingsOption:
    label_text: str
    widget: OptionWidget
    value_variable: str
    tooltip: str | Callable[[], str] | None = None

    dropdown_values: dict[str, str] | Callable | list[str] | None = None
    dropdown_command: Callable[[str], None] | None = None

    button_text: str | None = None
    button_command: Callable[[], None] | None = None
    button_tooltip: str | None = None

    toggle_variable: str | None = None

    load_if: Condition | None = None
    visible_if: Condition | None = None
    enabled_if: Condition | None = None

    input_button_text: str | None = None
    input_button_command: Callable | None = None
    input_button_tooltip: str | None = None

    value_validate_command: Callable[[], str] | None = None
    on_value_update_command: Callable[[Variable, Any], None] | None = None


@dataclass(frozen=True)
class SettingsSection:
    label_text: str
    options: tuple[SettingsOption, ...]


class SettingsSectionLabel(UILabel):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            **kwargs
        )


class SettingsContentFrame(UIScrollableFrame):
    def __init__(self, master, sections: tuple[SettingsSection, ...]):
        super().__init__(
            master,
            height=510,
            corner_radius=0,
            border_width=0,
            # hide_scrollbar=True,
            fix_grid=True,
            scroll_speed=4.0,
        )

        self._scrollbar.grid_forget()

        self.hide()

        self._scrollbar_hidden_color = master._fg_color
        self.grid_columnconfigure(0, weight=100)

        self._sections = sections

    def render_sections(self):
        # self._render_section()
        for row, section in enumerate(self._sections):
            self._create_section(section, row)
        self._sections = None

    def _render_section(self, row = 0):
        if row >= len(self._sections):
            return
        self._create_section(self._sections[row], row)
        self._render_section(row + 1)
        # self.after_idle(self._render_section, row + 1)

    def _create_section(self, section: SettingsSection, row: int):
        loadable_options = [option for option in section.options if not option.load_if or option.load_if.predicate()]

        if not loadable_options:
            return

        label = SettingsSectionLabel(self, text=section.label_text)
        self.put(label).grid(row=row * 2, column=0, padx=(20, 10), pady=(0, 6), sticky='w')

        frame = SettingsSectionFrame(self, loadable_options, label)
        self.put(frame).grid(row=row * 2 + 1, column=0, padx=(20, 20), pady=(0, 15), sticky='we')


class Separator(UIFrame):
    def __init__(self, master):
        super().__init__(
            border_color=ThemeManager.theme["CTkEntry"].get("border_color", None),
            border_width=1,
            height=1,
            master=master)

        self.grid_columnconfigure(0, weight=100)


class OptionWidgetLabel(UILabel):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            **kwargs
        )


class OptionWidgetErrorLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            master=master,
            text='Unknown error!',
        )

    def _show(self):
        if self.winfo_manager():
            super()._show()


class OptionWidgetLabelButton(UIButton):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            height=36,
            auto_width=True,
            **kwargs
        )


class OptionWidgetValueInputButton(UIButton):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            auto_width=True,
            padx=6,
            height=32,
            **kwargs
        )


class OptionWidgetToggleCheckbox(UICheckbox):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            width=0,
            **kwargs
        )


class OptionWidgetValueCheckbox(UICheckbox):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            width=0,
            **kwargs
        )


class OptionWidgetValueDropdown(UIOptionMenu):
    def __init__(self, master, **kwargs):
        values = kwargs.pop("values", None)

        self.values_getter = None

        if isinstance(values, type) and issubclass(values, Enum):
            kwargs["values"] = {
                item: item.value.relocalize() if isinstance(item.value, LocaleString) else item.value
                for item in values
            }
        elif callable(values):
            self.values_getter = values
        else:
            kwargs["values"] = values

        super().__init__(
            master=master,
            width=140,
            height=36,
            **kwargs,
        )

    def _open_dropdown_menu(self):
        if self.values_getter is not None:
            self.configure(values=self.values_getter())

        super()._open_dropdown_menu()


class OptionWidgetValueInputString(UIEntry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            width=500,
            height=36,
            **kwargs
        )


class OptionWidgetValueInputInteger(UIEntry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            input_filter='INT',
            width=50,
            height=36,
            **kwargs
        )


class OptionWidgetValueInputFloat(UIEntry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            input_filter='FLOAT',
            width=50,
            height=36,
            **kwargs
        )


class OptionWidgetValueInputText(UITextbox):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            height=90,
            undo=True,
            **kwargs
        )

    def get(self, index1, index2=None):
        return super().get(index1, index2).strip()


class OptionWidgetValueButton(UIButton):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            height=36,
            auto_width=True,
            **kwargs
        )


class OptionWidgetInfoButton(UIButton):
    def __init__(self, master, **kwargs):
        super().__init__(
            master=master,
            height=24,
            width=24,
            padx=0,
            text="",
            image_path="MainWindow/LauncherFrame/SettingsFrame/info.webp",
            **kwargs
        )


class InfoFrame(UIFrame):
    def __init__(self, master, info_text: str | Callable[[], str]):
        super().__init__(master=master)

        self._info_text = info_text
        self._info_label = None
        self._toggle_state = False

        # self._render_info_text()

    def toggle(self):
        if not self._info_label:
            self._render_info_text()
        self._toggle_state = not self._toggle_state
        self.show(self._toggle_state)
        if callable(self._info_text) and not self._toggle_state:
            self._info_label.destroy()
            self._info_label = None

    @staticmethod
    def handle_link_click(url):
        if url.startswith('file://'):
            path = Path(url.replace('file:///', ''))
            os.startfile(path)
        else:
            webbrowser.open(url)

    def _render_info_text(self):
        self._info_label = HtmlLabel(
            master=self,
            messages_enabled=False,
            caches_enabled=False,
            textwrap=True,
            fontscale=1.2 * self._apply_widget_scaling(1.0),
            on_link_click=self.handle_link_click,
            events_enabled=True,
        )

        # BUG WORKAROUND: Remove single white pixel from top-left corner.
        # Explicitly placed by tkinterweb bug with `self.motion_frame.place(x=0, y=0)`.
        self._info_label._html.motion_frame_bg = self._fg_color

        # Hack "selectbackground".
        self._info_label._html.selected_text_highlight_color = "#565B5E"
        self._info_label._html.selection_manager.update_tags()

        # Hack "selectforeground".
        self._info_label._html.selected_text_color = "#FFFFFF"
        self._info_label._html.selection_manager.update_tags()

        style: str = dedent(f"""
            <style>
                body {{ font-size: 14px; background-color: {self._fg_color}; color: #E5E5E5; }}
                p  {{ font-family: Segoe UI; margin: 5px;}}
                ul {{ margin: 10px -5px;}}
                li {{ margin: 10px -5px;}}
                h1 {{ font-size: 18px; margin: 10px 5px;}}
                h2 {{ font-size: 16px; margin: 10px 5px;}}
                pre {{ margin: 10px 5px; white-space: normal; width: 100%; }}
                code {{ padding: 4px 4px; line-height: 1.8; background: #2C2E33; border: 1px solid #565B5E; border-radius: 4px;}}
                pre code {{ display: block; margin: 0; padding: 6px 6px; line-height: 1.2; }}
                a {{ color: #84adf3; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        """)

        html = MARKDOWN_PARSER.convert(self._info_text() if callable(self._info_text) else self._info_text)
        html = html.replace("</code></pre>", "&nbsp;</code></pre>")
        self._info_label.load_html(style + f"<html><body>{html}</body></html>")

        self._info_label.pack(anchor="w", padx=5, fill="both", expand=True)


class SettingsOptionFrame(UIFrame):
    def __init__(self, master, option: SettingsOption, separator: Separator):
        super().__init__(master, fg_color='transparent')

        self.grid_columnconfigure(1, weight=1)

        self._separator = separator
        self._visible = True

        if option.widget != OptionWidget.CHECKBOX:
            label = self.put(OptionWidgetLabel(
                self,
                text=option.label_text,
            ))
        else:
            label = None

        widget = self.put(self._create_widget(option))

        pad_left = 7
        pad_right = 7

        # Option Widget
        match option.widget:
            case OptionWidget.CHECKBOX:
                widget.grid(row=0, column=0, padx=(pad_left, 0), pady=(5, 5), sticky='w')

            case OptionWidget.INPUT_STR | OptionWidget.INPUT_TEXT:
                # self.grid_columnconfigure(3, weight=100)

                if not option.toggle_variable:
                    label.grid(row=0, column=0, padx=(pad_left, 0), pady=(5, 5), sticky='w')

                widget.grid(row=1, column=0, padx=(pad_left, pad_right - 3), pady=(5, 5), sticky='we', columnspan=4)

                # Input field inline button.
                if option.input_button_text:
                    input_button = OptionWidgetValueInputButton(
                        master=self,
                        text=option.input_button_text,
                        command=option.input_button_command,
                    )
                    self.put(input_button).grid(row=1, column=0, padx=(pad_left, pad_right + 5), pady=(5, 5), sticky='e', columnspan=4)
                    # Set optional tooltip.
                    if option.input_button_tooltip:
                        input_button.set_tooltip(option.input_button_tooltip)

                # Optional button to the right of input option name.
                if option.button_command:
                    label_button = OptionWidgetLabelButton(
                        master=self,
                        text=option.button_text,
                        command=option.button_command,
                    )
                    self.put(label_button).grid(row=0, column=3, padx=(pad_left, pad_right - 3), pady=(5, 5), sticky='e')
                    # Set optional tooltip.
                    if option.button_tooltip:
                        label_button.set_tooltip(option.button_tooltip)

            case _:
                if not option.toggle_variable:
                    label.grid(row=0, column=0, padx=(pad_left, 0), pady=(5, 5), sticky='w')
                widget.grid(row=0, column=1, padx=(0, pad_right), pady=(5, 5), sticky='e')

        # Optional checkbox-based toggle.
        if option.toggle_variable:
            toggle_variable = self._resolve_variable(option.toggle_variable)
            if option.widget == OptionWidget.CHECKBOX:
                raise ValueError(f"Checkbox option '{option.label_text}' value widget is not compatible with 'toggle_variable'")
            self.put(OptionWidgetToggleCheckbox(
                master=self,
                text=option.label_text,
                variable=toggle_variable,
            )).grid(row=0, column=0, padx=(pad_left, 0), pady=(5, 5), sticky='w')
            self.trace_write(toggle_variable, self.handle_on_toggle_variable)

        # Value Validation
        if option.value_validate_command and option.value_variable:
            error_label = OptionWidgetErrorLabel(
                master=self,
            )
            self.put(error_label)

            if isinstance(widget, OptionWidgetValueDropdown):
                self._normal_color = widget._button_color
            else:
                self._normal_color = widget._border_color

            def validate(*args):
                error_text = option.value_validate_command()
                if error_text:
                    if isinstance(widget, OptionWidgetValueDropdown):
                        widget.configure(button_color="#db3434")
                    else:
                        widget.configure(border_color="#db3434")
                    error_label.configure(text=error_text)
                    error_label.grid(row=2, column=0, padx=0, pady=(0, 5), sticky='we', columnspan=4)
                else:
                    if isinstance(widget, OptionWidgetValueDropdown):
                        widget.configure(button_color=self._normal_color)
                    else:
                        widget.configure(border_color=self._normal_color)
                    error_label.grid_forget()

            self.trace_write(self._resolve_variable(option.value_variable), validate)

        # On Value Update Event
        if option.on_value_update_command and option.value_variable:
            self.trace_write(self._resolve_variable(option.value_variable), option.on_value_update_command)

        # Help Info
        if option.tooltip:
            info_button = OptionWidgetInfoButton(
                master=self,
                command=self._toggle_info,
            )
            self.put(info_button).grid(row=0, column=1, padx=(0, 0), pady=(5, 5), sticky='w')
            self._tooltip = option.tooltip

        self._bind_conditions(option)

    @property
    def is_visible(self):
        return self._visible

    def handle_on_toggle_variable(self, variable, new_value: bool):
        self._set_enabled(new_value)

    def _toggle_info(self):
        info_frame = self.grab(InfoFrame)
        if not info_frame:
            info_frame = InfoFrame(master=self, info_text=self._tooltip)
            self._tooltip = None
            info_frame.hide()
            self.put(info_frame).grid(row=3, column=0, padx=5, pady=(5, 5), sticky='we', columnspan=4)
            info_frame.grid_forget()
        info_frame.toggle()
        self.grab(OptionWidgetInfoButton).set_selected(not info_frame.is_hidden)

    def _create_widget(self, option: SettingsOption):

        variable = self._resolve_variable(option.value_variable) if option.value_variable else None

        match option.widget:
            case OptionWidget.CHECKBOX:
                return OptionWidgetValueCheckbox(
                    self,
                    text=option.label_text,
                    variable=variable,
                )

            case OptionWidget.DROPDOWN:
                return OptionWidgetValueDropdown(
                    self,
                    variable=variable,
                    values=option.dropdown_values or {},
                    command=option.dropdown_command,
                )

            case OptionWidget.INPUT_STR:
                return OptionWidgetValueInputString(
                    self,
                    textvariable=variable,
                )

            case OptionWidget.INPUT_INT:
                return OptionWidgetValueInputInteger(
                    self,
                    textvariable=variable,
                )

            case OptionWidget.INPUT_FLOAT:
                return OptionWidgetValueInputFloat(
                    self,
                    textvariable=variable,
                )

            case OptionWidget.INPUT_TEXT:
                return OptionWidgetValueInputText(
                    self,
                    text_variable=variable,
                )

            case OptionWidget.BUTTON:
                return OptionWidgetValueButton(
                    self,
                    text=option.button_text or option.label_text,
                    command=option.button_command,
                )

            case _:
                raise ValueError(
                    f'Unsupported option widget: {option.widget}'
                )

    def _bind_conditions(self, option: SettingsOption):
        if option.visible_if:
            self._bind_condition(option.visible_if, self._set_visible)

        if option.enabled_if:
            self._bind_condition(option.enabled_if, self._set_enabled)

    def _bind_condition(
        self,
        condition: Condition,
        callback: Callable[[bool], None],
    ):
        def update(*_):
            callback(condition.predicate())

        for variable in condition.variables or ():
            # variable.trace_add('write', update)
            self.trace_write(self._resolve_variable(variable), update)

        update()

    def _set_enabled(self, enabled: bool):
        state = 'normal' if enabled else 'disabled'
        exclude_elements = [
            self.grab(OptionWidgetToggleCheckbox), self.grab(InfoFrame), self.grab(OptionWidgetInfoButton)
        ]
        for element in self.elements.values():
            if element in exclude_elements:
                continue
            element.configure(state=state)

    def _set_visible(self, visible: bool):
        self._visible = visible
        self.show(visible)
        self.master._update_separators()

    @staticmethod
    def _resolve_variable(variable: str):
        obj = Vars

        for part in variable.split(".")[1:]:  # skip "Vars"
            obj = getattr(obj, part)

        return obj


class SettingsSectionFrame(UIFrame):
    def __init__(
        self,
        master,
        options: list[SettingsOption],
        label: SettingsSectionLabel,
    ):
        super().__init__(
            master=master,
        )

        self._label = label

        self.grid_columnconfigure(0, weight=100)

        self._option_frames = []

        for index, option in enumerate(options):
            row = index * 2 + 2

            separator = None
            if index != 0:
                separator = Separator(self)
                self.put(separator).grid(row=row - 1, column=0, padx=(10, 10), pady=(6, 6), sticky='we')

            try:
                frame = SettingsOptionFrame(self, option, separator)
            except Exception as e:
                raise ValueError(f'Failed to create option widget "{option.label_text}"!\n\n{e}')

            self.put(frame).grid(row=row, column=0, padx=10, sticky='we')

            self._option_frames.append(frame)

        # First and last row vertical padding.
        self.grid_rowconfigure(0, minsize=6)
        self.grid_rowconfigure(len(options) * 2 + 1, minsize=6)

        self._update_separators()

    def _update_separators(self):
        found_visible = False

        for frame in self._option_frames:
            if not frame.is_visible:
                if frame._separator:
                    frame._separator.show(False)
                continue

            # Separator is shown only when this isn't
            # the first visible option.
            if frame._separator:
                frame._separator.show(found_visible)

            found_visible = True

        self._label.show(found_visible)

        if found_visible:
            self._show()
        else:
            self._hide()
