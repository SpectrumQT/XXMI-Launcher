# Licensed under the GPLv3 License
# XXMI Launcher - Mod Manager Module
# Integrated mod management functionality inspired by d3dxSkinManage

import logging
import os
import shutil
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class ModInfo:
    """Mod information data structure"""
    sha: str
    name: str
    object_name: str  # Character/weapon name this mod applies to
    author: str = ""
    category: str = "Uncategorized"
    description: str = ""
    preview_image: Optional[Path] = None
    enabled: bool = False
    tags: List[str] = field(default_factory=list)


class ModManager:
    """
    Mod manager for 3DMigoto mods in XXMI Launcher
    Provides enable/disable, categorization, and metadata management
    """
    
    DISABLED_PREFIX = "DISABLED-"
    
    def __init__(self, mods_folder: Path):
        """
        Initialize mod manager
        
        Args:
            mods_folder: Path to the Mods folder containing mod directories
        """
        self.mods_folder = Path(mods_folder)
        self._lock = threading.RLock()
        
        # Cache structures
        self._mods_cache: Dict[str, ModInfo] = {}  # SHA -> ModInfo
        self._enabled_mods: Dict[str, str] = {}  # object_name -> SHA
        self._categories: Dict[str, List[str]] = {}  # category -> [object_names]
        self._initialized = False
        
    def initialize(self):
        """Initialize mod manager and scan for mods"""
        with self._lock:
            if self._initialized:
                return
                
            log.info("Initializing mod manager...")
            self._scan_mods()
            self._initialized = True
            log.info(f"Mod manager initialized. Found {len(self._mods_cache)} mods.")
    
    def _scan_mods(self):
        """Scan mods folder and build mod cache"""
        if not self.mods_folder.exists():
            log.warning(f"Mods folder does not exist: {self.mods_folder}")
            return
            
        self._mods_cache.clear()
        self._enabled_mods.clear()
        
        for item in self.mods_folder.iterdir():
            if not item.is_dir():
                continue
                
            # Check if mod is disabled
            mod_name = item.name
            is_disabled = mod_name.startswith(self.DISABLED_PREFIX)
            sha = mod_name[len(self.DISABLED_PREFIX):] if is_disabled else mod_name
            
            # Try to load mod metadata
            mod_info = self._load_mod_info(item, sha, not is_disabled)
            if mod_info:
                self._mods_cache[sha] = mod_info
                if mod_info.enabled:
                    self._enabled_mods[mod_info.object_name] = sha
                    
        self._build_categories()
    
    def _load_mod_info(self, mod_path: Path, sha: str, enabled: bool) -> Optional[ModInfo]:
        """
        Load mod information from mod folder
        
        Args:
            mod_path: Path to mod folder
            sha: SHA identifier
            enabled: Whether mod is currently enabled
            
        Returns:
            ModInfo object or None if invalid
        """
        # Look for mod.json or similar metadata file
        metadata_file = mod_path / "mod.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                return ModInfo(
                    sha=sha,
                    name=data.get('name', sha),
                    object_name=data.get('object', data.get('character', 'Unknown')),
                    author=data.get('author', ''),
                    category=data.get('category', 'Uncategorized'),
                    description=data.get('description', ''),
                    preview_image=mod_path / data['preview'] if 'preview' in data else None,
                    enabled=enabled,
                    tags=data.get('tags', [])
                )
            except Exception as e:
                log.warning(f"Failed to load metadata for {sha}: {e}")
        
        # Fallback: Create basic mod info from folder name
        # Try to extract object name from .ini files
        object_name = self._detect_object_name(mod_path)
        
        return ModInfo(
            sha=sha,
            name=sha,
            object_name=object_name or 'Unknown',
            enabled=enabled
        )
    
    def _detect_object_name(self, mod_path: Path) -> Optional[str]:
        """
        Try to detect object/character name from mod files
        
        Args:
            mod_path: Path to mod folder
            
        Returns:
            Detected object name or None
        """
        # Look for .ini files that might contain object info
        for ini_file in mod_path.glob('*.ini'):
            try:
                with open(ini_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Look for common patterns in mod .ini files
                    # This is a simple heuristic and may need refinement
                    if 'character' in content.lower():
                        # Try to extract character name
                        for line in content.split('\n'):
                            if 'character' in line.lower() and '=' in line:
                                parts = line.split('=')
                                if len(parts) > 1:
                                    return parts[1].strip().strip('"\'')
            except Exception:
                continue
        
        return None
    
    def _build_categories(self):
        """Build category index from mods"""
        self._categories.clear()
        
        for mod_info in self._mods_cache.values():
            category = mod_info.category
            if category not in self._categories:
                self._categories[category] = []
            if mod_info.object_name not in self._categories[category]:
                self._categories[category].append(mod_info.object_name)
    
    def get_all_mods(self) -> List[ModInfo]:
        """Get list of all mods"""
        with self._lock:
            return list(self._mods_cache.values())
    
    def get_mod(self, sha: str) -> Optional[ModInfo]:
        """Get specific mod by SHA"""
        with self._lock:
            return self._mods_cache.get(sha)
    
    def get_enabled_mod_for_object(self, object_name: str) -> Optional[ModInfo]:
        """Get currently enabled mod for an object"""
        with self._lock:
            sha = self._enabled_mods.get(object_name)
            return self._mods_cache.get(sha) if sha else None
    
    def get_mods_by_category(self, category: str) -> List[ModInfo]:
        """Get all mods in a category"""
        with self._lock:
            object_names = self._categories.get(category, [])
            mods = []
            for mod_info in self._mods_cache.values():
                if mod_info.object_name in object_names:
                    mods.append(mod_info)
            return mods
    
    def get_categories(self) -> List[str]:
        """Get list of all categories"""
        with self._lock:
            return list(self._categories.keys())
    
    def enable_mod(self, sha: str) -> bool:
        """
        Enable a mod
        
        Args:
            sha: SHA identifier of mod to enable
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            mod_info = self._mods_cache.get(sha)
            if not mod_info:
                log.error(f"Mod not found: {sha}")
                return False
            
            if mod_info.enabled:
                log.info(f"Mod already enabled: {sha}")
                return True
            
            # Disable any conflicting mod for the same object
            if mod_info.object_name in self._enabled_mods:
                conflicting_sha = self._enabled_mods[mod_info.object_name]
                if conflicting_sha != sha:
                    self.disable_mod(conflicting_sha)
            
            # Rename folder to remove DISABLED prefix
            disabled_path = self.mods_folder / f"{self.DISABLED_PREFIX}{sha}"
            enabled_path = self.mods_folder / sha
            
            try:
                if disabled_path.exists():
                    disabled_path.rename(enabled_path)
                    mod_info.enabled = True
                    self._enabled_mods[mod_info.object_name] = sha
                    log.info(f"Enabled mod: {sha}")
                    return True
                else:
                    log.error(f"Mod folder not found: {disabled_path}")
                    return False
            except Exception as e:
                log.error(f"Failed to enable mod {sha}: {e}")
                return False
    
    def disable_mod(self, sha: str) -> bool:
        """
        Disable a mod
        
        Args:
            sha: SHA identifier of mod to disable
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            mod_info = self._mods_cache.get(sha)
            if not mod_info:
                log.error(f"Mod not found: {sha}")
                return False
            
            if not mod_info.enabled:
                log.info(f"Mod already disabled: {sha}")
                return True
            
            # Rename folder to add DISABLED prefix
            enabled_path = self.mods_folder / sha
            disabled_path = self.mods_folder / f"{self.DISABLED_PREFIX}{sha}"
            
            try:
                if enabled_path.exists():
                    enabled_path.rename(disabled_path)
                    mod_info.enabled = False
                    if mod_info.object_name in self._enabled_mods:
                        del self._enabled_mods[mod_info.object_name]
                    log.info(f"Disabled mod: {sha}")
                    return True
                else:
                    log.error(f"Mod folder not found: {enabled_path}")
                    return False
            except Exception as e:
                log.error(f"Failed to disable mod {sha}: {e}")
                return False
    
    def toggle_mod(self, sha: str) -> bool:
        """Toggle mod enabled/disabled state"""
        with self._lock:
            mod_info = self._mods_cache.get(sha)
            if not mod_info:
                return False
            
            if mod_info.enabled:
                return self.disable_mod(sha)
            else:
                return self.enable_mod(sha)
    
    def refresh(self):
        """Refresh mod cache by rescanning mods folder"""
        with self._lock:
            log.info("Refreshing mod manager...")
            self._scan_mods()
            log.info(f"Mod manager refreshed. Found {len(self._mods_cache)} mods.")
    
    def delete_mod(self, sha: str) -> bool:
        """
        Delete a mod permanently
        
        Args:
            sha: SHA identifier of mod to delete
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            mod_info = self._mods_cache.get(sha)
            if not mod_info:
                log.error(f"Mod not found: {sha}")
                return False
            
            # Determine which path to delete
            if mod_info.enabled:
                mod_path = self.mods_folder / sha
            else:
                mod_path = self.mods_folder / f"{self.DISABLED_PREFIX}{sha}"
            
            try:
                if mod_path.exists():
                    shutil.rmtree(mod_path)
                    del self._mods_cache[sha]
                    if mod_info.object_name in self._enabled_mods:
                        del self._enabled_mods[mod_info.object_name]
                    log.info(f"Deleted mod: {sha}")
                    self._build_categories()
                    return True
                else:
                    log.error(f"Mod folder not found: {mod_path}")
                    return False
            except Exception as e:
                log.error(f"Failed to delete mod {sha}: {e}")
                return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about mods"""
        with self._lock:
            return {
                'total': len(self._mods_cache),
                'enabled': len(self._enabled_mods),
                'disabled': len(self._mods_cache) - len(self._enabled_mods),
                'categories': len(self._categories)
            }
