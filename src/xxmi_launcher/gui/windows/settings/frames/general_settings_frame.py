import subprocess
import webbrowser

from pathlib import Path
from customtkinter import filedialog, ThemeManager
from textwrap import dedent

import core.event_manager as Events
import core.config_manager as Config
import core.path_manager as Paths
import core.i18n_manager as I18n
import gui.vars as Vars
from core.application import Application

from gui.classes.containers import UIFrame
from gui.classes.widgets import UILabel, UIButton, UIEntry, UICheckbox,  UIOptionMenu


class GeneralSettingsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure((0, 2, 3), weight=1)
        self.grid_columnconfigure(1, weight=100)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(6, weight=100)

        # Language
        self.put(LanguageLabel(self)).grid(row=0, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(LanguageOptionMenu(self)).grid(row=0, column=1, padx=(0, 10), pady=(0, 30), sticky='w')

        # Game Folder
        self.put(GameFolderLabel(self)).grid(row=1, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(GameFolderFrame(self)).grid(row=1, column=1, padx=(0, 65), pady=(0, 30), sticky='new', columnspan=3)
        self.put(DetectGameFolderButton(self)).grid(row=1, column=1, padx=(0, 20), pady=(0, 30), sticky='e', columnspan=3)

        # Launch Options
        self.put(LaunchOptionsLabel(self)).grid(row=2, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
        self.put(LaunchOptionsFrame(self)).grid(row=2, column=1, padx=(0, 20), pady=(0, 30), sticky='ew', columnspan=3)

        # Process Priority
        self.put(ProcessPriorityLabel(self)).grid(row=3, column=0, padx=20, pady=(0, 30), sticky='w')
        self.put(ProcessPriorityOptionMenu(self)).grid(row=3, column=1, padx=(0, 10), pady=(0, 30), sticky='w')

        # Auto Config
        if Vars.Launcher.active_importer.get() != 'SRMI':
            self.put(AutoConfigLabel(self)).grid(row=4, column=0, padx=(20, 0), pady=(0, 30), sticky='w')
            self.put(AutoConfigFrame(self)).grid(row=4, column=1, padx=(0, 20), pady=(0, 30), sticky='w', columnspan=3)

        if Vars.Launcher.active_importer.get() != 'ZZMI':
            
            # Tweaks
            self.put(TweaksLabel(self)).grid(row=5, column=0, padx=(20, 10), pady=(0, 30), sticky='w')
    
            tweaks_frame = UIFrame(self, fg_color=master._fg_color)
            tweaks_frame.grid(row=5, column=1, padx=(0, 0), pady=(0, 30), sticky='we', columnspan=3)
            tweaks_frame.put(UnlockFPSCheckbox(tweaks_frame)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
    
            # Window mode for GI FPS Unlocker
            if Vars.Launcher.active_importer.get() == 'GIMI':
                tweaks_frame.put(UnlockFPSWindowOptionMenu(tweaks_frame)).grid(row=0, column=1, padx=(20, 10), pady=(0, 0), sticky='w')
                tweaks_frame.put(EnableHDR(tweaks_frame)).grid(row=0, column=2, padx=(60, 10), pady=(0, 0), sticky='w')
    
            #  Performance Tweaks
            if Vars.Launcher.active_importer.get() == 'WWMI':
                tweaks_frame.put(ApplyTweaksCheckbox(tweaks_frame)).grid(row=0, column=1, padx=(20, 10), pady=(0, 0), sticky='w')
                tweaks_frame.put(OpenEngineIniButton(tweaks_frame)).grid(row=0, column=2, padx=(10, 20), pady=(0, 0), sticky='e')


class LanguageLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.language'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class LanguageOptionMenu(UIOptionMenu):
    def __init__(self, master):
        self.language_options = I18n.I18n.get_language_options()
        # 创建双向映射
        self.language_codes = {name: code for code, name in self.language_options.items()}
        self.language_names = {code: name for code, name in self.language_options.items()}
        
        super().__init__(
            values=list(self.language_options.values()),
            variable=Vars.I18nSettings.language,
            width=150,
            dynamic_resizing=True,
            command=self.on_language_change,
            master=master)
        self.set_tooltip(I18n._('settings.language_tooltip'))

        current_lang = Vars.I18nSettings.language.get()
        if current_lang in self.language_names:
            self.set(self.language_names[current_lang])
        elif current_lang in self.language_codes:
            lang_code = self.language_codes[current_lang]
            ars.I18nSettings.language.set(self.language_names[lang_code])
            self.set(current_lang)
        else:
            Vars.I18nSettings.language.set(self.language_names['en'])
            self.set(self.language_names['en'])
    
    def on_language_change(self, value):
        if value in self.language_codes:
            lang_code = self.language_codes[value]
            Vars.I18nSettings.language.set(value)
            I18n.I18n.set_language(lang_code)
            Events.Fire(Events.Application.ShowInfo(
                title=I18n._('settings.language_change'),
                message=I18n._('settings.language_change_restart')
            ))


class GameFolderFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            border_color = ThemeManager.theme["CTkEntry"].get("border_color", None),
            border_width = ThemeManager.theme["CTkEntry"].get("border_width", None),
            fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None),
            master=master)

        self.grid_columnconfigure(0, weight=100)

        game_folder_error = master.put(GameFolderErrorLabel(master))

        self.put(GameFolderEntry(self, game_folder_error)).grid(row=0, column=0, padx=(4, 0), pady=(2, 0), sticky='new')
        self.put(ChangeGameFolderButton(self)).grid(row=0, column=1, padx=(0, 4), pady=(2, 2), sticky='ne')


class LaunchOptionsFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            border_color = ThemeManager.theme["CTkEntry"].get("border_color", None),
            border_width = ThemeManager.theme["CTkEntry"].get("border_width", None),
            fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None),
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(LaunchOptionsEntry(self)).grid(row=0, column=0, padx=(4, 0), pady=(2, 2), sticky='ew')
        self.put(LaunchOptionsButton(self)).grid(row=0, column=1, padx=(0, 4), pady=(2, 2), sticky='e')


class AutoConfigFrame(UIFrame):
    def __init__(self, master):
        super().__init__(
            fg_color = 'transparent',
            master=master)

        self.grid_columnconfigure(0, weight=100)

        self.put(ConfigureGameCheckbox(self)).grid(row=0, column=0, padx=(0, 10), pady=(0, 0), sticky='w')
        
        if Vars.Launcher.active_importer.get() == 'WWMI':
            self.put(DisableWoundedEffectCheckbox(self)).grid(row=0, column=1, padx=(10, 20), pady=(0, 0), sticky='w')


class GameFolderLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.game_folder'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class GameFolderEntry(UIEntry):
    def __init__(self, master, error_label: UILabel):
        super().__init__(
            textvariable=Vars.Active.Importer.game_folder,
            width=200,
            height=32,
            border_width=0,
            font=('Arial', 14),
            master=master)
        self.normal_border_color = self._border_color
        self.error_label = error_label
        self.configure(validate='all', validatecommand=(master.register(self.validate_game_folder), '%P'))
        self.set_tooltip(self.get_tooltip)
        self.validate_game_folder(Vars.Active.Importer.game_folder.get())

    def validate_game_folder(self, game_folder):
        try:
            game_path = Events.Call(Events.ModelImporter.ValidateGameFolder(game_folder=game_folder.strip()))
        except Exception as e:
            self.error_label.configure(text=str(e))
            self.error_label.grid(row=0, column=1, padx=(0, 15), pady=(36, 0), sticky='nwe')
            self.master.configure(border_color='#db3434')
            return True
        self.master.configure(border_color=self.normal_border_color)
        self.error_label.grid_forget()
        return True

    def get_tooltip(self):
        if Config.Launcher.active_importer == 'WWMI':
            return I18n._('tooltip.game_folder_wwmi')
        if Config.Launcher.active_importer == 'ZZMI':
            return I18n._('tooltip.game_folder_zzmi')
        if Config.Launcher.active_importer == 'SRMI':
            return I18n._('tooltip.game_folder_srmi')
        if Config.Launcher.active_importer == 'GIMI':
            return I18n._('tooltip.game_folder_gimi')
        return ''


class GameFolderErrorLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.game_folder_error'),
            font=('Microsoft YaHei', 14, 'bold'),
            text_color='#ff3636',
            fg_color='transparent',
            master=master)


class ChangeGameFolderButton(UIButton):
    def __init__(self, master):
        fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None)
        super().__init__(
            text=I18n._('buttons.browse'),
            command=self.change_game_folder,
            auto_width=True,
            padx=6,
            height=32,
            border_width=0,
            font=('Roboto', 14),
            fg_color=fg_color,
            hover_color=fg_color,
            text_color=["#000000", "#aaaaaa"],
            text_color_hovered=["#000000", "#ffffff"],
            master=master)

    def change_game_folder(self):
        game_folder = filedialog.askdirectory(initialdir=Vars.Active.Importer.game_folder.get())
        if game_folder == '':
            return
        Vars.Active.Importer.game_folder.set(game_folder)


class DetectGameFolderButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text=I18n._('buttons.detect'),
            command=self.detect_game_folder,
            width = 36,
            height=36,
            font=('Asap', 18),
            master=master)

        self.set_tooltip(I18n._('tooltip.detect_game_folder'))

    def detect_game_folder(self):
        try:
            game_folder, game_path, game_exe_path = Events.Call(Events.ModelImporter.DetectGameFolder())
            Vars.Active.Importer.game_folder.set(str(game_path))
            Config.Active.Importer.game_folder = str(game_path)
        except:
            pass


class LaunchOptionsLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.launch_options'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class LaunchOptionsEntry(UIEntry):
    def __init__(self, master):
        super().__init__(
            textvariable=Vars.Active.Importer.launch_options,
            width=200,
            height=32,
            border_width=0,
            font=('Arial', 14),
            master=master)
        self.set_tooltip(I18n._('tooltip.launch_options_tooltip'))


class LaunchOptionsButton(UIButton):
    def __init__(self, master):
        fg_color = ThemeManager.theme["CTkEntry"].get("fg_color", None)
        super().__init__(
            text="?",
            command=self.open_docs,
            auto_width=True,
            padx=6,
            height=32,
            border_width=0,
            font=('Roboto', 14),
            fg_color=fg_color,
            hover_color=fg_color,
            text_color=["#000000", "#aaaaaa"],
            text_color_hovered=["#000000", "#ffffff"],
            master=master)
        
        self.set_tooltip(I18n._('tooltip.launch_options_docs'))

    def open_docs(self):
        if Config.Launcher.active_importer == 'WWMI':
            webbrowser.open('https://dev.epicgames.com/documentation/en-us/unreal-engine/command-line-arguments?application_version=4.27')
        elif Config.Launcher.active_importer in ['GIMI', 'SRMI', 'ZZMI']:
            webbrowser.open('https://docs.unity3d.com/Manual/PlayerCommandLineArguments.html')


class ProcessPriorityLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.process_priority'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class ProcessPriorityOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Normal', 'Above Normal', 'High'],
            variable=Vars.Active.Importer.process_priority,
            width=150,
            dynamic_resizing=True,
            master=master)
        self.set_tooltip(I18n._('tooltip.process_priority'))


class AutoConfigLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.auto_config'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class ConfigureGameCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.configure_game'),
            variable=Vars.Active.Importer.configure_game,
            master=master)
        
        self.set_tooltip(self.get_tooltip)

    def get_tooltip(self):
        if Config.Launcher.active_importer == 'WWMI':
            return I18n._('tooltip.configure_game_wwmi')
        
        if Config.Launcher.active_importer == 'ZZMI':
            return I18n._('tooltip.configure_game_zzmi')
        
        if Config.Launcher.active_importer == 'SRMI':
            return I18n._('tooltip.configure_game_srmi')
        
        if Config.Launcher.active_importer == 'GIMI':
            return I18n._('tooltip.configure_game_gimi')
        
        return ''


class OpenEngineIniButton(UIButton):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.open_engine_ini'),
            command=self.open_engine_ini,
            width = 150,
            height=36,
            font=('Asap', 14),
            master=master)

    def open_engine_ini(self):
        game_folder = Vars.Active.Importer.game_folder.get()
        engine_ini = f"{game_folder}\\Engine\\Config\\Engine.ini"
        
        try:
            engine_ini_path = Path(engine_ini)
            if not engine_ini_path.exists():
                return
            subprocess.run(f'explorer /select,"{engine_ini_path.absolute()}"', check=True)
        except Exception as e:
            print(e)


class TweaksLabel(UILabel):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.tweaks'),
            font=('Microsoft YaHei', 14, 'bold'),
            fg_color='transparent',
            master=master)


class UnlockFPSCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.force_120_fps'),
            variable=Vars.Active.Importer.unlock_fps,
            master=master)
        self.set_tooltip(self.get_tooltip)
    
    def get_tooltip(self):
        if Config.Launcher.active_importer == 'WWMI':
            return I18n._('tooltip.unlock_fps_wwmi')
        
        if Config.Launcher.active_importer == 'SRMI':
            return I18n._('tooltip.unlock_fps_srmi')
        
        if Config.Launcher.active_importer == 'GIMI':
            return I18n._('tooltip.unlock_fps_gimi')
        
        return ""


class UnlockFPSWindowOptionMenu(UIOptionMenu):
    def __init__(self, master):
        super().__init__(
            values=['Fullscreen', 'Borderless', 'Window'],
            variable=Vars.Active.Importer.window_mode,
            width=150,
            dynamic_resizing=True,
            master=master)
        
        self.set_tooltip(I18n._('tooltip.unlock_fps_window_mode'))
        
        self.trace_write(Vars.Active.Importer.unlock_fps, self.handle_write_unlock_fps)
        
    def handle_write_unlock_fps(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')


class ApplyTweaksCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.apply_tweaks'),
            variable=Vars.Active.Importer.apply_perf_tweaks,
            master=master)
        
        self.set_tooltip(I18n._('tooltip.apply_tweaks'))


class EnableHDR(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.enable_hdr'),
            variable=Vars.Active.Importer.enable_hdr,
            master=master)
        
        self.set_tooltip(I18n._('tooltip.enable_hdr'))


class DisableWoundedEffectCheckbox(UICheckbox):
    def __init__(self, master):
        super().__init__(
            text=I18n._('settings.disable_wounded'),
            variable=Vars.Active.Importer.disable_wounded_fx,
            master=master)
        
        self.set_tooltip(I18n._('tooltip.disable_wounded_effect'))
        
        self.trace_write(Vars.Active.Importer.configure_game, self.handle_write_configure_game)
    
    def handle_write_configure_game(self, var, val):
        if val:
            self.configure(state='normal')
        else:
            self.configure(state='disabled')
