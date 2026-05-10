import argparse
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TI:
    n: str
    p: Optional[str] = None
    v: Optional[str] = None
    s: str = ""

def _rc(a, timeout=5):
    try:
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = 0x08000000
        r = subprocess.run(a, capture_output=True, text=True, timeout=timeout, **kw)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None

def _fe(n):
    return shutil.which(n)

def _gv(e):
    o = _rc([e, "--version"])
    return o.splitlines()[0].strip() if o else None

PYN = [
    "python3", "python", "python2",
    "python3.13", "python3.12", "python3.11", "python3.10", "python3.9",
    "python3.8", "python3.7", "python3.6", "python2.7",
    "pypy3", "pypy",
]

def _fpy_which():
    fs = []
    seen = set()
    for n in PYN:
        p = _fe(n)
        if p and p not in seen:
            seen.add(p)
            v = _gv(p)
            if not v:
                v = _rc([p, "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"])
            fs.append(TI(n=n, p=p, v=v, s="PATH"))
    return fs

def _fpy_sys():
    v = ".".join(map(str, sys.version_info[:3]))
    return [TI(n=f"python{sys.version_info.major}.{sys.version_info.minor}", p=sys.executable, v=v, s="sys.executable")]

def _fpy_pyenv():
    fs = []
    root = os.environ.get("PYENV_ROOT")
    if not root:
        home = os.path.expanduser("~")
        root = os.path.join(home, ".pyenv", "pyenv-win") if platform.system() == "Windows" else os.path.join(home, ".pyenv")
    vdir = os.path.join(root, "versions")
    if os.path.isdir(vdir):
        for d in os.listdir(vdir):
            dp = os.path.join(vdir, d)
            if not os.path.isdir(dp):
                continue
            exe = os.path.join(dp, "python.exe" if platform.system() == "Windows" else "bin/python")
            if os.path.isfile(exe):
                fs.append(TI(n=f"pyenv:{d}", p=exe, v=_gv(exe), s="pyenv"))
    return fs

def _fpy_conda():
    fs = []
    ce = _fe("conda")
    if not ce:
        return fs
    out = _rc([ce, "env", "list"])
    if not out:
        return fs
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        envp = parts[-1]
        exe = os.path.join(envp, "python.exe" if platform.system() == "Windows" else "bin/python")
        if os.path.isfile(exe):
            fs.append(TI(n=f"conda:{parts[0]}", p=exe, v=_gv(exe), s="conda env"))
    return fs

def _fpy_reg():
    if platform.system() != "Windows":
        return []
    try:
        import winreg
    except ImportError:
        return []
    fs = []
    seen = set()
    paths = [
        (winreg.HKEY_CURRENT_USER,  r"Software\Python"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Python"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Python"),
    ]
    for hive, base in paths:
        try:
            with winreg.OpenKey(hive, base) as key:
                i = 0
                while True:
                    try:
                        comp = winreg.EnumKey(key, i)
                        i += 1
                        with winreg.OpenKey(key, comp) as ck:
                            j = 0
                            while True:
                                try:
                                    tag = winreg.EnumKey(ck, j)
                                    j += 1
                                    with winreg.OpenKey(ck, tag) as tk:
                                        ep, _ = winreg.QueryValueEx(tk, "ExecutablePath")
                                        if ep and ep not in seen:
                                            seen.add(ep)
                                            fs.append(TI(n=f"python ({comp}/{tag})", p=ep, v=_gv(ep), s="winreg"))
                                except OSError:
                                    break
                    except OSError:
                        break
        except OSError:
            pass
    return fs

def fap():
    all_fs = []
    seen = {}
    def add(lst):
        for info in lst:
            if info.p:
                norm = os.path.normpath(os.path.realpath(info.p))
            else:
                norm = None
            if norm and norm not in seen:
                seen[norm] = info
                all_fs.append(info)
    add(_fpy_sys())
    add(_fpy_which())
    add(_fpy_conda())
    add(_fpy_pyenv())
    add(_fpy_reg())
    return all_fs

PKGM = [
    "pip", "pip3",
    "conda", "mamba", "micromamba",
    "poetry", "pdm", "uv", "rye", "hatch",
    "pipenv", "easy_install",
]

def _fpip_via(p):
    out = _rc([p, "-m", "pip", "--version"])
    if not out:
        return None
    parts = out.split()
    if len(parts) < 2:
        return None
    ver = parts[1]
    return TI(n=f"pip (via {os.path.basename(p)})", p=f"{p} -m pip", v=ver, s="python -m pip")

def fapm(ps):
    found = []
    seen = set()
    def add(info):
        if info is None:
            return
        if info.p not in seen:
            seen.add(info.p)
            found.append(info)
    for n in PKGM:
        p = _fe(n)
        if p:
            add(TI(n=n, p=p, v=_gv(p), s="PATH"))
    p = _fe("pipx")
    if p:
        add(TI(n="pipx", p=p, v=_gv(p), s="PATH"))
    for pi in ps:
        if pi.p and os.path.isfile(pi.p):
            add(_fpip_via(pi.p))
    if platform.system() == "Windows":
        py = _fe("py")
        if py:
            add(TI(n="py (Launcher)", p=py, v=_gv(py), s="PATH"))
            out = _rc([py, "-m", "pip", "--version"])
            if out:
                parts = out.split()
                ver = parts[1] if len(parts) > 1 else None
                add(TI(n="pip (via py)", p=f"{py} -m pip", v=ver, s="py -m pip"))
    return found

B   = "\033[1m"
GRN = "\033[92m"
YLW = "\033[93m"
CYN = "\033[96m"
RED = "\033[91m"
RST = "\033[0m"

def _c(t, code):
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return t
    return f"{code}{t}{RST}"

def pres(ps, pms, si, sp, js):
    if js:
        import json
        data = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
            },
            "interpreters": [{"name": i.n, "path": i.p, "version": i.v, "source": i.s} for i in ps],
            "package_managers": [{"name": i.n, "path": i.p, "version": i.v, "source": i.s} for i in pms],
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print()
    print(_c("System Info", B))
    print(f"  OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Current Python: {platform.python_version()}")
    print()

    if si:
        print(_c("Python Interpreters", B))
        if ps:
            for i, info in enumerate(ps, 1):
                lb = _c(f"[{i}]", GRN)
                print(f"  {lb} {info.n}")
                print(f"       Path:   {info.p or '(not found)'}")
                print(f"       Version:{info.v or '(unknown)'}")
                print(f"       Source: {info.s}")
                print()
        else:
            print(_c("  (No Python interpreters found)", RED))
            print()

    if sp:
        print(_c("Python Package Managers", B))
        if pms:
            for i, info in enumerate(pms, 1):
                lb = _c(f"[{i}]", YLW)
                print(f"  {lb} {info.n}")
                print(f"       Path:   {info.p or '(not found)'}")
                print(f"       Version:{info.v or '(unknown)'}")
                print(f"       Source: {info.s}")
                print()
        else:
            print(_c("  (No package managers found)", RED))
            print()

    print(_c("Summary", B))
    print(f"  Found {len(ps)} interpreter(s), {len(pms)} package manager(s)")
    print()

def main():
    p = argparse.ArgumentParser(
        prog="pyfinder",
        description="Cross-platform Python interpreter & package manager finder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-i", "--interpreters-only", action="store_true", help="Find only interpreters")
    p.add_argument("-p", "--packages-only", action="store_true", help="Find only package managers")
    p.add_argument("-j", "--json", action="store_true", dest="js", help="Output in JSON format")
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    a = p.parse_args()

    if a.no_color:
        os.environ["NO_COLOR"] = "1"

    si = not a.packages_only
    sp = not a.interpreters_only

    ps = fap() if si else []
    pms = fapm(ps) if sp else []
    pres(ps, pms, si, sp, a.js)

if __name__ == "__main__":
    main()
