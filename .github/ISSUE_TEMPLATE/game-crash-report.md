---
name: Game Crash Report
about: Help us with game crash investigation
title: "[CRASH]"
labels: crash
assignees: ''

---

⚠️ **Crash reports that do not follow the guidelines below will be removed.** ⚠️

---

## 📌 Read Before Reporting a Crash

Most crashes—unless caused by a specific mod—are usually **system-specific** and **cannot be diagnosed remotely** without your help.

You're expected to **narrow down the cause yourself** before submitting a report. This includes identifying the file that causes the crash, or at least reducing the number of possible causes significantly.

Please follow the steps below carefully. After each step, **restart the game and test again**. If the crash seems random, test each step multiple times.

---

## 🔍 Crash Isolation Checklist

1. **Remove all files from `GIMI\ShaderFixes`**  
   This disables shader tweaks, which are a common crash source.

2. **Remove all files from `GIMI\Mods`**  
   Ensures the crash isn’t caused by user mods.

3. **Keep only `main.ini` in `GIMI\Core`**  
   Delete everything else from `GIMI\Core\GIMI` to rule out bundled shader conflicts from the Model Importer.

---

If removing files during one of these steps **stops the crash**, please identify the exact file that caused it.  
To speed up the process, we recommend using the [Halves Method](https://leotorrez.github.io/modding/guides/troubleshooting#the-halves-method).

---

## 📤 Where to Submit Crash Reports

Once you've found the cause, **report it to the correct Model Importer repository below**.

> 💡 Most crashes are **game-specific** and not directly related to **XXMI Launcher** or the **XXMI DLL**. Such reports **will not be accepted here**.

- **GIMI (Genshin Impact)**  
  https://github.com/SilentNightSound/GIMI-Package/issues

- **SRMI (Star Rail)**  
  https://github.com/SpectrumQT/SRMI-Package/issues

- **WWMI (Wuthering Waves)**  
  https://github.com/SpectrumQT/WWMI-Package/issues

- **ZZMI (Zenless Zone Zero)**  
  https://github.com/leotorrez/ZZMI-package/issues
