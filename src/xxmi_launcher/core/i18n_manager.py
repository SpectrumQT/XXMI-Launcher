import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
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
        if not self.available_languages:
            # 如果没有找到语言文件，创建默认的英文文件
            self._create_default_english()
            self.available_languages = ["en"]
        
        # 确保当前语言在可用语言列表中
        if self.current_language not in self.available_languages:
            self.current_language = self.available_languages[0]
            
        log.debug(f"Available languages: {self.available_languages}")
        log.debug(f"Current language: {self.current_language}")
    
    def _create_default_english(self):
        """创建默认的英文翻译文件"""
        i18n_path = Paths.App.Resources / 'i18n'
        en_file = i18n_path / 'en.json'
        
        if not en_file.exists():
            log.debug("Creating default English translation file")
            self._create_translation_file('en')
    
    def _create_translation_file(self, lang_code):
        """创建翻译文件模板"""
        i18n_path = Paths.App.Resources / 'i18n'
        lang_file = i18n_path / f'{lang_code}.json'
        
        # 创建一个空的翻译文件结构
        empty_translations = {
            "settings": {
                "title": "",
                "language": "",
                "language_tooltip": "",
                "game_folder": "",
                "launch_options": "",
                "process_priority": "",
                "auto_config": "",
                "tweaks": "",
                "general_tab": "",
                "launcher_tab": "",
                "advanced_tab": "",
                "language_change": "",
                "language_change_restart": ""
            },
            "buttons": {
                "save": "",
                "cancel": "",
                "close": "",
                "browse": "",
                "detect": ""
            }
        }
        
        # 为英文和中文提供默认翻译
        if lang_code == 'en':
            empty_translations = {
                "settings": {
                    "title": "Settings",
                    "language": "Language",
                    "language_tooltip": "Change the display language",
                    "game_folder": "Game Folder:",
                    "launch_options": "Launch Options:",
                    "process_priority": "Process Priority:",
                    "auto_config": "Auto Config:",
                    "tweaks": "Tweaks:",
                    "general_tab": "General",
                    "launcher_tab": "Launcher",
                    "advanced_tab": "Advanced",
                    "language_change": "Language Changed",
                    "language_change_restart": "Please restart the application to fully apply the language change."
                },
                "buttons": {
                    "save": "Save",
                    "cancel": "Cancel",
                    "close": "Close",
                    "browse": "Browse...",
                    "detect": "⟳"
                }
            }
        elif lang_code == 'zh':
            empty_translations = {
                "settings": {
                    "title": "设置",
                    "language": "语言",
                    "language_tooltip": "更改显示语言",
                    "game_folder": "游戏文件夹:",
                    "launch_options": "启动选项:",
                    "process_priority": "进程优先级:",
                    "auto_config": "自动配置:",
                    "tweaks": "调整:",
                    "general_tab": "常规",
                    "launcher_tab": "启动器",
                    "advanced_tab": "高级",
                    "language_change": "语言已更改",
                    "language_change_restart": "请重启应用程序以完全应用语言更改。"
                },
                "buttons": {
                    "save": "保存",
                    "cancel": "取消",
                    "close": "关闭",
                    "browse": "浏览...",
                    "detect": "⟳"
                }
            }
        
        with open(lang_file, 'w', encoding='utf-8') as f:
            json.dump(empty_translations, f, indent=4, ensure_ascii=False)
        
        self.translations[lang_code] = empty_translations
    
    def create_chinese_translation(self):
        """创建中文翻译文件"""
        i18n_path = Paths.App.Resources / 'i18n'
        zh_file = i18n_path / 'zh.json'
        
        if not zh_file.exists():
            log.debug("Creating Chinese translation file")
            self._create_translation_file('zh')
            
        if "zh" not in self.available_languages:
            self.available_languages.append("zh")
    
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
            # 如果键为空，返回空字符串
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
                            # 如果在英文中也没有找到，记录缺失的键并返回键名
                            log.warning(f"Missing translation key: {key}")
                            return key
                    if isinstance(en_current, str):
                        return en_current
                
                # 如果在英文中也没有找到或当前语言就是英文，记录缺失的键
                log.warning(f"Missing translation key: {key}")
                # 返回键名作为默认值
                return key
        
        if isinstance(current, str):
            return current
        
        # 如果解析到的不是字符串（可能是嵌套对象），返回键名
        log.warning(f"Translation key {key} resolves to a non-string value")
        return key
    
    def get_language_name(self, lang_code: str) -> str:
        """获取语言的本地化名称"""
        language_names = {
            "en": "English",
            "zh": "中文"
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