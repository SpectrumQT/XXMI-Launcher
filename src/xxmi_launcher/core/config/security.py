import os
import logging

from typing import Any

import core.path_manager as Paths
from core.utils.security import Security

from core.config.model import AppConfig

log = logging.getLogger(__name__)


class AppConfigSecurity:
    def __init__(self, config: AppConfig):
        self.config = config
        self.security = Security()
        self.keys_path = Paths.App.Resources / "Security"

    @property
    def user(self) -> str:
        return os.getlogin()

    def is_key_pair_valid(self) -> bool:
        Paths.verify_path(self.keys_path)

        try:
            self.security.read_key_pair(self.keys_path)
        except Exception:
            return False

        return self.security.verify(self.config.Security.user_signature, self.user)

    def generate_key_pair(self):
        self.security.generate_key_pair()
        self.security.write_key_pair(self.keys_path)
        self.config.Security.user_signature = self.security.sign(self.user)

    def validate_config(self):
        config = self.config

        protected_settings = [
            config.Active.Migoto.unsafe_mode,
            config.Active.Importer.run_pre_launch,
            config.Active.Importer.custom_launch,
            config.Active.Importer.run_post_load,
            config.Active.Importer.extra_libraries,
        ]

        wrong_signatures = {}

        if not any(protected_settings):
            return wrong_signatures

        if config.Active.Migoto.unsafe_mode:
            if not self.security.verify(config.Active.Migoto.unsafe_mode_signature, self.user):
                wrong_signatures["Unsafe Mode"] = "Enabled"

        if config.Active.Importer.run_pre_launch:
            if not self.security.verify(config.Active.Importer.run_pre_launch_signature,
                                        config.Active.Importer.run_pre_launch.encode()):
                wrong_signatures["Run Pre Launch"] = config.Active.Importer.run_pre_launch

        if config.Active.Importer.custom_launch:
            if not self.security.verify(config.Active.Importer.custom_launch_signature,
                                        config.Active.Importer.custom_launch.encode()):
                wrong_signatures["Custom Launch"] = config.Active.Importer.custom_launch

        if config.Active.Importer.run_post_load:
            if not self.security.verify(config.Active.Importer.run_post_load_signature,
                                        config.Active.Importer.run_post_load.encode()):
                wrong_signatures["Run Post Load"] = config.Active.Importer.run_post_load

        if config.Active.Importer.extra_libraries:
            if not self.security.verify(config.Active.Importer.extra_libraries_signature,
                                        config.Active.Importer.extra_libraries.encode()):
                wrong_signatures["Extra Libraries"] = config.Active.Importer.extra_libraries

        return wrong_signatures

    def reset_invalid_settings(self, wrong_signatures: dict[str, Any]):
        config = self.config
        if "Unsafe Mode" in wrong_signatures:
            config.Active.Migoto.unsafe_mode = False
        if "Run Pre Launch" in wrong_signatures:
            config.Active.Importer.run_pre_launch = ""
        if "Custom Launch" in wrong_signatures:
            config.Active.Importer.custom_launch = ""
        if "Run Post Load" in wrong_signatures:
            config.Active.Importer.run_post_load = ""
        if "Extra Libraries" in wrong_signatures:
            config.Active.Importer.extra_libraries = ""

    def sign_settings(self):
        config = self.config
        if config.Active.Migoto.unsafe_mode:
            config.Active.Migoto.unsafe_mode_signature = self.security.sign(self.user)
        if config.Active.Importer.run_pre_launch:
            config.Active.Importer.run_pre_launch_signature = self.security.sign(config.Active.Importer.run_pre_launch.encode())
        if config.Active.Importer.custom_launch:
            config.Active.Importer.custom_launch_signature = self.security.sign(config.Active.Importer.custom_launch.encode())
        if config.Active.Importer.run_post_load:
            config.Active.Importer.run_post_load_signature = self.security.sign(config.Active.Importer.run_post_load.encode())
        if config.Active.Importer.extra_libraries:
            config.Active.Importer.extra_libraries_signature = self.security.sign(config.Active.Importer.extra_libraries.encode())
