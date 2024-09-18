import webbrowser

from dataclasses import dataclass
from enum import Enum, auto

import core.event_manager as Events
import core.path_manager as Paths
import core.config_manager as Config
import gui.vars as Vars

from gui.events import Stage
from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UIText, UIProgressBar, UILabel, UIImageButton, UIImage


class TopBarFrame(UIFrame):
    def __init__(self, master, canvas, **kwargs):
        super().__init__(master=master, canvas=canvas, **kwargs)

        self.set_background_image(image_path='background-image.png', width=1280,
                                  height=80, opacity=0.65)

        self._offset_x = 0
        self._offset_y = 0
        self.background_image.bind('<Button-1>', self._handle_button_press)
        self.background_image.bind('<B1-Motion>', self._handle_mouse_move)

        self.put(LoadWWMIButton(self))
        self.put(LoadZZMIButton(self))
        self.put(LoadSRMIButton(self))
        self.put(LoadGIMIButton(self))

        self.put(GameBananaButton(self))
        self.put(DiscordButton(self))
        self.put(GitHubButton(self))

        self.put(SettingsButton(self))
        self.put(MinimizeButton(self))
        self.put(CloseButton(self))

        self.put(UnsafeModeText(self))

    def _handle_button_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _handle_mouse_move(self, event):
        Events.Fire(Events.Application.MoveWindow(offset_x=self._offset_x, offset_y=self._offset_y))


# region Importer Selection Buttons
class ImporterSelectButton(UIImageButton):
    def __init__(self, **kwargs):
        self.command = kwargs['command']
        kwargs.update(
            # button_normal_brightness=0.8,
            # button_selected_brightness=1,
            # button_hover_brightness=1,
            button_normal_opacity=0.8,
            button_hover_opacity=1,
            button_selected_opacity=1,
            button_disabled_opacity=0.5,
            bg_image_path='button-select-game-background.png',
            bg_normal_opacity=0,
            bg_hover_opacity=0.5,
            bg_selected_opacity=1,
            bg_disabled_opacity=0,
        )
        super().__init__(**kwargs)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)

    def _handle_button_press(self, event):
        if self.disabled:
            return
        self.command()

    def _handle_button_release(self, event):
        pass

    def handle_stage_update(self, event):
        if event.stage == Stage.Ready:
            self.set_disabled(False)
        elif not self.selected:
            self.set_disabled(True)


class LoadWWMIButton(ImporterSelectButton):
    def __init__(self, master):
        super().__init__(
            x=40,
            button_image_path='button-select-game-wwmi.png',
            command=lambda: Events.Fire(Events.Application.LoadImporter(importer_id='WWMI')),
            master=master)
        self.subscribe(Events.Application.LoadImporter,
                       lambda event: self.set_selected(event.importer_id == 'WWMI'))
        self.set_tooltip(f'Wuthering Waves Model Importer', delay=0.5)


class LoadZZMIButton(ImporterSelectButton):
    def __init__(self, master):
        super().__init__(
            x=120,
            button_image_path='button-select-game-zzmi.png',
            command=lambda: Events.Fire(Events.Application.LoadImporter(importer_id='ZZMI')),
            master=master)

        self.subscribe(Events.Application.LoadImporter,
                       lambda event: self.set_selected(event.importer_id == 'ZZMI'))
        self.set_tooltip(f'Zenless Zone Zero Model Importer', delay=0.5)


class LoadSRMIButton(ImporterSelectButton):
    def __init__(self, master):
        super().__init__(
            x=200,
            button_image_path='button-select-game-srmi.png',
            command=lambda: Events.Fire(Events.Application.LoadImporter(importer_id='SRMI')),
            master=master)

        self.subscribe(Events.Application.LoadImporter,
                       lambda event: self.set_selected(event.importer_id == 'SRMI'))
        self.set_tooltip(f'Honkai: Star Rail Model Importer', delay=0.5)


class LoadGIMIButton(ImporterSelectButton):
    def __init__(self, master):
        super().__init__(
            x=280,
            button_image_path='button-select-game-gimi.png',
            command=lambda: Events.Fire(Events.Application.LoadImporter(importer_id='GIMI')),
            master=master)

        self.subscribe(Events.Application.LoadImporter,
                       lambda event: self.set_selected(event.importer_id == 'GIMI'))
        self.set_tooltip(f'Genshin Impact Model Importer', delay=0.5)

# endregion


# region Web Resource Buttons

class WebResourceButton(UIImageButton):
    def __init__(self, **kwargs):
        kwargs.update(
            y=40,
            width=42,
            height=42,
            bg_width=54,
            bg_height=54,
            button_normal_opacity=0.8,
            button_hover_opacity=1,
            button_selected_opacity=1,
            bg_image_path='button-resource-background.png',
            bg_normal_opacity=0,
            bg_hover_opacity=0.2,
            bg_selected_opacity=0.35)
        super().__init__(**kwargs)


class GameBananaButton(WebResourceButton):
    def __init__(self, master):
        super().__init__(
            x=860,
            button_image_path='button-resource-gamebanana.png',
            command=self.open_link,
            master=master)
        self.set_tooltip(self.get_tooltip, delay=0.01)

    def get_tooltip(self):
        return f'{Config.Launcher.active_importer} GameBanana'

    def open_link(self):
        if Config.Launcher.active_importer == 'WWMI':
            webbrowser.open('https://gamebanana.com/tools/17252'),
        elif Config.Launcher.active_importer == 'ZZMI':
            webbrowser.open('https://gamebanana.com/tools/17467'),
        elif Config.Launcher.active_importer == 'SRMI':
            webbrowser.open('https://gamebanana.com/tools/13050'),
        elif Config.Launcher.active_importer == 'GIMI':
            webbrowser.open('https://gamebanana.com/tools/10093'),


class DiscordButton(WebResourceButton):
    def __init__(self, master):
        super().__init__(
            x=930,
            button_image_path='button-resource-discord.png',
            command=lambda: webbrowser.open('https://discord.com/invite/agmg'),
            master=master)
        self.set_tooltip(f'AGMG Modding Community Discord', delay=0.01)


class GitHubButton(WebResourceButton):
    def __init__(self, master):
        super().__init__(
            x=1000,
            button_image_path='button-resource-github.png',
            command=lambda: webbrowser.open('https://github.com/SpectrumQT/XXMI-Launcher'),
            master=master)
        self.set_tooltip(f'XXMI Launcher GitHub', delay=0.01)

# endregion


# region Control Buttons

class ControlButton(UIImageButton):
    def __init__(self, **kwargs):
        kwargs.update(
            y=40,
            width=32,
            height=32,
            bg_width=48,
            bg_height=48,
            button_normal_opacity=0.8,
            button_hover_opacity=1,
            button_selected_opacity=1,
            bg_image_path='button-system-background.png',
            bg_normal_opacity=0,
            bg_hover_opacity=0.2,
            bg_selected_opacity=0.3)
        super().__init__(**kwargs)


class SettingsButton(ControlButton):
    def __init__(self, master):
        super().__init__(
            x=1120,
            width=36,
            height=36,
            button_disabled_opacity=0.5,
            bg_disabled_opacity=0,
            button_image_path='button-system-settings.png',
            command=lambda: Events.Fire((Events.Application.OpenSettings())),
            master=master)
        self.set_tooltip(f'Open Settings', delay=0.1)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)

    def handle_stage_update(self, event):
        if event.stage == Stage.Ready:
            self.set_disabled(False)
        elif not self.selected:
            self.set_disabled(True)


class MinimizeButton(ControlButton):
    def __init__(self, master):
        super().__init__(
            x=1180,
            button_image_path='button-system-minimize.png',
            command=lambda: Events.Fire((Events.Application.Minimize())),
            master=master)
        self.set_tooltip(f'Minimize', delay=0.1)


class CloseButton(ControlButton):
    def __init__(self, master):
        super().__init__(
            x=1240,
            button_image_path='button-system-close.png',
            command=lambda: Events.Fire((Events.Application.Close())),
            master=master)
        self.set_tooltip(f'Close', delay=0.1)

# endregion


class UnsafeModeText(UIText):
    def __init__(self, master):
        super().__init__(x=640,
                         y=25,
                         text='Unsafe Mode',
                         font=('Asap', 20),
                         fill='#ff2929',
                         activefill='#ff4040',
                         anchor='n',
                         master=master)
        self.subscribe_show(
            Events.GUI.LauncherFrame.StageUpdate,
            lambda event: event.stage == Stage.Ready)
        self.subscribe(
            Events.Application.ConfigUpdate,
            self.handle_config_update)
        self.set_tooltip(f'Usage of 3-rd party 3dmigoto DLLs is allowed. Make sure to use ones only from a trusted source!')

    def handle_config_update(self, event=None):
        self.enabled = Config.Active.Migoto.unsafe_mode
        self.show()
