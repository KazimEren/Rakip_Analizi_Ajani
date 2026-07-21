"""Builds Rakip_Analizi_Ajani.exe with PyInstaller.

Usage:
    python build_exe.py

Produces dist/Rakip_Analizi_Ajani.exe (onefile, windowed - no console).
The .env file is NOT bundled: it must sit next to the .exe (run_app.py
chdir's to the exe's own directory), so keys stay editable without a rebuild.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "competitor_analysis_agent" / "gui" / "static"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
APP_NAME = "Rakip_Analizi_Ajani"


def main() -> int:
    add_data_sep = ";" if sys.platform.startswith("win") else ":"
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        APP_NAME,
        "--onefile",
        "--noconsole",
        "--noconfirm",
        "--add-data",
        f"{STATIC_DIR}{add_data_sep}competitor_analysis_agent/gui/static",
        "--collect-all",
        "google.genai",
        "--collect-all",
        "supabase",
        str(ROOT / "run_app.py"),
    ]
    print("Çalıştırılıyor:", " ".join(args))
    subprocess.run(args, check=True, cwd=ROOT)

    env_example = ROOT / ".env.example"
    if env_example.exists():
        shutil.copy(env_example, DIST_DIR / ".env.example")

    print(f"\nBitti. Çıktı: {DIST_DIR / (APP_NAME + '.exe')}")
    print(f"İlk çalıştırmadan önce {DIST_DIR / '.env.example'} dosyasını {DIST_DIR / '.env'} olarak kopyalayıp anahtarları girin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
