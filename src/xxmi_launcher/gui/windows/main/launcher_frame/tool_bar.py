from dataclasses import dataclass
from enum import Enum, auto

import core.event_manager as Events
import core.path_manager as Paths
import core.config_manager as Config
import gui.vars as Vars

from core.locale_manager import L

from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UIText, UIProgressBar, UILabel, UIImageButton, UIImage


class ToolBarFrame(UIFrame):
    def __init__(self, master, canvas, **kwargs):
        super().__init__(master=master, canvas=canvas, **kwargs)

        self.set_background_image(width=100, height=191, x=1230, y=595, anchor='se',
                                  fg_color='#000000', border_color='#000000', border_radius=16, border_width=1,
                                  brightness=1.0, opacity=0.7, dim_opacity=0.0)

        self.hovered = False
        self.locked = False

        self.background_image.bind('<Enter>', self._handle_enter)
        self.background_image.bind('<Leave>', self._handle_leave)

        self.hide_on_leave_running = False
        self.hide_on_leave_locked = False

        self.put(RepairXXMIButton(self))
        self.put(CheckForUpdatesButton(self))
        self.put(CreateShortcutButton(self))
        self.put(OptimizeModsButton(self))
        self.put(OpenModsFolderButton(self))

        width = max(e.winfo_width() for e in self.elements.values() if isinstance(e, ToolsBarButton)) + 30
        width = int(width / self._apply_widget_scaling(1.0))
        self.background_image.configure(width=width)
        for element in self.elements.values():
            if isinstance(element, ToolsBarButton):
                element.move(1230 - width + 10, element._y)
                element._bg_image.configure(width=width-20)

        self.subscribe(Events.GUI.LauncherFrame.ToggleToolbox, self.handle_toggle_toolbox)
        self.subscribe(Events.Application.Busy, lambda event: self.hide())

        self.hide()

    def handle_toggle_toolbox(self, event):
        if event.show:
            self.hide_on_leave_locked = True
        else:
            self.hide_on_leave_locked = False

        if event.hide_on_leave and not event.show:
            if self.hide_on_leave_running:
                return
            self.hide_on_leave_running = True
            self.master.master.after(200, self.hide_on_leave)
            self.master.master.after(100, self.show)
        else:
            self.master.master.after(100, self.show)

    def hide_on_leave(self, hide_on_next=False):
        if self.hovered or self.hide_on_leave_locked:
            self.master.master.after(50, self.hide_on_leave)
            return
        for element in self.elements.values():
            if not isinstance(element, ToolsBarButton):
                continue
            if element.hovered:
                self.master.master.after(50, self.hide_on_leave)
                return
        if not hide_on_next:
            self.master.master.after(200, self.hide_on_leave, True)
        else:
            self.hide_on_leave_running = False
            self.hide()

    def _handle_enter(self, event):
        self.hovered = True

    def _handle_leave(self, event):
        self.hovered = False

    def _show(self):
        self.locked = False
        super()._show()


# region Tools Bar Buttons

class ToolsBarButton(UIImageButton):
    def __init__(self, **kwargs):
        kwargs.update(
            x=1010,
            anchor='w',
            width=22,
            height=22,
            bg_width=100,
            bg_height=30,
            button_x_offset=8,
            button_normal_opacity=0.8,
            button_hover_opacity=1,
            button_disabled_opacity=0.35,
            bg_image_path='button-tool-background.png',
            bg_normal_opacity=0,
            bg_hover_opacity=0.15,
            bg_selected_opacity=0.25,
            bg_disabled_opacity=0,
            text_x_offset=36,
            font=("Asap", 17),
            fill='#cccccc',
            activefill='#ffffff',
            disabledfill='#888888',
        )
        super().__init__(**kwargs)

    def _handle_button_release(self, event):
        if self.hovered:
            if self.master.locked:
                return
            self.master.locked = True
            self.master.master.after(100, self.set_selected, False)
            self.master.master.after(300, self.master.hide)
        else:
            self.master.locked = False
        super()._handle_button_release(event)


class RepairXXMIButton(ToolsBarButton):
    def __init__(self, master):
        super().__init__(
            y=430,
            button_image_path='button-tool-repair-xxmi.png',
            text='',
            command=lambda: Events.Fire(Events.Application.Update(force=True, reinstall=True, packages=[Config.Launcher.active_importer])),
            master=master)
        self.subscribe(Events.Application.LoadImporter,
                       lambda event: self.set_text(L('tool_bar_repair_button', 'Repair {importer}').format(importer=event.importer_id)))


class CheckForUpdatesButton(ToolsBarButton):
    def __init__(self, master):
        super().__init__(
            y=465,
            button_image_path='button-tool-check-for-updates.png',
            text=L('tool_bar_check_updates_button', 'Check For Updates'),
            command=lambda: Events.Fire(Events.Application.CheckForUpdates()),
            master=master)


class CreateShortcutButton(ToolsBarButton):
    def __init__(self, master):
        super().__init__(
            y=500,
            button_image_path='button-tool-add-shortcut.png',
            text=L('tool_bar_add_shortcut_button', 'Add Desktop Shortcut'),
            command=lambda: Events.Fire(Events.ModelImporter.CreateShortcut()),
            master=master)


class OptimizeModsButton(ToolsBarButton):
    def __init__(self, master):
        super().__init__(
            y=535,
            button_image_path='button-tool-optimize-mods.png',
            text=L('tool_bar_optimize_mods_button', 'Optimize Mods'),
            command=lambda: Events.Fire(Events.ModelImporter.OptimizeMods(silent=False, reset_cache=True)),
            master=master)


class OpenModsFolderButton(ToolsBarButton):
    def __init__(self, master):
        super().__init__(
            y=570,
            button_image_path='button-tool-mods-folder.png',
            text=L('tool_bar_open_mods_button', 'Open Mods Folder'),
            command=lambda: Events.Fire(Events.MigotoManager.OpenModsFolder()),
            master=master)
        self.subscribe(Events.PackageManager.VersionNotification, self.handle_version_notification)

    def handle_version_notification(self, event):
        package_state = event.package_states.get(Config.Launcher.active_importer, None)
        if package_state is None:
            return
        self.set_disabled(not package_state.installed_version)

# endregion
