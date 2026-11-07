"""
build_playground.py

Assembles the static playground site into _site/ (what GitHub Pages serves):

    playground/             -> _site/
    playground/py/bridge.py -> _site/py/bridge.py
    mech_toolkit/*.py       -> _site/py/mech_toolkit/*.py   (calculation modules only)
    + _site/py/manifest.json, listing those files for the web worker

The playground loads the package straight from these copies, so whatever is
on main is exactly what runs in the browser.

Usage:
    python scripts/build_playground.py                 # build _site/
    python scripts/build_playground.py --serve         # build, then serve on :8000
    python scripts/build_playground.py --pyodide DIR   # also copy a local Pyodide
                                                       # (offline testing; open
                                                       # /?pyodide=pyodide/)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "playground"
PKG = ROOT / "mech_toolkit"
OUT = ROOT / "_site"

# Modules that need a desktop or plotting stack the browser doesn't have.
SKIP = {"gui.py", "plotting.py"}


def count_tests() -> int:
    return sum(len(re.findall(r"^def test_", p.read_text(encoding="utf-8"), re.M))
               for p in (ROOT / "tests").glob("test_*.py"))


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def build(pyodide: Path | None = None) -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    dest = OUT / "py" / "mech_toolkit"
    dest.mkdir(parents=True, exist_ok=True)
    files = ["bridge.py"]
    for f in sorted(PKG.glob("*.py")):
        if f.name in SKIP:
            continue
        shutil.copy2(f, dest / f.name)
        files.append(f"mech_toolkit/{f.name}")

    version = re.search(r'__version__\s*=\s*"([^"]+)"', (PKG / "__init__.py").read_text()).group(1)
    manifest = {"version": version, "commit": git_commit(), "tests": count_tests(), "files": files}
    (OUT / "py" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / ".nojekyll").write_text("")

    if pyodide:
        shutil.copytree(pyodide, OUT / "pyodide")
    print(f"Built {OUT.relative_to(ROOT)}/ with {len(files)} Python files, {manifest['tests']} tests counted")
    return OUT


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serve", action="store_true", help="serve _site/ on http://localhost:8000")
    ap.add_argument("--pyodide", type=Path, help="copy a local Pyodide distribution for offline use")
    args = ap.parse_args()
    out = build(args.pyodide)
    if args.serve:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
        print("Serving on http://localhost:8000")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()


if __name__ == "__main__":
    main()
