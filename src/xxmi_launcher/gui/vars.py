
import customtkinter

from typing import Union
from dataclasses import dataclass, field, fields

import core.event_manager as Events
import core.config_manager as Config

from core import package_manager
from core.packages import launcher_package
from core.packages.model_importers import wwmi_package
from core.packages.model_importers import zzmi_package


@dataclass
class AppSettings(Config.AppConfig):
    def __init__(self):
        super().__init__()
        self.cfg = None
        self.gui = None
        self.on_write_callbacks = {}
        self.on_save_callbacks = {}

    @property
    def Active(self):
        return Settings.Importers.__dict__[Config.Launcher.active_importer]

    def initialize(self, cfg, gui):
        self.gui = gui
        self.cfg = cfg
        self.on_write_callbacks = {}
        self.on_save_callbacks = {}
        self.initialize_vars()

    def initialize_vars(self):
        self.convert_vars(self)
        global Launcher
        Launcher = self.Launcher
        global Packages
        Packages = self.Packages
        global Importers
        Importers = self.Importers
        global Active
        Active = self.Active

    def subscribe_on_save(self, var, callback, caller_id=None):
        if not var._name in self.on_save_callbacks:
            self.on_save_callbacks[var._name] = {}
        callback_id = f'{caller_id.__class__}_{len(self.on_save_callbacks[var._name])}'
        self.on_save_callbacks[var._name][callback_id] = (var, callback, caller_id, None)
        return callback_id

    def subscribe_on_write(self, var, callback, caller_id=None):
        if not var._name in self.on_write_callbacks:
            self.on_write_callbacks[var._name] = {}
        callback_id = f'{caller_id.__class__}_{len(self.on_write_callbacks[var._name])}'
        trace_id = var.trace('w', lambda var_id, index, mode: callback(var, var.get()))
        self.on_write_callbacks[var._name][callback_id] = (var, callback, caller_id, trace_id)
        return callback_id

    def unsubscribe_on_write(self, callback_id=None, var=None, callback=None, caller_id=None):
        """
        Removes all callbacks for on_write subscribers, can be limited with params
        :param var: (optional) limits callback removal to provided variable
        :param callback: (optional) limits callback removal to provided callback
        :param caller_id: (optional) limits callback removal to provided caller_id
        """
        self._unsubscribe(self.on_write_callbacks, callback_id, var, callback, caller_id)

    def unsubscribe_on_save(self, callback_id=None, var=None, callback=None, caller_id=None):
        """
        Removes all callbacks for on_save subscribers, can be limited with params
        :param var: (optional) limits callback removal to provided variable
        :param callback: (optional) limits callback removal to provided callback
        :param caller_id: (optional) limits callback removal to provided caller_id
        """
        self._unsubscribe(self.on_save_callbacks, callback_id, var, callback, caller_id)

    def _unsubscribe(self, callbacks, callback_id=None, var=None, callback=None, caller_id=None):
        if var is not None:
            var_callbacks = callbacks.get(var._name, None)
            if var_callbacks is not None:
                self._unsubscribe_callbacks(var_callbacks, callback_id=callback_id, callback=callback, caller_id=caller_id)
        else:
            for var_callbacks in callbacks.values():
                self._unsubscribe_callbacks(var_callbacks, callback_id=callback_id, callback=callback, caller_id=caller_id)

    def _unsubscribe_callbacks(self, callbacks, callback_id=None, callback=None, caller_id=None):
        for del_callback_id, (del_var, del_callback, del_caller_id, del_trace_id) in list(callbacks.items()):
            if callback_id is not None and callback_id != del_callback_id:
                continue
            if callback is not None and callback != del_callback:
                continue
            if caller_id is not None and caller_id != del_caller_id:
                continue
            if del_trace_id is not None:
                del_var.trace_vdelete('w', del_trace_id)
            del callbacks[del_callback_id]

    def load(self):
        self.load_vars(self.cfg, self)

    def save(self):
        self.save_vars(self, self.cfg)
        Config.ConfigSecurity.sign_settings(save_config=False)
        Events.Fire(Events.Application.ConfigUpdate())

    def convert_vars(self, obj):
        for obj_field in fields(obj):
            value = getattr(obj, obj_field.name)
            if hasattr(value, '__dataclass_fields__'):
                self.convert_vars(value)
            elif isinstance(value, str | int | float | bool):
                var = self.convert_value(value)
                setattr(obj, obj_field.name, var)

    def convert_value(self, value):
        if isinstance(value, bool):
            return customtkinter.BooleanVar(master=self.gui, value=value)
        elif isinstance(value, str):
            return customtkinter.StringVar(master=self.gui, value=value)
        elif isinstance(value, int):
            return customtkinter.IntVar(master=self.gui, value=value)
        elif isinstance(value, float):
            return customtkinter.DoubleVar(master=self.gui, value=value)
        else:
            raise ValueError(f'Unsupported settings var type {type(value)}!')

    def load_vars(self, src, dst):
        if hasattr(dst, '__dataclass_fields__'):
            for dst_field in fields(dst):
                var = getattr(dst, dst_field.name)
                value = getattr(src, dst_field.name)
                if hasattr(value, '__dataclass_fields__'):
                    self.load_vars(value, var)
                elif isinstance(value, dict | list | tuple):
                    pass
                else:
                    var.set(value)
                    self.fire_on_write(var, value)

    def save_vars(self, src, dst):
        for dst_field in fields(dst):
            var = getattr(src, dst_field.name)
            value = getattr(dst, dst_field.name)
            if hasattr(value, '__dataclass_fields__'):
                self.save_vars(var, value)
            elif isinstance(value, str | int | float | bool):
                var_value = var.get()
                setattr(dst, dst_field.name, var_value)
                self.fire_on_save(var, var_value, value)

    def fire_on_save(self, var, new_value, old_value):
        callbacks = self.on_save_callbacks.get(var._name, None)
        if callbacks is not None:
            for callback_id, (cb_var, callback, caller_id, trace_id) in callbacks.items():
                callback(var, new_value, old_value)

    def fire_on_write(self, var, new_value):
        callbacks = self.on_write_callbacks.get(var._name, None)
        if callbacks is not None:
            for callback_id, (cb_var, callback, caller_id, trace_id) in callbacks.items():
                callback(var, new_value)


Settings: AppSettings = AppSettings()

# Settings aliases, intended to shorten dot names
Launcher: launcher_package.LauncherManagerConfig
Packages: package_manager.PackageManagerConfig
Importers: Config.ImportersConfig
Active: Union[wwmi_package.WWMIPackageConfig, zzmi_package.ZZMIPackageConfig]
