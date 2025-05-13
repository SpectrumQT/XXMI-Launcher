import os
import json
import logging
from pathlib import Path
from typing import Dict
from dataclasses import dataclass

import core.path_manager as Paths

log = logging.getLogger(__name__)

@dataclass
class I18nConfig:
    """国际化配置类，用于存储应用程序的语言设置"""
    language: str = "en"

class I18nManager:
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language = "en"
        self.available_languages = []

    def initialize(self):
        """初始化翻译管理器，加载所有可用的语言文件"""
        self.translations = {}

        # 确保i18n目录存在
        i18n_path = Paths.App.Resources / 'i18n'
        Paths.verify_path(i18n_path)

        # 加载所有语言文件
        for lang_file in i18n_path.glob('*.json'):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
                log.debug(f"Loaded language: {lang_code}")
            except Exception as e:
                log.error(f"Failed to load language {lang_code}: {e}")

        # 更新可用语言列表
        self.available_languages = list(self.translations.keys())

        # 确保当前语言在可用语言列表中
        if self.current_language not in self.available_languages:
            self.current_language = self.available_languages[0]

        log.debug(f"Available languages: {self.available_languages}")
        log.debug(f"Current language: {self.current_language}")

    def set_language(self, lang_code: str) -> bool:
        """设置当前语言"""
        if lang_code in self.available_languages:
            self.current_language = lang_code
            log.debug(f"Language changed to: {lang_code}")
            return True
        return False

    def get(self, key: str, default: str = None) -> str:
        """获取指定键的翻译"""
        if not key:
            return ""

        # 支持嵌套键，如 "settings.title"
        parts = key.split('.')
        current = self.translations.get(self.current_language, {})

        for part in parts:
            if part in current:
                current = current[part]
            else:
                # 如果在当前语言中没有找到翻译，尝试在英文中查找
                if self.current_language != "en":
                    en_current = self.translations.get("en", {})
                    for en_part in parts:
                        if en_part in en_current:
                            en_current = en_current[en_part]
                        else:
                            log.warning(f"Missing translation key: {key}")
                            return key
                    if isinstance(en_current, str):
                        return en_current

                log.warning(f"Missing translation key: {key}")
                return key

        if isinstance(current, str):
            return current

        log.warning(f"Translation key {key} resolves to a non-string value")
        return key

    def get_language_name(self, lang_code: str) -> str:
        """获取语言的本地化名称"""
        language_names = {
            "zh": "简体中文",
            "ja": "日本語",
            "en": "English",
            "ko": "한국어"
        }
        return language_names.get(lang_code, lang_code)

    def get_language_options(self) -> Dict[str, str]:
        """获取语言选项，用于下拉菜单"""
        return {code: self.get_language_name(code) for code in self.available_languages}

# 全局实例
I18n = I18nManager()

def _(key: str) -> str:
    """翻译函数的简写，不接受default参数"""
    return I18n.get(key)