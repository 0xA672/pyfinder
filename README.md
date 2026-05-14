## 🐍 pyfinder - Where are my py?

**pyfinder** is a cross-platform command-line tool that finds all Python interpreters and package managers installed on your system. It searches across PATH, `pyenv`, `conda`, and the Windows Registry—then presents the results in a clear, colorful overview.

### ✨ Features

- 🔍 **Comprehensive Discovery** – Finds Python interpreters from:
    - `PATH` (common names like `python3`, `python3.11`, `pypy3`, etc.)
    - The currently running interpreter (`sys.executable`)
    - `pyenv` installations
    - `conda` environments
    - Windows Registry (PEP 514)
- 📦 **Package Managers** – Detects package managers including `pip`, `conda`, `mamba`, `poetry`, `pdm`, `uv`, `pipenv`, and more.
- 🌈 **Beautiful Output** – Color-coded terminal output with icons, status indicators, and neatly formatted paths.
- 📋 **JSON Export** – Option to output machine-readable JSON (great for scripts or CI/CD).
- 🪟 **Windows Friendly** – Uses `py` launcher detection, `winreg`, and `NO_COLOR` support.
- ⚡ **Zero Dependencies** – Pure Python 3 standard library. No `pip install` needed.

### 📦 Installation

Just download the script—no dependencies required.

```bash
git clone https://github.com/0xA672/pyfinder.git
cd pyfinder
python pyfinder.py
```

Or copy it directly:

```bash
curl -O https://raw.githubusercontent.com/0xA672/pyfinder/main/pyfinder.py
python pyfinder.py
```

### 🚀 Usage

```
python pyfinder.py [OPTIONS]
```

#### Options

| Flag | Description |
|------|-------------|
| `-i`, `--interpreters-only` | Show only Python interpreters |
| `-p`, `--packages-only` | Show only package managers |
| `-j`, `--json` | Output in JSON format |
| `--no-color` | Disable colored output |

#### Examples

**1. Default – show everything**

```bash
$ python pyfinder.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  System Info
────────────────────────────────────────────────────────────────────────────────
  OS       Linux 5.15.0-91-generic (x86_64)
  Python   3.11.6
  Prefix   /usr

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Python Interpreters
────────────────────────────────────────────────────────────────────────────────
  1 ● python3.11  Python 3.11.6
     ↳ /usr/bin/python3.11
     src: sys.executable
  2 ● python3     Python 3.10.12
     ↳ /usr/bin/python3
     src: PATH
  3 ● pyenv:3.9.18  Python 3.9.18
     ↳ /home/user/.pyenv/versions/3.9.18/bin/python
     src: pyenv
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Package Managers
────────────────────────────────────────────────────────────────────────────────
  1 ● pip  23.2.1
     ↳ /usr/bin/pip
     src: PATH
  2 ● poetry  Poetry (version 1.6.1)
     ↳ /home/user/.local/bin/poetry
     src: PATH
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Interpreters: 4  ·  Package Managers: 3  ·  Unreachable: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**2. Only interpreters, JSON output**

```bash
$ python pyfinder.py -i -j
```

**3. Use in a script**

```python
import subprocess, json
result = subprocess.run(["python", "pyfinder.py", "-j"], capture_output=True, text=True)
data = json.loads(result.stdout)
for interpreter in data["interpreters"]:
    print(interpreter["path"])
```

### 📊 JSON Schema

```json
{
  "platform": {
    "system": "Linux",
    "release": "5.15.0-91-generic",
    "machine": "x86_64",
    "python_version": "3.11.6"
  },
  "interpreters": [
    {
      "name": "python3.11",
      "path": "/usr/bin/python3.11",
      "version": "Python 3.11.6",
      "source": "sys.executable",
      "accessible": true
    }
  ],
  "package_managers": [
    {
      "name": "pip",
      "path": "/usr/bin/pip",
      "version": "23.2.1",
      "source": "PATH",
      "accessible": true
    }
  ]
}
```

### 🧩 How It Works

pyfinder scans your system using multiple strategies:

1. **PATH scanning** – Looks for executables named `python3`, `python`, `pip`, etc.
2. **Current process** – Uses `sys.executable`.
3. **pyenv** – Lists all versions under `$PYENV_ROOT/versions` (or `~/.pyenv`).
4. **conda** – Runs `conda env list` and checks each environment’s `bin/python`.
5. **Windows Registry** – Reads PEP 514 keys to find Python installations.
6. **`py` launcher** (Windows only) – Detects the Python launcher and `py -m pip`.

Each found executable is verified for accessibility (`os.X_OK`) and its version is extracted.

### 🛠️ Requirements

- **Python 3.6+** (uses f-strings, `subprocess.run`, `dataclasses`)
- No external packages required
- Works on **Linux**, **macOS**, and **Windows**

### 🤝 Contributing

Contributions are welcome! Here's how you can help:

- Test on different operating systems and report issues
- Add support for additional package managers
- Improve error handling or performance
- Submit PRs with enhancements

### 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### 🙏 Acknowledgments

Inspired by [pythonfinder](https://github.com/sarugaku/pythonfinder) and the need for a lightweight, dependency‑free Python discovery tool.

---

**pyfinder** – never lose track of your Python installations again.
