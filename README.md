<h1 align="center">XXMI Launcher</h1>

<h4 align="center">Launcher tool for XXMI</h4>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#supported-model-importers">Supported Model Importers</a> •
  <a href="#license">License</a>
</p>

## Disclaimers

- **In-Dev Warning** — **GIMI** and **SRMI** packages are **in-dev** versions, feel free to test but please be aware!

- **Paranoia Warning** — Some picky AVs may be triggered by XXMI .exe or .dll files. Installer and Launcher are unsigned python apps compiled with Pyinstaller, that is [known to have false positives](https://discuss.python.org/t/pyinstaller-false-positive/43171). DLLs are unsigned binaries intended to inject or be injected into the game process, and it doesn't help either. We can't do anything about it, so it's up to you to use them as is, build yourself or go by.

## Features  

- **One Ring** — Allows to launch and manage all supported Model Importers in unified and convenient way
- **Plug-and-Play** — Configures any supported game and installs its XXMI instance automatically
- **Custom Launch** — Can be configured to start game in almost every possible way via Advanced Settings
- **Automatic Updates** — Always keeps XXMI instances and itself up-to date
- **Safe to Use** — Verifies authenticity of XXMI libraries and own downloads

![xxmi-launcher](https://github.com/SpectrumQT/XXMI-Launcher/blob/main/public-media/XXMI%20Launcher.jpg)

## Installation

1. Install [the latest Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170) ([direct download](https://aka.ms/vs/17/release/vc_redist.x64.exe))
2. Use [XXMI Installer](https://github.com/SpectrumQT/XXMI-Installer) to download and install **XXMI Launcher**.
3. Once installation is complete, **XXMI Launcher** window will open and install **XXMI** instance automatically.

## Supported Model Importers

- [WWMI - Wuthering Waves Model Importer GitHub](https://github.com/SpectrumQT/WWMI)
- [ZZMI - Zenless Zone Zero Model Importer GitHub](https://github.com/leotorrez/ZZ-Model-Importer)
- [SRMI - Honkai: Star Rail Model Importer GitHub](https://github.com/SilentNightSound/SR-Model-Importer)
- [GIMI - Genshin Impact Model Importer GitHub](https://github.com/SilentNightSound/GI-Model-Importer)
  
## License

XXMI Launcher is licensed under the [GPLv3 License](https://github.com/SpectrumQT/WWMI-Launcher/blob/main/LICENSE).
