\# 🧩 Breakers Companion  

!\[Python](https://img.shields.io/badge/Python-3.11+-blue.svg)

!\[Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-lightgrey.svg)

!\[License](https://img.shields.io/badge/License-MIT-green.svg)

!\[Build](https://img.shields.io/badge/Build-PyInstaller-success.svg)

!\[Version](https://img.shields.io/badge/Version-2.0.24--test.8-orange.svg)



\*\*Developer:\*\* Big Beard Trading (BBT)  

\*\*Latest Version:\*\* `2.0.24-test.8`  

\*\*Status:\*\* Active Development 🧪  



---



\## 🎯 Overview

\*\*Breakers Companion\*\* is a Windows desktop application built for \*\*sports card collectors and breakers\*\*.  

It streamlines the organization, sorting, and tracking of trading card sets — designed to make every break, repack, or checklist workflow faster, cleaner, and more professional.



> “From organizing checklists to sorting by team — Breakers Companion is your all-in-one BBT sorting solution.”



---



\## 🖥️ Features



\### 🗂️ Set Management

\- Add, rename, and delete saved sets  

\- Import `.xlsx` checklists (e.g., \*2025 Panini Donruss Football\*)  

\- Auto-detects header rows and common columns (Player / Team / Subset)



\### 🧮 Sorting \& Filtering

\- Search by \*\*player\*\*, \*\*team\*\*, or \*\*subset\*\*  

\- Color-coded rows using \*\*NFL team palettes\*\*  

\- Optional \*\*dark / light UI themes\*\*  



\### 🏈 Branding \& UI

\- BBT logo \& branding built in  

\- Background image integration (`assets/Background.png`)  

\- Top-corner \*\*version tag\*\* syncs with `VERSION` file  



\### ⚙️ Automation

\- `run.bat` — creates venv, installs deps, launches app  

\- `build\_core.bat` — compiles standalone `.exe`  

\- `move\_files.bat` — cleans and relocates builds  

\- `InnoSetup.iss` — builds distributable Windows installer  



---



\## 🧰 Requirements

| Requirement | Version | Notes |

|--------------|----------|-------|

| Python | 3.11+ | Required for source builds |

| OS | Windows 10+ | 64-bit recommended |

| Disk Space | ~300 MB | For build output and environment |

| Internet | Optional | Only for first-run dependency install |



---



\## 📦 Installation



\### 🔹 Option A — Prebuilt Installer

1\. Download the latest `.exe` or `.zip` from the \[Releases page](../../releases).  

2\. Run the installer or extract the archive.  

3\. Launch \*\*Breakers Companion\*\* via the desktop shortcut.



\### 🔹 Option B — From Source

```bash

git clone https://github.com/BigBeardTrading/breakers-companion.git

cd breakers-companion

.\\run.bat



