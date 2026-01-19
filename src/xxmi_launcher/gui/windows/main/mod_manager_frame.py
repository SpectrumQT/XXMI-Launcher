# Licensed under the GPLv3 License
# XXMI Launcher - Mod Manager GUI Frame

import logging
from pathlib import Path

import core.event_manager as Events
import core.config_manager as Config
from gui.classes.containers import UIFrame
from gui.classes.widgets import UIButton, UIText, UIScrollableFrame

log = logging.getLogger(__name__)


class ModManagerFrame(UIFrame):
    """
    GUI frame for managing 3DMigoto mods
    Displays mod list with enable/disable functionality
    """
    
    def __init__(self, master, canvas, **kwargs):
        super().__init__(master, canvas, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Title
        title_text = UIText(
            self, 
            text="Mod Manager",
            font_size=24,
            font_weight='bold'
        )
        title_text.grid(row=0, column=0, padx=20, pady=(20, 10), sticky='w')
        
        # Mod list scrollable frame
        self.mod_list_frame = UIScrollableFrame(
            self,
            width=700,
            height=500,
            fg_color='transparent'
        )
        self.mod_list_frame.grid(row=1, column=0, padx=20, pady=10, sticky='nsew')
        
        # Refresh button
        refresh_btn = UIButton(
            self,
            text="Refresh Mods",
            command=self.refresh_mods
        )
        refresh_btn.grid(row=2, column=0, padx=20, pady=10, sticky='e')
        
        # Stats text
        self.stats_text = UIText(
            self,
            text="",
            font_size=12
        )
        self.stats_text.grid(row=3, column=0, padx=20, pady=(0, 20), sticky='w')
        
        # Subscribe to mod events
        self.subscribe(Events.Application.ConfigUpdate, lambda e: self.load_mods())
        self.subscribe(Events.Application.LoadImporter, lambda e: self.load_mods())
        
        # Load mods initially
        self.load_mods()
    
    def get_mod_manager(self):
        """Get the active mod manager instance"""
        try:
            if not hasattr(Config, 'Active'):
                return None
            
            # Get the active importer package from application
            from core.application import Application
            if hasattr(self.master, 'app') and hasattr(self.master.app, 'package_manager'):
                package = self.master.app.package_manager.get_package(Config.Launcher.active_importer)
                if hasattr(package, 'mod_manager'):
                    return package.mod_manager
        except Exception as e:
            log.warning(f"Failed to get mod manager: {e}")
        
        return None
    
    def load_mods(self):
        """Load and display mods from mod manager"""
        # Clear existing mod widgets
        for widget in self.mod_list_frame.winfo_children():
            widget.destroy()
        
        mod_manager = self.get_mod_manager()
        
        if not mod_manager:
            # Show message when no mod manager available
            no_mods_text = UIText(
                self.mod_list_frame,
                text="No model importer selected or mod manager not initialized.\n\n"
                     "Please select a game and ensure it is installed to manage mods.",
                font_size=14,
                text_color='gray'
            )
            no_mods_text.pack(padx=20, pady=50)
            self.stats_text.configure(text="")
            return
        
        # Get all mods
        all_mods = mod_manager.get_all_mods()
        
        if not all_mods:
            no_mods_text = UIText(
                self.mod_list_frame,
                text="No mods found in Mods folder.\n\n"
                     "Place mod folders in the Mods directory to manage them here.",
                font_size=14,
                text_color='gray'
            )
            no_mods_text.pack(padx=20, pady=50)
            self.stats_text.configure(text="No mods found")
            return
        
        # Group mods by category
        categories = mod_manager.get_categories()
        
        for category in sorted(categories):
            # Category header
            category_header = UIText(
                self.mod_list_frame,
                text=category,
                font_size=16,
                font_weight='bold'
            )
            category_header.pack(padx=10, pady=(15, 5), anchor='w')
            
            # Get mods in this category
            category_mods = mod_manager.get_mods_by_category(category)
            
            for mod in sorted(category_mods, key=lambda m: m.name):
                # Create mod item frame
                mod_item = ModItemWidget(
                    self.mod_list_frame,
                    mod=mod,
                    toggle_callback=lambda sha=mod.sha: self.toggle_mod(sha)
                )
                mod_item.pack(padx=10, pady=2, fill='x')
        
        # Update stats
        stats = mod_manager.get_stats()
        stats_text = f"Total: {stats['total']} | Enabled: {stats['enabled']} | Disabled: {stats['disabled']} | Categories: {stats['categories']}"
        self.stats_text.configure(text=stats_text)
    
    def toggle_mod(self, sha: str):
        """Toggle mod enabled/disabled state"""
        Events.Fire(Events.ModelImporter.ToggleMod(sha=sha))
        # Reload mods to reflect changes
        self.after(100, self.load_mods)
    
    def refresh_mods(self):
        """Refresh mod list"""
        Events.Fire(Events.ModelImporter.RefreshMods())
        self.load_mods()


class ModItemWidget(UIFrame):
    """Widget representing a single mod in the list"""
    
    def __init__(self, master, mod, toggle_callback, **kwargs):
        super().__init__(master, **kwargs)
        
        self.mod = mod
        self.toggle_callback = toggle_callback
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        
        # Status indicator (enabled/disabled)
        status_color = '#00ff00' if mod.enabled else '#888888'
        status_indicator = UIFrame(
            self,
            width=10,
            height=30,
            fg_color=status_color
        )
        status_indicator.grid(row=0, column=0, padx=(5, 10), pady=5)
        
        # Mod info text
        mod_text = f"{mod.name}"
        if mod.object_name != 'Unknown':
            mod_text += f" ({mod.object_name})"
        if mod.author:
            mod_text += f" - by {mod.author}"
        
        info_text = UIText(
            self,
            text=mod_text,
            font_size=12
        )
        info_text.grid(row=0, column=1, sticky='w', pady=5)
        
        # Toggle button
        button_text = "Disable" if mod.enabled else "Enable"
        toggle_btn = UIButton(
            self,
            text=button_text,
            width=80,
            command=self.toggle_callback
        )
        toggle_btn.grid(row=0, column=2, padx=10, pady=5)
