import os
import subprocess
import sys
from pathlib import Path


def ensure_venv(venv_dir: Path):
    if not venv_dir.exists():
        print("[setup] Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    else:
        print("[setup] Reusing existing virtual environment")


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def main():
    print("=== One-command demo bootstrap ===")
    repo_root = Path(__file__).resolve().parent
    os.chdir(repo_root)

    venv_dir = repo_root / ".venv"
    ensure_venv(venv_dir)

    py = venv_python(venv_dir)
    print("[setup] Installing dependencies...")
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "-r", "requirements.txt"], check=True)

    print("[run] Launching local demo...")
    result = subprocess.run([str(py), "demo.py"])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
