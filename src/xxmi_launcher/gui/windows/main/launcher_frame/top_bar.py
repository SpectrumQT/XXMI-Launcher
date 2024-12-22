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

        # for index, importer_id in enumerate(Config.Launcher.enabled_importers):

        for importer_id in Config.Importers.__dict__.keys():
            self.put(ImporterSelectButton(self, importer_id))
        self.put(LoadXXMIButton(self))

        self.put(GameBananaButton(self))
        self.put(DiscordButton(self))
        self.put(GitHubButton(self))

        self.put(SettingsButton(self))
        self.put(MinimizeButton(self))
        self.put(CloseButton(self))

        self.put(UnsafeModeText(self))

        self.subscribe(Events.Application.ToggleImporter, self.handle_toggle_importer)
        self.handle_toggle_importer(event=None)

    def _handle_button_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _handle_mouse_move(self, event):
        Events.Fire(Events.Application.MoveWindow(offset_x=self._offset_x, offset_y=self._offset_y))

    def handle_toggle_importer(self, event):
        if event is not None:
            try:
                index = Config.Launcher.enabled_importers.index(event.importer_id)
                del Config.Launcher.enabled_importers[index]
                Events.Fire(Events.GUI.LauncherFrame.ToggleImporter(importer_id=event.importer_id, index=0, show=False))

                for idx, importer_id in enumerate(Config.Launcher.enabled_importers):
                    if idx < index:
                        continue
                    Events.Fire(Events.GUI.LauncherFrame.ToggleImporter(importer_id=importer_id, index=idx, show=True))

            except ValueError:
                Config.Launcher.enabled_importers.append(event.importer_id)
                idx = len(Config.Launcher.enabled_importers) - 1
                Events.Fire(Events.GUI.LauncherFrame.ToggleImporter(importer_id=event.importer_id, index=idx, show=True))

        idx = len(Config.Launcher.enabled_importers)
        Events.Fire(Events.GUI.LauncherFrame.ToggleImporter(importer_id='XXMI', index=idx, show=True))


# region Importer Selection Buttons

class ImporterSelectButton(UIImageButton):
    def __init__(self, master, importer_id, **kwargs):
        defaults = {}
        defaults.update(
            button_image_path=f'button-select-game-{importer_id.lower()}.png',
            button_normal_opacity=0.8,
            button_hover_opacity=1,
            button_selected_opacity=1,
            button_disabled_opacity=0.5,
            bg_image_path='button-select-game-background.png',
            bg_width=60,
            bg_height=60,
            bg_normal_opacity=0,
            bg_hover_opacity=0.4,
            bg_selected_opacity=0.6,
            bg_disabled_opacity=0,
            command=lambda: Events.Fire(Events.Application.LoadImporter(importer_id=importer_id)),
            master=master
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.importer_id = importer_id
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)
        self.subscribe(Events.Application.LoadImporter,
                       lambda event: self.set_selected(event.importer_id == importer_id))
        self.subscribe(Events.GUI.LauncherFrame.ToggleImporter, self.handle_toggle_importer)
        self.subscribe(Events.GUI.LauncherFrame.HoverImporter, self.handle_hover_importer)

        tooltips = {
            'XXMI': f'Manage Model Importers',
            'WWMI': f'Wuthering Waves Model Importer',
            'ZZMI': f'Zenless Zone Zero Model Importer',
            'SRMI': f'Honkai: Star Rail Model Importer',
            'GIMI': f'Genshin Impact Model Importer',
        }
        self.set_tooltip(tooltips[importer_id], delay=0.5)

        try:
            idx = Config.Launcher.enabled_importers.index(importer_id)
            Events.Fire(Events.GUI.LauncherFrame.ToggleImporter(importer_id=importer_id, index=idx, show=True))
        except ValueError:
            Events.Fire(Events.GUI.LauncherFrame.ToggleImporter(importer_id=importer_id, index=-1, show=False))

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

    def handle_toggle_importer(self, event):
        if event.importer_id != self.importer_id:
            return
        if event.show:
            self.move(x=40 + 80 * event.index)
            self.show()
        else:
            self.hide()

    def handle_hover_importer(self, event):
        if event.importer_id != self.importer_id:
            return
        if event.hover:
            self._handle_enter(None)
        else:
            self._handle_leave(None)


class LoadXXMIButton(ImporterSelectButton):
    def __init__(self, master):
        super().__init__(
            importer_id='XXMI',
            width=38,
            height=38,
            button_normal_opacity=0.25,
            button_hover_opacity=0.9,
            button_selected_opacity=0.9,
            # bg_hover_opacity=0,
            # bg_selected_opacity=0,
            master=master)

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
        self.subscribe(Events.Application.LoadImporter, self.handle_load_importer)
        self.set_tooltip(self.get_tooltip, delay=0.01)

    def handle_load_importer(self, event):
        self.show(event.importer_id != 'XXMI')

    def open_link(self):
        if Config.Launcher.active_importer == 'WWMI':
            webbrowser.open('https://gamebanana.com/tools/17252'),
        elif Config.Launcher.active_importer == 'ZZMI':
            webbrowser.open('https://gamebanana.com/tools/17467'),
        elif Config.Launcher.active_importer == 'SRMI':
            webbrowser.open('https://gamebanana.com/tools/13050'),
        elif Config.Launcher.active_importer == 'GIMI':
            webbrowser.open('https://gamebanana.com/tools/10093'),

    def get_tooltip(self):
        return f'{Config.Launcher.active_importer} GameBanana'


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
        self.subscribe(Events.Application.LoadImporter, self.handle_load_importer)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)

    def handle_load_importer(self, event):
        self.set_disabled(event.importer_id == 'XXMI')

    def handle_stage_update(self, event):
        self.set_disabled(event.stage != Stage.Ready or Config.Launcher.active_importer == 'XXMI')


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
        self.enabled = Config.Launcher.active_importer != 'XXMI' and Config.Active.Migoto.unsafe_mode
        self.show()
