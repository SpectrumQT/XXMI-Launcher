<h1 align="center">XXMI Launcher</h1>

<h4 align="center">Launcher tool for XXMI</h4>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#included-model-importers">Model Importers</a> •
  <a href="#support-this-project">Support This Project</a> •
  <a href="#license">License</a>
</p>

## Disclaimers

- **Paranoia Warning** — Some picky AVs may trigger [false positives](https://learn.microsoft.com/en-us/defender-endpoint/defender-endpoint-false-positives-negatives) for XXMI **.exe** or **.dll** files. Project has no funds to [satisfy](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control) Microsoft's [endless greed](https://www.reddit.com/r/electronjs/comments/17sizjf/a_guide_to_code_signing_certificates_for_the/), so it's up to you to use them as is, build yourself or go by.

## Features

- **One Ring** — Allows to launch and manage all supported Model Importers in unified and convenient way
- **Plug-and-Play** — Configures any supported game and installs its XXMI instance automatically
- **Custom Launch** — Can be configured to start game in almost every possible way via Advanced Settings
- **Automatic Updates** — Always keeps XXMI instances and itself up-to date
- **Safe to Use** — Verifies authenticity of XXMI libraries and own downloads
- **Mod Manager** — Built-in visual mod management system for easy mod enable/disable and organization

![xxmi-launcher](https://github.com/SpectrumQT/XXMI-Launcher/blob/main/public-media/XXMI%20Launcher.jpg)

## Installation

> **Wuthering Waves Warning:** **Google Play Games** version is **not** supported currently.

### **Native Windows APP** (for **Windows** only)
  1. Download the [latest release](https://github.com/SpectrumQT/XXMI-Launcher/releases/latest) of **XXMI-Launcher-Installer-Online-vX.X.X.msi**
  2. Run **XXMI-Launcher-Installer-Online-vX.X.X.msi** with Double-Click.
  3. Click **[Quick Installation]** to install **XXMI Launcher** to the default location (`%AppData%\XXMI Launcher`) or use **[Custom Installation]** to set another folder.
  4. On the game selection page of **XXMI Launcher Window** click desired **Game Tile** to add **Model Importer Icon** to the top-left corner.
  5. Click **Model Importer Icon** to open Model Importer page and press **[Install]** button to download and install selected Model Importer.

### **Portable** (for **Windows** and **Linux** via **WINE 9.22+**)
  1. Download and install [the latest Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe).
  2. Download the [latest release](https://github.com/SpectrumQT/XXMI-Launcher/releases/latest) of **XXMI-Launcher-Portable-vX.X.X.zip**.
  3. Extract the archive to desired location (avoid Program Files folders!).
  4. Create shortcut for `Resources\Bin\XXMI Launcher.exe` for convenience and run it.
  5. On the game selection page of **XXMI Launcher Window** click desired **Game Tile** to add **Model Importer Icon** to the top-left corner.
  6. Click **Model Importer Icon** to open Model Importer page and press **[Install]** button to download and install selected Model Importer.

## Included Model Importers

- [WWMI - Wuthering Waves Model Importer GitHub](https://github.com/SpectrumQT/WWMI-Package)
- [ZZMI - Zenless Zone Zero Model Importer GitHub](https://github.com/leotorrez/ZZMI-Package)
- [SRMI - Star Rail Model Importer GitHub](https://github.com/SpectrumQT/SRMI-TEST) ([old repo](https://github.com/SilentNightSound/SR-Model-Importer))
- [GIMI - Genshin Impact Model Importer GitHub](https://github.com/SilentNightSound/GIMI-Package) ([old repo](https://github.com/SilentNightSound/GI-Model-Importer))
- [HIMI - Honkai Impact Model Importer GitHub](https://github.com/leotorrez/HIMI-Package) ([old repo](https://github.com/SilentNightSound/HI-Model-Importer))
  
## Support This Project

**XXMI Project** is result of collaboration. Please consider to support respective developers:

### XXMI Launcher:
- **Creator & Maintainer**: [SpectrumQT](https://github.com/SpectrumQT) ([Patreon](https://patreon.com/SpectrumQT))
### GIMI:
- **Creator**: [SilentNightSound](https://github.com/SilentNightSound) ([Ko-Fi](https://ko-fi.com/silentnightsound))
- **Maintainers**: [LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [SinsOfSeven](https://github.com/SinsOfSeven) ([Ko-Fi](https://ko-fi.com/sinsofseven)), [Gustav0](https://github.com/Seris0) ([Ko-Fi](https://ko-fi.com/gustav0_)), [Nurarihyon](https://github.com/NurarihyonMaou) ([Ko-Fi](https://ko-fi.com/nurarihyonmaou))
### SRMI:
- **Creator**: [SilentNightSound](https://github.com/SilentNightSound) ([Ko-Fi](https://ko-fi.com/silentnightsound))
- **Maintainers**: [SinsOfSeven](https://github.com/SinsOfSeven) ([Ko-Fi](https://ko-fi.com/sinsofseven)), [LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [Scyll](https://gamebanana.com/members/2644630) ([Ripe](https://gamebanana.com/members/2644630)), [Gustav0](https://github.com/Seris0) ([Ko-Fi](https://ko-fi.com/gustav0_))
### WWMI:
- **Creator & Maintainer**: [SpectrumQT](https://github.com/SpectrumQT) ([Patreon](https://patreon.com/SpectrumQT))
### ZZMI: 
- **Creator**: [LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [Scyll](https://gamebanana.com/members/2644630) ([Ripe](https://gamebanana.com/members/2644630)), [SilentNightSound](https://github.com/SilentNightSound) ([Ko-Fi](https://ko-fi.com/silentnightsound))
- **Maintainers**: [SinsOfSeven](https://github.com/SinsOfSeven) ([Ko-Fi](https://ko-fi.com/sinsofseven)), [LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [Gustav0](https://github.com/Seris0) ([Ko-Fi](https://ko-fi.com/gustav0_)), [Scyll](https://gamebanana.com/members/2644630) ([Ripe](https://gamebanana.com/members/2644630)), [Satan1c](https://gamebanana.com/members/2789093) ([Patreon](https://patreon.com/Satan1cL))
### HIMI:
- **Creator**: [SilentNightSound](https://github.com/SilentNightSound) ([Ko-Fi](https://ko-fi.com/silentnightsound))
- **Maintainers**: [LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [SinsOfSeven](https://github.com/SinsOfSeven) ([Ko-Fi](https://ko-fi.com/sinsofseven))

## Mod Management

XXMI Launcher now includes an integrated mod manager inspired by [d3dxSkinManage](https://github.com/numlinka/d3dxSkinManage), providing visual mod management alongside kernel updates.

### Features

- **Visual Mod Browser** — Browse all installed mods in a clean, organized interface
- **Easy Enable/Disable** — Toggle mods on or off with a single click
- **Automatic Categorization** — Mods are automatically grouped by category for easy navigation
- **Mod Metadata** — View mod names, authors, descriptions, and associated characters/weapons
- **Live Statistics** — See total, enabled, and disabled mod counts at a glance
- **Conflict Detection** — Only one mod per character/weapon can be active at a time

### How to Use

1. Select a game from the main launcher screen
2. Click the **Tools** icon (wrench) in the bottom-right corner
3. Click **Mod Manager** to open the mod management interface
4. Browse mods by category
5. Use the **Enable/Disable** buttons to toggle individual mods
6. Click **Refresh Mods** to rescan the Mods folder after adding new mods

### Mod Structure

Mods should be placed in the `Mods` folder of your model importer installation. Each mod should be in its own folder:

```
YourGameFolder/
  Mods/
    ModFolderName/
      mod.json (optional metadata)
      *.ini (mod configuration files)
      *.buf (mod assets)
      preview.png (optional preview image)
```

### Mod Metadata (Optional)

Create a `mod.json` file in your mod folder for enhanced mod information:

```json
{
  "name": "Character Outfit Name",
  "object": "CharacterName",
  "author": "YourName",
  "category": "Characters",
  "description": "Description of the mod",
  "preview": "preview.png",
  "tags": ["outfit", "costume"]
}
```

## License

XXMI Launcher is licensed under the [GPLv3 License](https://github.com/SpectrumQT/WWMI-Launcher/blob/main/LICENSE).
