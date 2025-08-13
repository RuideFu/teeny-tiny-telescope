# the teeny-tiny-telescope (ttt)

This project is designed to be a high level user interface and data pipeline for the teeny-tiny-telescope project at ERIRA 2025.
All applications should be at the top level, and all utilities/libraries to interact with the hardware and/or to process data should be in /ttt.

# Setup Instructions

## 1. Set up a Python virtual environment

Open a terminal in your project directory and run:

```bash
python3 -m venv venv
```

Activate the virtual environment:

- On Linux/macOS:
  ```bash
  source venv/bin/activate
  ```
- On Windows:
  ```bat
  venv\Scripts\activate
  ```

## 2. Install dependencies from `requirements.txt`

Assuming you're in the root of `RuideFu/teeny-tiny-telescope`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Install `rtlobs` (`EmmanuelSchaan/rtlobs`) locally as a dependency

If you have a local clone of `rtlobs`, install it in *editable* mode so changes are picked up automatically:

```bash
pip install -e /path/to/rtlobs
```

Replace `/path/to/rtlobs` with the actual path to your local `rtlobs` repository.

Alternatively, to install directly from GitHub (latest main branch):

```bash
pip install git+https://github.com/EmmanuelSchaan/rtlobs.git
```

---
You are now set up to use both `teeny-tiny-telescope` and `rtlobs` together in your Python environment.

