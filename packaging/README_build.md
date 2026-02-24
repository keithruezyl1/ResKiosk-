# ResKiosk Build Instructions

This document describes **manual/advanced** build steps. For normal use, run the scripts in **TO RUN** (`01_install_deps.bat`, `02_download_models.bat`) first; they set up the environment and models. The steps below are for building the standalone executable or working without the TO RUN scripts.

## Prerequisites
- Python 3.10+
- Installed `ollama` (for model pulling) OR manual placement of `ollama.exe`

## Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install requirements:
   ```bash
   pip install fastapi uvicorn requests pyinstaller huggingface_hub sentence-transformers
   ```

## Model Bundling (One-Time)
Run the bundler script to download models and set up the portable Ollama instance.
```bash
python packaging/bundle_models.py
```
*Note: This might require `ollama.exe` to be present or installed on the system to copy it.*

## Build Executable
Run PyInstaller using the spec file:
```bash
pyinstaller packaging/reskiosk-hub.spec
```

## Run
The output will be in `dist/ResKiosk-Hub/`.
Run `ResKiosk-Hub.exe`.
