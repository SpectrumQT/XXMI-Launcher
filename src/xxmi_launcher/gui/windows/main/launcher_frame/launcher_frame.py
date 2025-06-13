import webbrowser
from textwrap import dedent

from core.locale_manager import L, T
import core.event_manager as Events
import core.path_manager as Paths
import core.config_manager as Config
import gui.vars as Vars

from gui.events import Stage
from gui.classes.containers import UIFrame
from gui.classes.widgets import UIText, UIImageButton
from gui.windows.main.launcher_frame.top_bar import TopBarFrame
from gui.windows.main.launcher_frame.bottom_bar import BottomBarFrame
from gui.windows.main.launcher_frame.tool_bar import ToolBarFrame
from gui.windows.settings.settings_frame import SettingsFrame


class LauncherFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master, width=master.cfg.width, height=master.cfg.height, fg_color='transparent')

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas.grid(row=0, column=0)

        # Background
        self.update_background(Config.Launcher.active_importer)

        # Top Panel
        self.put(TopBarFrame(self, self.canvas))

        # Bottom Panel
        self.put(BottomBarFrame(self, self.canvas, width=master.cfg.width, height=master.cfg.height)).grid(row=0, column=0, sticky='swe')

        # Game Tiles Panel
        self.put(SelectGameText(self))
        for index, importer_id in enumerate(Config.Importers.__dict__.keys()):
            self.put(GameTileButton(self, index, importer_id))

        # Action Panel
        self.put(UpdateButton(self))
        tools_button = self.put(ToolsButton(self))
        self.put(StartButton(self, tools_button))
        self.put(InstallButton(self, tools_button))
        self.put(ToolBarFrame(self, self.canvas))

        # Package versions
        self.put(LauncherVersionText(self))
        self.put(XXMIVersionText(self))
        self.put(ImporterVersionText(self))

        # Settings Frame
        self.put(SettingsFrame(self, self.canvas))

        # Donate Frame
        self.subscribe(Events.Application.OpenDonationCenter, self.handle_open_donation_center)

        # Application Events
        self.subscribe(
            Events.Application.Ready,
            lambda event: Events.Fire(Events.GUI.LauncherFrame.StageUpdate(Stage.Ready)))
        self.subscribe(
            Events.PackageManager.StartDownload,
            lambda event: Events.Fire(Events.GUI.LauncherFrame.StageUpdate(Stage.Download)))
        self.subscribe(
            Events.Application.Busy,
            lambda event: Events.Fire(Events.GUI.LauncherFrame.StageUpdate(Stage.Busy)))
        self.subscribe(
            Events.Application.LoadImporter,
            lambda event: self.update_background(event.importer_id))

    def update_background(self, importer_id):
        self.set_background_image(f'background-image-{importer_id.lower()}.jpg',
                                  width=self.master.cfg.width,
                                  height=self.master.cfg.height)

    def handle_open_donation_center(self, event: Events.Application.OpenDonationCenter):
        from gui.windows.main.donate_frame.donate_frame import DonateFrame
        donate_frame = self.put(DonateFrame(self, self.canvas))
        donate_frame.set_content(mode=event.mode, model_importer=event.model_importer, num_sessions=event.launch_count)
        donate_frame.show()


class SelectGameText(UIText):
    def __init__(self, master):
        super().__init__(x=30,
                         y=495,
                         text=str(L('launcher_select_games_text', 'Select Games To Mod:')),
                         font=('Microsoft YaHei', 24, 'bold'),
                         fill='white',
                         activefill='white',
                         anchor='nw',
                         master=master)
        self.subscribe(Events.Application.LoadImporter, self.handle_load_importer)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)
        # self.subscribe_show(
        #     Events.GUI.LauncherFrame.StageUpdate,
        #     lambda event: event.stage == Stage.Ready)

    def handle_load_importer(self, event):
        self.show(self.stage == Stage.Ready and event.importer_id == 'XXMI')

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready and Config.Launcher.active_importer == 'XXMI')


class GameTileButton(UIImageButton):
    def __init__(self, master, pos_id, importer_id):
        super().__init__(
            x=130+pos_id*234,
            y=600,
            button_image_path='game-tile-background.png',
            width=206,
            height=116,
            button_normal_opacity=0.35,
            button_hover_opacity=0.65,
            button_selected_opacity=1,
            button_normal_brightness=1,
            button_selected_brightness=1,
            bg_image_path=f'game-tile-{importer_id.lower()}.png',
            bg_width=204,
            bg_height=113,
            bg_normal_opacity=0.75,
            bg_hover_opacity=0.75,
            bg_selected_opacity=1,
            bg_normal_brightness=0.6,
            bg_selected_brightness=1,
            command=lambda: Events.Fire(Events.Application.ToggleImporter(importer_id=importer_id)),
            master=master)

        self.eye_button_image = self.put(UIImageButton(
            x=self._x + 80, y=self._y - 42,
            button_image_path='eye-show.png',
            width=28,
            height=28,
            button_normal_opacity=0,
            button_hover_opacity=1,
            button_selected_opacity=0,
            bg_image_path=f'eye-hide.png',
            bg_width=28,
            bg_height=28,
            bg_normal_opacity=0,
            bg_hover_opacity=0,
            bg_selected_opacity=1,
            master=master))

        self.eye_button_image.bind("<ButtonPress-1>", self._handle_button_press)
        self.eye_button_image.bind("<ButtonRelease-1>", self._handle_button_release)
        self.eye_button_image.bind("<Enter>", self._handle_enter)
        self.eye_button_image.bind("<Leave>", self._handle_leave)

        self.importer_id = importer_id

        self.subscribe(Events.Application.LoadImporter, self.handle_load_importer)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)
        self.subscribe(Events.GUI.LauncherFrame.ToggleImporter, self.handle_toggle_importer)

        try:
            idx = Config.Launcher.enabled_importers.index(importer_id)
            self.set_selected(True)
        except ValueError:
            self.set_selected(False)

    def handle_load_importer(self, event):
        self.show(self.stage == Stage.Ready and event.importer_id == 'XXMI')

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready and Config.Launcher.active_importer == 'XXMI')

    def handle_toggle_importer(self, event):
        if event.importer_id != self.importer_id:
            return
        self.set_selected(event.show)

    def _handle_enter(self, event):
        super()._handle_enter(event)
        Events.Fire(Events.GUI.LauncherFrame.HoverImporter(importer_id=self.importer_id, hover=True))
        self.eye_button_image._handle_enter(event)
        if self.selected:
            self.eye_button_image.set_selected(self.selected)

    def _handle_leave(self, event):
        super()._handle_leave(event)
        Events.Fire(Events.GUI.LauncherFrame.HoverImporter(importer_id=self.importer_id, hover=False))
        self.eye_button_image._handle_leave(event)
        self.eye_button_image.set_selected(False)

    def set_selected(self, selected: bool = False):
        super().set_selected(selected)
        if self.hovered:
            self.eye_button_image.set_selected(selected)


class MainActionButton(UIImageButton):
    def __init__(self, **kwargs):
        self.command = kwargs['command']
        defaults = {}
        defaults.update(
            y=640,
            height=64,
            button_normal_opacity=0.95,
            button_hover_opacity=1,
            button_normal_brightness=0.95,
            button_hover_brightness=1,
            button_selected_brightness=0.8,
            bg_normal_opacity=0.95,
            bg_hover_opacity=1,
            bg_normal_brightness=0.95,
            bg_hover_brightness=1,
            bg_selected_brightness=0.8,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.stage = None
        self.subscribe(Events.Application.LoadImporter, self.handle_load_importer)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)

    def handle_load_importer(self, event):
        self.show(self.stage == Stage.Ready and event.importer_id != 'XXMI')

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready and Config.Launcher.active_importer != 'XXMI')


class UpdateButton(MainActionButton):
    def __init__(self, master):
        super().__init__(
            x=800,
            width=64,
            button_image_path='button-update.png',
            command=lambda: Events.Fire(Events.Application.Update(force=True)),
            master=master)
        self.set_tooltip(str(L('launcher_update_tooltip', 'Update packages to latest versions')), delay=0.01)
        self.subscribe(Events.PackageManager.VersionNotification, self.handle_version_notification)

    def handle_version_notification(self, event):
        pending_update_message = []

        for package_name, package in event.package_states.items():
            if package_name == Config.Launcher.active_importer and not package.installed_version:
                pending_update_message = []
                break
            if package.latest_version != '' and (package.installed_version != package.latest_version):
                pending_update_message.append(
                    f'* {package_name}: {package.installed_version or 'N/A'} → {package.latest_version}')

        if len(pending_update_message) > 0:
            self.enabled = True
            self.set_tooltip(str(L('action_update_packages', dedent("""
                ## Update packages to latest versions:
                {pending_update_message}
                
                <font color="#3366ff">*Hover over versions in the bottom-left corner to view update descriptions.*</font>
            """)).format(
                pending_update_message='\n'.join(pending_update_message)
            )))
            self.show(self.stage == Stage.Ready and Config.Launcher.active_importer != 'XXMI')
        else:
            self.enabled = False
            self.set_tooltip(str(L('launcher_no_updates_tooltip', 'No updates available!')))
            self.hide()


class StartButton(MainActionButton):
    def __init__(self, master, tools_button):
        super().__init__(
            x=1023,
            width=32,
            height=32,
            button_image_path='button-start.png',
            button_x_offset=-14,
            bg_image_path='button-start-background.png',
            bg_width=340,
            bg_height=64,
            text=str(L('launcher_start_button', 'Start')),
            text_x_offset=36,
            text_y_offset=-1,
            font=('Microsoft YaHei', 23, 'bold'),
            command=lambda: Events.Fire(Events.Application.Launch()),
            master=master)
        self.tools_button = tools_button
        self.stage = None
        self.subscribe(
            Events.PackageManager.VersionNotification,
            self.handle_version_notification)

    def handle_version_notification(self, event):
        package_state = event.package_states.get(Config.Launcher.active_importer, None)
        if package_state is None:
            return
        installed = package_state.installed_version != ''
        self.set_enabled(installed)
        self.show(self.stage == Stage.Ready and Config.Launcher.active_importer != 'XXMI')

    def _handle_enter(self, event):
        self.tools_button._handle_enter(None, True)
        super()._handle_enter(self)

    def _handle_leave(self, event):
        self.tools_button._handle_leave(None, True)
        super()._handle_leave(self)

    def _handle_button_press(self, event):
        self.tools_button.set_selected(True)
        super()._handle_button_press(self)

    def _handle_button_release(self, event):
        self.tools_button.selected = False
        self.tools_button._handle_leave(None, True)
        super()._handle_button_release(self)


class InstallButton(MainActionButton):
    def __init__(self, master, tools_button):
        super().__init__(
            x=1023,
            width=32,
            height=32,
            # button_image_path='button-start.png',
            # button_x_offset=-14,
            bg_image_path='button-start-background.png',
            bg_width=340,
            bg_height=64,
            text=str(L('launcher_install_button', 'Install')),
            text_x_offset=18,
            text_y_offset=-1,
            font=('Microsoft YaHei', 23, 'bold'),
            command=lambda: Events.Fire(Events.ModelImporter.Install()),
            master=master)
        self.tools_button = tools_button
        self.subscribe(
            Events.PackageManager.VersionNotification,
            self.handle_version_notification)

    def handle_version_notification(self, event):
        package_state = event.package_states.get(Config.Launcher.active_importer, None)
        if package_state is None:
            return
        not_installed = package_state.installed_version == ''
        self.set_enabled(not_installed)
        self.show(self.stage == Stage.Ready and Config.Launcher.active_importer != 'XXMI')

    def _handle_enter(self, event):
        self.tools_button._handle_enter(None, True)
        super()._handle_enter(self)

    def _handle_leave(self, event):
        self.tools_button._handle_leave(None, True)
        super()._handle_leave(self)

    def _handle_button_press(self, event):
        self.tools_button.set_selected(True)
        super()._handle_button_press(self)

    def _handle_button_release(self, event):
        self.tools_button.selected = False
        self.tools_button._handle_leave(None, True)
        super()._handle_button_release(self)


class ToolsButton(MainActionButton):
    def __init__(self, master):
        super().__init__(
            x=1210,
            width=37,
            button_image_path='button-tools.png',
            command=lambda: True,
            master=master)

    def _handle_enter(self, event, suppress=False):
        if not suppress:
            Events.Fire(Events.GUI.LauncherFrame.ToggleToolbox(show=True))
        super()._handle_enter(self)

    def _handle_leave(self, event, suppress=False):
        if not suppress:
            Events.Fire(Events.GUI.LauncherFrame.ToggleToolbox(hide_on_leave=True))
        super()._handle_leave(self)


class PackageVersionText(UIImageButton):
    def __init__(self, **kwargs):
        defaults = {}
        defaults.update(
            width=32,
            height=32,
            text='',
            font=('Consolas', 16),
            fill='#999999',
            activefill='white',
            anchor='nw',
            command=self.open_dev_blog_link,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.stage = None
        self.package_name = ''
        self.set_tooltip(self.get_tooltip, delay = 0.1)
        self.subscribe(Events.GUI.LauncherFrame.StageUpdate, self.handle_stage_update)
        self.package_aliases = {
            'Launcher': 'XXMI Launcher',
            'XXMI': 'XXMI DLL',
        }
        self.dev_blog_links = {
            'XXMI-Launcher': 'https://www.patreon.com/collection/1552149',
            'XXMI-Libs-Package': 'https://www.patreon.com/collection/1552154',
            'WWMI-Package': 'https://www.patreon.com/collection/1552139',
        }
        self.bind("<ButtonRelease-3>", self.open_changelog_link)

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready and Config.Launcher.active_importer != 'XXMI')

    def open_dev_blog_link(self):
        package = Events.Call(Events.PackageManager.GetPackage(self.package_name))
        metadata = package.metadata
        dev_blog_link = self.dev_blog_links.get(metadata.github_repo_name, None)
        if dev_blog_link is not None:
            webbrowser.open(dev_blog_link)
        else:
            webbrowser.open(f'https://github.com/{metadata.github_repo_owner}/{metadata.github_repo_name}/releases')

    def open_changelog_link(self, event):
        package = Events.Call(Events.PackageManager.GetPackage(self.package_name))
        metadata = package.metadata
        webbrowser.open(f'https://github.com/{metadata.github_repo_owner}/{metadata.github_repo_name}/releases')

    def get_tooltip(self):
        package = Events.Call(Events.PackageManager.GetPackage(self.package_name))

        installed_release_notes = package.cfg.deployed_release_notes

        if package.installed_version == package.cfg.latest_version:
            package_release_notes = str(L('package_release_notes_up_to_date', dedent("""
                # What's new in {package_name} v{new_package_version}:
                {installed_release_notes}
            """)).format(
                package_name=package.metadata.package_name,
                new_package_version=package.cfg.latest_version,
                installed_release_notes=installed_release_notes or package.cfg.latest_release_notes
            ))
        else:
            package_release_notes = str(L('package_release_notes_update_available', dedent("""
                # Update {package_name} to v{new_package_version} for:
                {latest_release_notes}
            """)).format(
                package_name=package.metadata.package_name,
                new_package_version=package.cfg.latest_version,
                latest_release_notes=package.cfg.latest_release_notes
            ))

        if not package.cfg.deployed_release_notes and not package.cfg.latest_release_notes:
            package_release_notes = str(L('package_release_notes_not_installed', dedent("""
                Press **Install** button to setup the package.
            """)))

        if self.package_name == 'Launcher':
            package_description = str(L('package_description_launcher', dedent("""
                *This package is XXMI Launcher App itself and defines its features.*
            """)))
        elif self.package_name == 'XXMI':
            package_description = str(L('package_description_xxmi_libraries', dedent("""
                *XXMI Libraries package is custom 3dmigoto build fiddling with data between GPU and a game process.*
            """)))
        else:
            package_description = str(L('package_description_model_importer', dedent("""
                *Model Importer package offers a set of API functions required for mods to work in given game.*
            """)))
        if self.package_name in ['Launcher', 'XXMI', 'WWMI']:
            actions_tooltip = str(L('package_description_tooltip_open_github_changelog', 
                '<font color="#3366ff">*<u>Left-Click</u> to open {package_name} Dev Blog on Patreon.*</font>\n'
                '<font color="#3366ff">*<u>Right-Click</u> to open {package_name} GitHub releases for full changelog.*</font>'))
        else:
            actions_tooltip = str(L('package_description_tooltip_open_dev_blog', 
                '<font color="#3366ff">*<u>Left-Click</u> to open {package_name} GitHub releases for full changelog.*</font>'))

        txt = str(L('package_release_notes', 
            '{package_release_notes}\n\n{actions_tooltip}\n<font color="#aaaaaa">{package_description}</font>')).format(
            package_release_notes=package_release_notes,
            actions_tooltip=actions_tooltip,
            package_description=package_description
        )

        return txt.format(
            package_name=self.package_aliases.get(package.metadata.package_name, package.metadata.package_name),
            active_importer=Config.Launcher.active_importer,
            installed_package_version=package.installed_version,
            new_package_version=package.cfg.latest_version,
            latest_release_notes=package.cfg.latest_release_notes,
            installed_release_notes=installed_release_notes
        )


class LauncherVersionText(PackageVersionText):
    def __init__(self, master):
        super().__init__(x=20,
                         y=680,
                         master=master)
        self.package_name = 'Launcher'
        self.subscribe(Events.PackageManager.VersionNotification, self.handle_version_notification)

    def handle_stage_update(self, event):
        self.stage = event.stage
        self.show(self.stage == Stage.Ready)

    def handle_version_notification(self, event):
        self.set_text(f'CORE {event.package_states["Launcher"].installed_version}')


class XXMIVersionText(PackageVersionText):
    def __init__(self, master):
        super().__init__(x=125,
                         y=680,
                         master=master)
        self.subscribe(Events.Application.LoadImporter, self.handle_load_importer)
        self.subscribe(Events.PackageManager.VersionNotification, self.handle_version_notification)
        self.package_name = 'XXMI'

    def handle_load_importer(self, event):
        self.show(self.stage == Stage.Ready and event.importer_id != 'XXMI')

    def handle_version_notification(self, event):
        package_state = event.package_states.get('XXMI', None)
        if package_state is None:
            return
        if package_state.installed_version:
            self.set_text(f'XXMI {package_state.installed_version}')
        else:
            self.set_text(f'XXMI N/A')


class ImporterVersionText(PackageVersionText):
    def __init__(self, master):
        super().__init__(x=230,
                         y=680,
                         master=master)
        self.subscribe(Events.Application.LoadImporter, self.handle_load_importer)
        self.subscribe(Events.PackageManager.VersionNotification, self.handle_version_notification)

    def handle_load_importer(self, event):
        self.show(self.stage == Stage.Ready and event.importer_id != 'XXMI')

    def handle_version_notification(self, event):
        package_state = event.package_states.get(Config.Launcher.active_importer, None)
        if package_state is None:
            return
        package_name = Config.Launcher.active_importer
        if package_state.installed_version:
            self.set_text(f'{package_name} {package_state.installed_version}')
        else:
            self.set_text(f'{package_name} N/A')

    def get_tooltip(self, package_name=''):
        self.package_name = Config.Launcher.active_importer
        return super().get_tooltip()
