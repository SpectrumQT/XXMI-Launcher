<h1 align="center">XXMI Launcher</h1>

<h4 align="center">Launcher tool for XXMI</h4>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#supported-model-importers">Supported Model Importers</a> •
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

![xxmi-launcher](https://github.com/SpectrumQT/XXMI-Launcher/blob/main/public-media/XXMI%20Launcher.jpg)

## Installation

* **Native Windows APP** (for **Windows** only)
  1. Download the [latest release](https://github.com/SpectrumQT/XXMI-Launcher/releases/latest) of **XXMI-Launcher-Installer-Online-vX.X.X.msi**
  2. Run **XXMI-Launcher-Installer-Online-vX.X.X.msi** with Double-Click.
  3. Click **[Quick Installation]** to install **XXMI Launcher** to the default location (`%AppData%\XXMI Launcher`) or use **[Custom Installation]** to set another folder.
  4. On the game selection page of **XXMI Launcher Window** click desired **Game Tile** to add **Model Importer Icon** to the top-left corner.
  5. Click **Model Importer Icon** to open Model Importer page and press **[Install]** button to download and install selected Model Importer.

* **Portable** (for **Windows** and **Linux** via **WINE 9.22+**)
  1. Download and install [the latest Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe).
  2. Download the [latest release](https://github.com/SpectrumQT/XXMI-Launcher/releases/latest) of **XXMI-Launcher-Portable-vX.X.X.zip**.
  3. Extract the archive to desired location (avoid Program Files folders!).
  4. Create shortcut for `Resources\Bin\XXMI Launcher.exe` for convenience and run it.
  5. On the game selection page of **XXMI Launcher Window** click desired **Game Tile** to add **Model Importer Icon** to the top-left corner.
  6. Click **Model Importer Icon** to open Model Importer page and press **[Install]** button to download and install selected Model Importer.

## Supported Model Importers

- [WWMI - Wuthering Waves Model Importer GitHub](https://github.com/SpectrumQT/WWMI)
- [ZZMI - Zenless Zone Zero Model Importer GitHub](https://github.com/leotorrez/ZZ-Model-Importer)
- [SRMI - Honkai: Star Rail Model Importer GitHub](https://github.com/SilentNightSound/SR-Model-Importer)
- [GIMI - Genshin Impact Model Importer GitHub](https://github.com/SilentNightSound/GI-Model-Importer)
  
## License

XXMI Launcher is licensed under the [GPLv3 License](https://github.com/SpectrumQT/WWMI-Launcher/blob/main/LICENSE).
