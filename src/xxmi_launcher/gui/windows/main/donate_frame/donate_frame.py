import logging
import time
import webbrowser

from textwrap import dedent

import core.config_manager as Config
import core.event_manager as Events
import gui.vars as Vars
from core.locale_manager import T, L

from gui.classes.containers import UIFrame
from gui.classes.widgets import UIText, UIImageButton


class DonateFrame(UIFrame):
    def __init__(self, master, canvas):
        super().__init__(master=master, canvas=canvas)

        self.set_background_image(image_path='background-image.png', width=master.master.cfg.width,
                                  height=master.master.cfg.height, x=0, y=0, anchor='nw', brightness=1.0, opacity=0.95)

        self._offset_x = 0
        self._offset_y = 0
        self.background_image.bind('<Button-1>', self._handle_button_press)
        self.background_image.bind('<B1-Motion>', self._handle_mouse_move)

        self.avatar = self.put(DevAvatarButton(self))
        self.introduction = self.put(IntroductionText(self))
        self.subject = self.put(SubjectText(self))
        self.subject_creators = self.put(SubjectText(self))
        self.subject_maintainers = self.put(SubjectText(self))
        self.subject_footer = self.put(SubjectText(self))
        self.my_patreon_button = self.put(MyPatreonButton(self))
        self.close_button = self.put(CloseButton(self))

        # self.put(UpdatePolicyFrame(self)).pack()

        self.hide()

    def _handle_button_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _handle_mouse_move(self, event):
        Events.Fire(Events.Application.MoveWindow(offset_x=self._offset_x, offset_y=self._offset_y))

    def set_content(self, model_importer = 'WWMI', num_sessions = 0, mode = 'NORMAL'):
        """
        Here comes the most cope function in the entire launcher ^^'
        It would have way more sense to use tkinterweb there, but it doesn't support transparency and bad with image AA
        So I'll go with this hardcoded coords mess until the proper layout manager is implemented
        """

        self.close_button.disable_timeout = 5 if mode == 'POPUP' else 0

        if mode == 'POPUP':
            importer_info = str(L('donate_and_wwmi', ' and WWMI')) if model_importer == 'WWMI' else ''
            self.introduction.set(dedent(str(L('donate_popup_introduction', """
                Hey there — just a quick moment, I promise I won't interrupt again!
                
                I'm SpectrumQT, the developer behind XXMI Launcher{importer_info}.
                Looks like you've already enjoyed {num_sessions} {model_importer} sessions — awesome!
            """).format(
                importer_info=importer_info,
                num_sessions=num_sessions,
                model_importer=model_importer
            ))).strip())
        else:
            if model_importer == 'WWMI':
                self.introduction.set(dedent(str(L('donate_wwmi_introduction', """
                    Hello! Thank you for visiting WWMI Appreciation Corner!
                    
                    This page is a bit unique, since I can't list many names here.
                    Simply because I'm soloing WWMI and XXMI Launcher development.
                """))).strip())
            else:
                self.introduction.set(dedent(str(L('donate_other_introduction', """
                    Hello! Thank you for visiting {model_importer} Appreciation Corner!
                    
                    Here you can see the dev team fighting for {model_importer} behind the scenes.
                    It's a tough battle — but shader hackers prevail!
                """).format(model_importer=model_importer))).strip())

        if model_importer == 'WWMI':
            self.subject.move(260, 345)
            self.subject.configure(anchor='nw', justify='left')
            self.subject.set(str(L('donate_wwmi_useful_check', "If you've been finding it useful, consider checking out")))

            self.my_patreon_button._text_image.configure(anchor='nw', justify='left')
            self.my_patreon_button._text_image.set(str(L('donate_my_patreon_campaign', 'my Patreon campaign.')))
            offset_x = 260 + self.subject._width + 10
            self.my_patreon_button.move(offset_x, 345)

            self.subject_creators.set('')
            self.subject_maintainers.set('')

            self.subject_footer.set(dedent(str(L('donate_wwmi_footer', """
                It's all about building better tools for the entire WWMI community.
                
                Who knows — maybe your few bucks could help shape the next big feature!
            """))).strip())
            self.subject_footer.configure(anchor='n', justify='center')
            self.subject_footer.move(640, 375)

        else:
            devs = {
                'Gustav0': {
                    'Home': 'https://github.com/Seris0',
                    'Tips': 'https://ko-fi.com/gustav0_'
                },
                'LeoTorrez': {
                    'Home': 'https://github.com/leotorrez',
                    'Tips': 'https://ko-fi.com/leotorrez'
                },
                'Nurarihyon': {
                    'Home': 'https://github.com/NurarihyonMaou',
                    'Tips': 'https://ko-fi.com/nurarihyonmaou'
                },
                'Satan1c': {
                    'Home': 'https://gamebanana.com/members/2789093',
                    'Tips': 'https://patreon.com/Satan1cL'
                },
                'Scyll': {
                    'Home': 'https://gamebanana.com/members/2644630',
                    'Tips': 'https://gamebanana.com/members/2644630'
                },
                'SilentNightSound': {
                    'Home': 'https://github.com/SilentNightSound',
                    'Tips': 'https://ko-fi.com/silentnightsound'
                },
                'SinsOfSeven': {
                    'Home': 'https://github.com/SinsOfSeven',
                    'Tips': 'https://ko-fi.com/sinsofseven'
                },
                'SpectrumQT': {
                    'Home': 'https://github.com/SpectrumQT',
                    'Tips': 'https://patreon.com/SpectrumQT'
                },
            }
            projects = {
                'GIMI': {
                    'Creators': ['SilentNightSound'],
                    'Maintainers': ['LeoTorrez', 'SinsOfSeven', 'Gustav0', 'Nurarihyon']
                },
                'SRMI': {
                    'Creators': ['SilentNightSound'],
                    'Maintainers': ['SinsOfSeven', 'LeoTorrez', 'Scyll', 'Gustav0']
                },
                'ZZMI': {
                    'Creators': ['LeoTorrez', 'Scyll', 'SilentNightSound'],
                    'Maintainers': ['SinsOfSeven', 'LeoTorrez', 'Gustav0', 'Scyll', 'Satan1c']
                },
                'HIMI': {
                    'Creators': ['SilentNightSound'],
                    'Maintainers': ['LeoTorrez', 'SinsOfSeven']
                },
            }
            platforms = {
                'ko-fi': 'Ko-Fi',
                'patreon': 'Patreon',
                'gamebanana': 'Ripe',
                'paypal': 'PayPal',
            }
            creators = projects[model_importer]['Creators']
            maintainers = projects[model_importer]['Maintainers']

            self.set_background_image(image_path='background-image-big.png', width=self.master.master.cfg.width,
                                      height=self.master.master.cfg.height, x=0, y=0, anchor='nw', brightness=1.0,
                                      opacity=0.95)

            self.avatar.move(220, 175)
            self.introduction.move(390, 180)

            self.subject.configure(anchor='n', justify='center')
            self.subject.set(dedent(str(L('donate_support_message', "Please consider supporting those who work hard every day to make {model_importer} possible!").format(model_importer=model_importer))))
            self.subject.move(640, 320)

            def get_devs_data(devs_list):
                result = []
                for dev in devs_list:
                    home = devs[dev]['Home']
                    link = devs[dev]['Tips']
                    platform = '???'
                    for path, name in platforms.items():
                        if path in link.lower():
                            platform = name
                            break
                    result.append((dev, home, platform, link))
                return result

            creators_data = get_devs_data(creators)
            maintainers_data = get_devs_data(maintainers)

            extra_offset_x = 0
            if len(maintainers_data) == 4:
                extra_offset_x = +80

            creator_label = str(L('donate_creators_single', '• Creator: ')) if len(creators) == 1 else str(L('donate_creators_multiple', '• Creators: '))
            self.subject_creators.set(creator_label)
            self.subject_creators.move(290+extra_offset_x, 355)

            offset_x = 405 + extra_offset_x
            if len(creators_data) == 1:
                offset_x -= 10

            for (name, home, platform, link) in creators_data:
                dev_name_button = self.put(LinkButton(self, x=offset_x, y=356, text=name, link=home))
                offset_x += 5 + dev_name_button._text_image._width
                tips_button = self.put(LinkButton(self, x=offset_x, y=356, text=f'({platform})', link=link))
                offset_x += 20 + tips_button._text_image._width

            maintainers_offset_y = 0
            if len(maintainers_data) >= 4:
                maintainers_offset_y = 15

            maintainer_label = str(L('donate_maintainers_single', '• Maintainer:')) if len(maintainers) == 1 else str(L('donate_maintainers_multiple', '• Maintainers:'))
            self.subject_maintainers.set(maintainer_label)
            self.subject_maintainers.move(290+extra_offset_x, 390 + maintainers_offset_y)

            offset_x = 440 + extra_offset_x
            offset_y = 0
            for pos_id, (name, home, platform, link) in enumerate(maintainers_data):
                if maintainers_offset_y > 0 and pos_id == 2:
                    offset_x = 440 + extra_offset_x
                    offset_y = 30
                dev_name_button = self.put(LinkButton(self, x=offset_x, y=391+offset_y, text=name, link=home))
                offset_x += 5 + dev_name_button._text_image._width
                tips_button = self.put(LinkButton(self, x=offset_x, y=391+offset_y, text=f'({platform})', link=link))
                offset_x += 20 + tips_button._text_image._width

            self.subject_footer.set(str(L('donate_launcher_handy', "Also, if the launcher has been handy, I'd appreciate you joining")))
            self.subject_footer.move(270, 427+maintainers_offset_y*2)

            offset_x = 325 + self.subject_footer._width + 10

            self.my_patreon_button._text_image.set(str(L('donate_my_patreon_short', 'my Patreon.')))
            self.my_patreon_button.move(offset_x, 427+maintainers_offset_y*2)

            self.close_button.move(640, 520+maintainers_offset_y)

    def close(self):
        self.hide()
        self.destroy()


class CloseButton(UIImageButton):
    def __init__(self, master):
        super().__init__(
            x=640,
            y=515,
            width=225,
            height=40,
            text=str(L('donate_close_button', 'Close')),
            # text_x_offset=36,
            text_y_offset=-1,
            text_anchor='center',
            font=('Roboto', 20),
            button_image_path='button-close-background.png',
            button_normal_opacity=0.85,
            button_hover_opacity=1,
            button_selected_opacity=1,
            button_disabled_opacity=0.75,
            disabledfill='#808080',
            command=self.close,
            anchor='center',
            master=master)
        self.disable_timeout = 0
        self.disable_time = 0

    def show(self, show=True):
        super().show(show)
        if self.disable_timeout > 0:
            self.set_disabled(True)
            self.auto_enable(timeout=self.disable_timeout)

    def close(self):
        self.master.close()

    def auto_enable(self, timeout=5):
        if self.disable_time == 0:
            self.disable_time = time.time()
        time_left = self.disable_time + timeout - time.time()
        if time_left > 0:
            self.set_text(str(L('donate_close_countdown', 'Close ({time_left})').format(time_left=int(time_left))))
            self.after(1000, self.auto_enable)
            return
        self.disable_time = 0
        self.set_disabled(False)
        self.set_text(str(L('donate_close_button', 'Close')))


class DevAvatarButton(UIImageButton):
    def __init__(self, master):
        super().__init__(
            x=220,
            y=195,
            width=128,
            height=128,
            button_image_path='button_dev_avatar.png',
            button_normal_opacity=1,
            button_hover_opacity=0.8,
            button_selected_opacity=1,
            command=self.open_link,
            anchor='nw',
            master=master)

    def open_link(self):
        webbrowser.open('https://patreon.com/SpectrumQT')


class IntroductionText(UIText):
    def __init__(self, master):
        super().__init__(x=390,
                         y=200,
                         text='',
                         font=('Asap', 22),
                         fill='#f0f0f0',
                         activefill='#f0f0f0',
                         anchor='nw',
                         master=master)


class SubjectText(UIText):
    def __init__(self, master):
        super().__init__(x=640,
                         y=355,
                         text='',
                         font=('Asap', 22),
                         justify='left',
                         fill='#f0f0f0',
                         activefill='#f0f0f0',
                         anchor='nw',
                         master=master)


class LinkButton(UIImageButton):
    def __init__(self, master, **kwargs):
        defaults = {}
        defaults.update(
            width=32,
            height=32,
            text='',
            font=('Asap', 22),
            fill='#88aef2',
            activefill='white',
            anchor='nw',
            command=self.open_link,
            master=master
        )
        defaults.update(kwargs)
        super().__init__(**defaults)

        self.link = kwargs.get('link', None)
        self.set_tooltip(self.get_tooltip, delay = 0.1)

    def get_tooltip(self):
        return f'`{self.link}`'

    def open_link(self):
        webbrowser.open(self.link)


class MyPatreonButton(LinkButton):
    def __init__(self, master):
        super().__init__(x=896,
                         y=340,
                         text='my Patreon campaign',
                         anchor='n',
                         link='https://patreon.com/SpectrumQT',
                         master=master)
        # self.subscribe(Events.PackageManager.VersionNotification, self.handle_version_notification)


# class UpdatePolicyFrame(UIFrame):
#     def __init__(self, master):
#         super().__init__(master, width=800,
#             height=500)
#         self.configure(fg_color='transparent')
#
#         self.message_widget = HtmlLabel(
#             master=self,
#             messages_enabled=False,
#             caches_enabled=False,
#             width=800,
#             height=500,
#             fontscale=1.2 * self._apply_widget_scaling(1.0))
#         # self.message_widget.html.config(
#         #     # Set max width for word wrapping
#         #     width=int(self.width * self.widget._apply_widget_scaling(1.0)),
#         #     # Setting height doesn't seem to have any effect
#         #     # height=int(self.tooltip.height * self.tooltip.scaling),
#         # )
#         style = """
#         <style>
#             html { background-color: #24252a;}
#             body { font-size: 18px; color: #ffffff}
#             p { font-family: Asap; margin: 5px;}
#             ul { margin: 10px 5px;}
#             li { margin: 10px 5px;}
#             h1 { font-size: 18px; margin: 10px 5px;}
#             h2 { font-size: 16px; margin: 10px 5px;}
#         </style>
#         """
#         html = style + f"""
#         <html>
#         <h1>This is a heading</h1>
#         <p>This is a paragraph.</p>
#
#         <img src='file:///{Config.get_resource_path(self, 'button_dev_avatar.png')}' width='128'> <br>
#
#         Hey there — just a quick moment, I promise I won't interrupt again!
#         <br><br>
#         I'm SpectrumQT, the developer behind XXMI Launcher and WWMI.
#         <br>
#         Looks like you've already enjoyed 123 WWMI sessions — awesome!
#         <br><br>
#         If you've been finding it useful, consider checking out my Patreon campaign.
#         <br>
#         It's all about building better tools for the entire WWMI community.
#         <br><br>
#         Who knows — maybe your few bucks could help shape the next big feature!
#         </body>
#         </html>
#         """
#         html = html.replace("\\", "/")
#         self.message_widget.load_html(html)
#         # self.message_widget.pack(fill="both", expand=True)
#         self.message_widget.place(x=0, y=0, width=800, height=500)
#         # self.message_widget.place(x=150, y=150)
