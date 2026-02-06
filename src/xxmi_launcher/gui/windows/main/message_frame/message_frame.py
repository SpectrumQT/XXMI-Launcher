import logging
import re
import webbrowser
import markdown

from typing import List, Optional
from textwrap import dedent
from mdx_gfm import GithubFlavoredMarkdownExtension
from customtkinter import IntVar, BooleanVar
from tkinterweb import HtmlLabel, HtmlFrame
from PIL import Image, ImageDraw, ImageTk

import core.config_manager as Config
import core.event_manager as Events
import gui.vars as Vars

from core.locale_manager import L
from gui.classes.containers import UIFrame, UIScrollableFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox,  UIOptionMenu
from gui.classes.widgets import UIText, UIImageButton


markdown_parser = markdown.Markdown(extensions=[GithubFlavoredMarkdownExtension()])


class MessageFrame(UIFrame):
    def __init__(self, master, canvas, icon='info-icon.ico', title='Message', message='< Text >',
                 confirm_text='OK', confirm_command=None, cancel_text='', cancel_command=None,
                 radio_options: Optional[List[str]] = None, lock_master=True, screen_center=False):
        super().__init__(master=master, canvas=canvas)

        self.radio_var = None
        self.response = None

        self._offset_x = 0
        self._offset_y = 0

        min_width = 400
        max_width = 600

        min_height = 100
        max_height = 310

        min_button_width = 100

        self.content_frame = ContentFrame(self, message, radio_options, min_width, max_width, min_height, max_height)

        self.update()

        content_width = int(self.content_frame.message_widget.winfo_width() / self._apply_widget_scaling(1.0))
        content_height = int(self.content_frame.message_widget.winfo_height() / self._apply_widget_scaling(1.0))

        self.update()

        if content_width < min_width:
            target_width = min_width + 20 + int(self._apply_widget_scaling(10))
            content_width = min_width
        # elif content_width > max_width:
        #     target_width = max_width + 20 + int(self._apply_widget_scaling(10))
        #     content_width = max_width
        else:
            target_width = content_width + 35 + int(self._apply_widget_scaling(10))

        if content_height < min_height:
            target_height = min_height + 120
        elif content_height > max_height:
            target_height = max_height + 120
        else:
            target_height = content_height + 120

        self.set_background_image(width=target_width, height=target_height,
                                  x=640, y=360, anchor='c', brightness=1.0, opacity=1.0,
                                  fg_color='#1f2024', border_radius=20, border_width=1, border_color='gray',
                                  dim_opacity=0.5)

        title_x = master.master.cfg.width / 2 - target_width / 2 + 25
        title_y = master.master.cfg.height / 2 - target_height / 2 + 20
        self.message_title = self.put(MessageTitleText(self, title, -1000, -1000))

        x = master.master.cfg.width / 2 + target_width / 2 - 25
        y = master.master.cfg.height / 2 - target_height / 2 + 25
        self.close_button = self.put(CloseButton(self, x, y))

        confirm_width, cancel_width = 0, 0

        if confirm_text:
            button = ConfirmButton(self, confirm_text, confirm_command, -1000, -1000, min_button_width)
            confirm_width = button._width
            button.destroy()

        if cancel_text:
            button = CancelButton(self, cancel_text, cancel_command, -1000, -1000, min_button_width)
            cancel_width = button._width
            button.destroy()

        buttons_count = 2 if confirm_text and cancel_text else 1
        button_width = max(confirm_width, cancel_width) + 60
        button_width = max(min_button_width, button_width)

        if confirm_text:
            # x=890 if two_buttons_mode else 640
            confirm_x = master.master.cfg.width / 2 + target_width / 2 - button_width / 2 - 20
            confirm_y = master.master.cfg.height / 2 + target_height / 2 - 35
            self.confirm_button = self.put(ConfirmButton(self, confirm_text, confirm_command, confirm_x, confirm_y, button_width))

        if cancel_text:
            offset = 0
            if buttons_count == 2:
                offset = button_width + 20
            # x=390 if two_buttons_mode else 640
            cancel_x = master.master.cfg.width / 2 + target_width / 2 - button_width / 2 - 20 - offset
            cancel_y = master.master.cfg.height / 2 + target_height / 2 - 35
            self.cancel_button = self.put(CancelButton(self, cancel_text, cancel_command, cancel_x, cancel_y, button_width))

        self.put(self.content_frame).pack()

        scrollbar_width = 0
        if self.content_frame._scrollbar.grid_info():
            scrollbar_width = self.content_frame._scrollbar._current_width
        content_frame_width = 6 + content_width + scrollbar_width

        self.message_title.move(int(1280/2 - content_frame_width/2 + 7 + 7/self._apply_widget_scaling(1.0)), title_y)


        self.place(relx=0.5, rely=0.5, anchor='c')

        self.background_image.bind('<Button-1>', self._handle_button_press)
        self.background_image.bind('<B1-Motion>', self._handle_mouse_move)

    def _handle_button_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _handle_mouse_move(self, event):
        Events.Fire(Events.Application.MoveWindow(offset_x=self._offset_x, offset_y=self._offset_y))

    def set_content(self, model_importer = 'WWMI', num_sessions = 0, mode = 'NORMAL'):
        pass

    def close(self):
        self.destroy()


class MessageTitleText(UIText):
    def __init__(self, master, text: str, x, y):
        super().__init__(x=x,
                         y=y,
                         text=text,
                         font=('Microsoft YaHei', 26, 'bold'),
                         fill='white',
                         activefill='white',
                         anchor='nw',
                         master=master)


class ConfirmButton(UIImageButton):
    def __init__(self, master, text: str, command, x, y, width):
        super().__init__(
            x=x,
            y=y,
            # width=225,
            # height=40,
            bg_width=width,
            bg_height=36,
            text=text,
            fg_color='white',
            border_radius=10,
            # border_width=1,
            # border_color='yellow',
            # text_x_offset=36,
            text_y_offset=-1,
            text_anchor='center',
            font=('Roboto', 20),
            # button_image_path='button-close-background.png',
            bg_normal_opacity=0.85,
            bg_hover_opacity=1,
            bg_selected_opacity=1,
            bg_disabled_opacity=0.75,
            disabledfill='#808080',
            command=lambda: self.confirm(command),
            anchor='center',
            master=master)

    def confirm(self, confirm_command):
        if confirm_command is not None:
            confirm_command()
        self.master.response = True
        self.master.close()


class CancelButton(UIImageButton):
    def __init__(self, master, text: str, command, x, y, width):
        super().__init__(
            x=x,
            y=y,
            # width=225,
            # height=40,
            bg_width=width,
            bg_height=36,
            text=text,
            fg_color='#1f2024',
            border_radius=10,
            border_width=1,
            border_color='white',
            # text_x_offset=36,
            text_y_offset=-1,
            text_anchor='center',
            font=('Roboto', 20),
            # button_image_path='button-close-background.png',
            bg_normal_opacity=0.85,
            bg_hover_opacity=1,
            bg_selected_opacity=1,
            bg_disabled_opacity=0.75,
            fill='#dddddd',
            activefill='#ffffff',
            disabledfill='#808080',
            command=lambda: self.cancel(command),
            anchor='center',
            master=master)

    def cancel(self, cancel_command):
        if cancel_command is not None:
            cancel_command()
        self.master.response = False
        self.master.close()


class CloseButton(UIImageButton):
    def __init__(self, master, x, y):
        super().__init__(
            x=x,
            y=y,
            width=18,
            height=18,
            button_image_path='button-system-close.png',
            button_normal_opacity=0.8,
            button_hover_opacity=1,
            button_selected_opacity=1,
            bg_image_path='button-system-background.png',
            bg_width=24,
            bg_height=24,
            bg_normal_opacity=0,
            bg_hover_opacity=0.1,
            bg_selected_opacity=0.2,
            command=self.close,
            master=master)

    def close(self):
        self.master.close()


class ContentFrame(UIScrollableFrame):
    def __init__(self, master, message: str, radio_options: Optional[List[str]] = None,
                 min_width: int = 480, max_width: int = 600, min_height: int = 180, max_height: int = 260):
        super().__init__(master, width=max_width, height=max_height, hide_scrollbar=True)

        self.configure(fg_color='#1f2024')
        # self.configure(fg_color='green')

        self.message_widget = HtmlFrame(
            master=self,
            messages_enabled=False,
            caches_enabled=False,
            width=max_width,
            height=max_height,
            fontscale=1.2 * self._apply_widget_scaling(1.0),
            shrink=True,
            textwrap=True,
            on_link_click=self.open_in_browser,
            events_enabled=True,
        )

        # self.message_widget.html.config(
        #     # Set max width for word wrapping
        #     width=int(self.width * self.widget._apply_widget_scaling(1.0)),
        #     # Setting height doesn't seem to have any effect
        #     # height=int(self.tooltip.height * self.tooltip.scaling),
        # )

        style = self.get_style()
        # html = self.get_html()

        html = markdown_parser.convert(str(message))

        radio_widget = None
        if radio_options is not None:
            master.radio_var = IntVar(master=master, value=0)
            radio_widget = RadioWidget(self.message_widget, radio_options, master.radio_var)
            style += radio_widget.get_style()
            if '{radio_widget}' in html:
                html = html.replace('{radio_widget}', radio_widget.get_html())
            else:
                html += radio_widget.get_html()

        html = html.replace("\\", "/")

        html = f"<html>\n{style}\n<body>\n{html}\n</body>\n</html>"

        html = self.insert_space_in_long_words_multiline(html, 64)

        # loaded = BooleanVar(value=False)
        #
        # def on_load(event=None):
        #     loaded.set(True)
        #
        # self.message_widget.bind("<<DoneLoading>>", on_load)

        self.message_widget.load_html(html)

        if radio_widget is not None:
            radio_widget.setup_callbacks()

        # self.wait_variable(loaded)

        self.message_widget.pack()

        self.update()

        message_width = int(self.message_widget.winfo_width() / self._apply_widget_scaling(1.0))
        message_height = int(self.message_widget.winfo_height() / self._apply_widget_scaling(1.0))

        if message_width < min_width:
            self.configure(width=min_width)
        # elif message_width > max_width:
        #     self.configure(width=max_width)
        else:
            self.configure(width=message_width)

        if message_height < min_height:
            self.configure(height=min_height)
        elif message_height > max_height:
            self.configure(height=max_height)
        else:
            self.configure(height=message_height)

        self.update()

        self.message_widget.pack(fill="both", expand=True)

        self.update()

        # self.message_widget.place(x=0, y=0, width=800, height=500)
        # self.message_widget.place(x=150, y=150)

    @staticmethod
    def insert_space_in_long_words_multiline(text, max_len):
        def process_word(word):
            if len(word) <= max_len:
                return word
            parts = [word[i:i + max_len] for i in range(0, len(word), max_len)]
            return ' '.join(parts)

        tokens = re.findall(r'\S+|\s+', text)
        processed = [process_word(t) if not t.isspace() else t for t in tokens]
        return ''.join(processed)

    #  html { background-color: #1f2024;}
    def get_style(self):
        return dedent("""
            <style>
                html { background-color: #1f2024;}
                body { font-size: 18px; color: #ffffff}
                p { font-family: Asap; margin: 10px 0px;}
                ul { margin: 10px 0px;}
                li { margin: 10px 0px;}
                h1 { font-size: 18px; margin: 10px 0px;}
                h2 { font-size: 16px; margin: 10px 0px;}
            </style>
        """)

    def get_html(self):
        return ''

    def open_in_browser(self, url):
        webbrowser.open(url)

    def get_selected_radio(self):
        selected_value = self.message_widget.evaljs("""
            (function() {
                const radios = document.getElementsByName("fruit");
                for (let i = 0; i < radios.length; i++) {
                    if (radios[i].checked) {
                        return radios[i].id;
                    }
                }
                return null;
            })();
        """)
        print("Selected radio ID:", selected_value)

    def hide(self, hide=True):
        super().hide(hide=hide)

    def destroy(self):
        self.message_widget.unbind_all('<MouseWheel>')
        self.message_widget.unbind_all('<Button-4>')
        self.message_widget.unbind_all('<Button-5>')
        self.message_widget.destroy()
        self.message_widget = None


class RadioWidget:
    def __init__(self, frame: HtmlFrame, options: List[str], radio_var: IntVar):
        self.frame: HtmlFrame = frame
        self.options: List[str] = options
        self.selected_option = 0
        self.hovered_option = 0
        self.radio_var = radio_var

    def get_style(self):
        return dedent(f"""
            <style>
            label {{
              cursor: pointer;
              padding: 0px;
            }}
            input[type="radio"] {{
              cursor: pointer;
              margin: 0px; 
              padding-bottom: 5px; 
              transform: scale(4);
              accent-color: #007bff;
            }}
            </style>
        """)

        # input[type="radio"] {{
        #   margin-right: 6px;
        # }}

    def get_html(self):
        return dedent(f"""
            <form id="radio_widget">
            {
                "<br>\n".join([
                    dedent(f'''
                    <div>
                    <input type="radio" name="radio_widget_buttons" id="radio_button_{str(i)}" value="{str(i)}"{" checked" if i == 0 else ""}>
                    <label id="radio_label_{str(i)}" for="radio_button_{str(i)}"> {option}</label>
                    </div>
                    ''') for i, option in enumerate(self.options)
                ])
            }
            </form>
        """)

    def make_radio_label_hover_callback(self, idx):
        def callback(event):
            self.hovered_option = idx
            # print(f'hovered {self.hovered_option}')
        return callback

    def make_radio_label_callback(self, idx):
        def callback(event):
            button = self.frame.document.getElementById(f"radio_button_{idx}")
            button.checked = True
            self.selected_option = idx
            self.radio_var.set(self.selected_option)
            # print(f'label {idx}')
        return callback

    def make_radio_button_hover_callback(self, idx):
        def callback(event):
            self.hovered_option = idx
            # print(f'hovered {self.hovered_option}')
        return callback

    def make_radio_button_modified_callback(self, idx):
        def callback(event):
            self.selected_option = self.hovered_option
            self.radio_var.set(self.selected_option)
            # print(f'selected {self.selected_option}')
        return callback

    def setup_callbacks(self):
        self.selected_option = 0

        for i in range(len(self.options)):
            radio_label = self.frame.document.getElementById(f"radio_label_{i}")
            radio_label.bind("<Enter>", self.make_radio_label_hover_callback(i))
            radio_label.bind("<Button-1>", self.make_radio_label_callback(i))

            radio_button = self.frame.document.getElementById(f"radio_button_{i}")
            radio_button.bind("<Enter>", self.make_radio_button_hover_callback(i))
            radio_button.bind("<<Modified>>", self.make_radio_button_modified_callback(i))
