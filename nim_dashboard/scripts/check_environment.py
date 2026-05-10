"""Check local runtime prerequisites for the NIM dashboard without importing app code.

This script intentionally avoids importing pandas/FastAPI project modules so it can
run even before dependencies are installed. It reports the active Python version,
proxy/index-related environment variables, and missing Python packages with
installation guidance for online, corporate-mirror, and offline wheelhouse setups.
"""
from __future__ import annotations

import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path

REQUIRED_MODULES = {
    "pandas": "pandas>=2.0",
    "openpyxl": "openpyxl>=3.1",
    "fastapi": "fastapi>=0.110",
    "uvicorn": "uvicorn>=0.27",
    "multipart": "python-multipart>=0.0.9",
}

NETWORK_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL",
    "PIP_CERT",
)


def _is_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    print("NIM dashboard environment check")
    print(f"Project: {root}")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    pip_version = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True, check=False)
    print(f"pip: {pip_version.stdout.strip() if pip_version.returncode == 0 else '<pip unavailable for this interpreter>'}")
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11 이상이 필요합니다.")
        return 1

    print("\nNetwork / pip related environment variables:")
    for key in NETWORK_ENV_KEYS:
        value = os.environ.get(key)
        print(f"- {key}={value if value else '<unset>'}")

    missing = []
    print("\nRequired Python modules:")
    for module_name, requirement in REQUIRED_MODULES.items():
        installed = _is_installed(module_name)
        print(f"- {requirement}: {'OK' if installed else 'MISSING'}")
        if not installed:
            missing.append(requirement)

    if not missing:
        print("\nAll required modules are importable. You can run:")
        print("  python src/export/build_dashboard_data.py")
        print("  python app.py")
        return 0

    print("\nMissing dependencies detected for THIS Python interpreter.")
    print("If you already installed pandas, verify that you installed it into the same interpreter shown above:")
    print(f"   {sys.executable} -m pip show pandas")
    print("\nChoose one installation path:")
    print("1) Normal internet / approved PyPI access:")
    print("   python -m pip install -r requirements.txt")
    print("2) Corporate PyPI mirror:")
    print("   python -m pip install -r requirements.txt --index-url https://<company-pypi-mirror>/simple")
    print("3) Offline wheelhouse copied from an internet-connected machine:")
    print("   python -m pip install --no-index --find-links ./wheelhouse -r requirements.txt")
    print("\nIf pip reports 'Tunnel connection failed: 403 Forbidden', the proxy or package index")
    print("is blocking outbound PyPI traffic; fix the network/index policy or use options 2/3.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
