---
name: Game Crash Report
about: Help us with game crash investigation
title: "[CRASH]"
labels: 3dmigoto, bug, crash, launcher
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

1. **Reboot your PC**  
   Lets ensure there are no leftover traces running in the background.

2. **Run game repair via official launcher**  
   This way we'll exclude possibility of game files corruption.

3. **Run Model Importer repair via XXMI Launcher** (**3-dots button** next to **Start**)  
   Just to make sure that Model Importer files aren't corrupted or configured wrong.

4. **Remove all files from `GIMI\ShaderFixes`**  
   Here we disable shader tweaks, which are known to easily cause crashes.

5. **Remove all files from `GIMI\Mods`**  
   Ensures the crash isn’t caused by user mods.

6. **Keep only `main.ini` in `GIMI\Core`**  (`WuWa-Model-Importer.ini` for WWMI)  
   Delete everything else from `GIMI\Core\GIMI` to rule out built-in shaders incompatibility.

> ⚠️ Warning! Don't forget to run **Repair GIMI** again to restore `GIMI\Core` after Step #6.  

> 📝 Note: GIMI used as example. For SRMI / WWMI / ZZMI process is the same.

---

If removing files during one of these steps **stops the crash**, please identify the exact file that caused it.  
To speed up the process, we recommend using the [Halves Method](https://leotorrez.github.io/modding/guides/troubleshooting#the-halves-method).

Once you've found the cause (or still crashing) please proceed.

---

## 📤 Where to Submit Crash Reports

> 💡 Most crashes are **game-specific** and not directly related to **XXMI Launcher** or the **XXMI DLL**. Such crash report **will not be accepted as XXMI Launcher issue**, please **report it to the correct Model Importer repository below**.

### **📄 Provide Logs**
Please don't forget to include the **launcher log**  — it is essential for understanding your environment (OS, PC specs, versions, and launcher actions performed).

- Upload your `XXMI Launcher Log.txt` from the launcher installation folder to [Pastebin](https://pastebin.com), and provide the link.

> 🕒 Crash reports without logs take way more time to handle.

- **GIMI (Genshin Impact)**  
  https://github.com/SilentNightSound/GIMI-Package/issues

- **SRMI (Star Rail)**  
  https://github.com/SpectrumQT/SRMI-Package/issues

- **WWMI (Wuthering Waves)**  
  https://github.com/SpectrumQT/WWMI-Package/issues

- **ZZMI (Zenless Zone Zero)**  
  https://github.com/leotorrez/ZZMI-package/issues

- **HIMI (Zenless Zone Zero)**  
  https://github.com/leotorrez/HIMI-package/issues
