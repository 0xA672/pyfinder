#!/usr/bin/env python3
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TI:
    n: str
    p: Optional[str] = None
    v: Optional[str] = None
    s: str = ""
    ok: bool = True

def _rc(a, timeout=5):
    try:
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = 0x08000000
        r = subprocess.run(
            a, capture_output=True, text=True,
            timeout=timeout, errors="replace", **kw
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, PermissionError, OSError, subprocess.TimeoutExpired):
        pass
    return None

def _fe(n):
    try:
        return shutil.which(n)
    except (FileNotFoundError, PermissionError, OSError):
        return None

def _gv(e):
    for flag in ["--version", "-V", "version"]:
        o = _rc([e, flag])
        if o:
            for line in o.splitlines():
                line = line.strip()
                if line and not line.lower().startswith("usage"):
                    return line
    o = _rc([e, "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"])
    return o

def _is_exe(p):
    try:
        return os.path.isfile(p) and os.access(p, os.X_OK)
    except OSError:
        return False

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
        if not p or p in seen:
            continue
        seen.add(p)
        v = _gv(p)
        ok = _is_exe(p)
        fs.append(TI(n=n, p=p, v=v, s="PATH", ok=ok))
    return fs

def _fpy_sys():
    v = ".".join(map(str, sys.version_info[:3]))
    ok = _is_exe(sys.executable)
    return [TI(n=f"python{sys.version_info.major}.{sys.version_info.minor}", p=sys.executable, v=v, s="sys.executable", ok=ok)]

def _fpy_pyenv():
    fs = []
    root = os.environ.get("PYENV_ROOT")
    if not root:
        home = os.path.expanduser("~")
        root = os.path.join(home, ".pyenv", "pyenv-win") if platform.system() == "Windows" else os.path.join(home, ".pyenv")
    vdir = os.path.join(root, "versions")
    if not os.path.isdir(vdir):
        return fs
    try:
        entries = os.listdir(vdir)
    except (PermissionError, OSError):
        return fs
    for d in sorted(entries):
        dp = os.path.join(vdir, d)
        if not os.path.isdir(dp):
            continue
        exe = os.path.join(dp, "python.exe" if platform.system() == "Windows" else "bin/python")
        if os.path.isfile(exe):
            v = _gv(exe)
            ok = _is_exe(exe)
            fs.append(TI(n=f"pyenv:{d}", p=exe, v=v, s="pyenv", ok=ok))
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
        if len(parts) < 2:
            continue
        envp = parts[-1]
        exe = os.path.join(envp, "python.exe" if platform.system() == "Windows" else "bin/python")
        if os.path.isfile(exe):
            v = _gv(exe)
            ok = _is_exe(exe)
            fs.append(TI(n=f"conda:{parts[0]}", p=exe, v=v, s="conda env", ok=ok))
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
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(key, comp) as ck:
                            j = 0
                            while True:
                                try:
                                    tag = winreg.EnumKey(ck, j)
                                    j += 1
                                except OSError:
                                    break
                                try:
                                    with winreg.OpenKey(ck, tag) as tk:
                                        ep, _ = winreg.QueryValueEx(tk, "ExecutablePath")
                                        if ep and ep not in seen:
                                            seen.add(ep)
                                            v = _gv(ep)
                                            ok = _is_exe(ep)
                                            fs.append(TI(n=f"python ({comp}/{tag})", p=ep, v=v, s="winreg", ok=ok))
                                except OSError:
                                    continue
                    except OSError:
                        continue
        except OSError:
            pass
    return fs

def fap():
    all_fs = []
    seen = {}
    def add(lst):
        for info in lst:
            if not info.p:
                continue
            try:
                norm = os.path.normcase(os.path.normpath(os.path.realpath(info.p)))
            except OSError:
                norm = info.p
            if norm not in seen:
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
    ok = _is_exe(p)
    return TI(n=f"pip (via {os.path.basename(p)})", p=f"{p} -m pip", v=ver, s="python -m pip", ok=ok)

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
            v = _gv(p)
            ok = _is_exe(p)
            add(TI(n=n, p=p, v=v, s="PATH", ok=ok))
    p = _fe("pipx")
    if p:
        v = _gv(p)
        ok = _is_exe(p)
        add(TI(n="pipx", p=p, v=v, s="PATH", ok=ok))
    for pi in ps:
        if pi.p and os.path.isfile(pi.p):
            add(_fpip_via(pi.p))
    if platform.system() == "Windows":
        py = _fe("py")
        if py:
            v = _gv(py)
            ok = _is_exe(py)
            add(TI(n="py (Launcher)", p=py, v=v, s="PATH", ok=ok))
            out = _rc([py, "-m", "pip", "--version"])
            if out:
                parts = out.split()
                ver = parts[1] if len(parts) > 1 else None
                add(TI(n="pip (via py)", p=f"{py} -m pip", v=ver, s="py -m pip", ok=ok))
    return found

B   = "\033[1m"
DIM = "\033[2m"
GRN = "\033[92m"
YLW = "\033[93m"
CYN = "\033[96m"
RED = "\033[91m"
MGN = "\033[95m"
BLU = "\033[94m"
RST = "\033[0m"

_no_color = False

def _c(t, *codes):
    if _no_color or not sys.stdout.isatty():
        return t
    return "".join(codes) + t + RST

def _tw():
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80

def _pad(s, w):
    d = w - _vw(s)
    return s + " " * max(d, 0)

def _vw(s):
    w = 0
    esc = False
    for ch in s:
        if ch == "\033":
            esc = True
        elif esc and ch == "m":
            esc = False
        elif not esc:
            w += 1
    return w

def _hr(ch="─", color=""):
    w = _tw()
    line = ch * w
    if color and not _no_color and sys.stdout.isatty():
        return color + line + RST
    return line

def _box(title, items, label_color, icon):
    if not items:
        return
    w = _tw()
    nw = 20
    pw = max(w - nw - 4, 30)
    print(_hr("━", DIM))
    print(_c(f" {icon} {title}", B, label_color))
    print(_hr("─", DIM))
    for i, info in enumerate(items, 1):
        idx = _c(f" {i:>2} ", B, label_color)
        status = _c("●", GRN) if info.ok else _c("○", YLW)
        name = _c(info.n, B)
        ver = _c(info.v or "unknown", CYN if info.v else DIM)
        print(f"{idx}{status} {name}  {ver}")
        if info.p:
            pp = info.p
            if len(pp) > pw:
                pp = "…" + pp[-(pw - 1):]
            print(f"     {_c('↳', DIM)} {_c(pp, DIM)}")
        print(f"     {_c('src:', DIM)} {_c(info.s, DIM)}")
    print()

def pres(ps, pms, si, sp, js):
    if js:
        data = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
            },
            "interpreters": [{"name": i.n, "path": i.p, "version": i.v, "source": i.s, "accessible": i.ok} for i in ps],
            "package_managers": [{"name": i.n, "path": i.p, "version": i.v, "source": i.s, "accessible": i.ok} for i in pms],
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print()
    print(_hr("━", CYN))
    print(_c("  System Info", B, CYN))
    print(_hr("─", DIM))
    print(f"  OS       {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Python   {platform.python_version()}")
    print(f"  Prefix   {sys.prefix}")
    print()

    if si:
        if ps:
            _box("Python Interpreters", ps, GRN, "")
        else:
            print(_hr("━", DIM))
            print(_c("Python Interpreters", B, GRN))
            print(_hr("─", DIM))
            print(_c("  No Python interpreters found", RED))
            print()

    if sp:
        if pms:
            _box("Package Managers", pms, YLW, "")
        else:
            print(_hr("━", DIM))
            print(_c("Package Managers", B, YLW))
            print(_hr("─", DIM))
            print(_c("  No package managers found", RED))
            print()

    print(_hr("━", CYN))
    pi = _c(str(len(ps)), GRN if ps else RED)
    pm = _c(str(len(pms)), YLW if pms else RED)
    po = _c(str(sum(1 for i in ps if not i.ok)), RED) if any(not i.ok for i in ps) else _c("0", GRN)
    print(f"  Interpreters: {pi}  ·  Package Managers: {pm}  ·  Unreachable: {po}")
    print(_hr("━", CYN))
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

    global _no_color
    if a.no_color or os.environ.get("NO_COLOR"):
        _no_color = True

    si = not a.packages_only
    sp = not a.interpreters_only

    ps = fap() if si else []
    pms = fapm(ps) if sp else []
    pres(ps, pms, si, sp, a.js)

if __name__ == "__main__":
    main()
