# the teeny-tiny-telescope (ttt)

This project is designed to be a high level user interface and data pipeline for the teeny-tiny-telescope project at ERIRA 2025.
All applications should be at the top level, and all utilities/libraries to interact with the hardware and/or to process data should be in /ttt.

# Hardware

We used a small antenna of unknown brand, with an amplifier (details TBD), and the [Nooelec NESDR SMArTee XTR SDR](https://www.nooelec.com/store/nesdr-smartee-xtr-sdr.html?srsltid=AfmBOoqEyfS_t4iCNts-fj9BeDsQ_8n0PPxO5HfT14pSGFp9GPuS2cjl).

# Setup Instructions

This project uses [uv](https://docs.astral.sh/uv/) to manage the Python
environment and dependencies.

## 1. Install uv

- On Linux/macOS:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- On Windows:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

## 2. Sync the environment

Assuming you're in the root of `RuideFu/teeny-tiny-telescope`:

```bash
uv sync
```

This creates a `.venv` with the exact versions pinned in `uv.lock`, installing
Python 3.14 if it isn't already available.

## 3. Run the applications

Prefix commands with `uv run` and uv will use the project environment:

```bash
uv run main.py
```

Alternatively, activate the environment (`source .venv/bin/activate` on
Linux/macOS, `.venv\Scripts\activate` on Windows) and run the scripts directly.

# Code Structure

```
.
├── main.py                 # entry point stub
├── on_off.py               # take an on/off observation pair and plot the difference
├── on_off_plotter.py       # browse and re-plot previously saved observations
├── gain_cal.py             # sweep the SDR gain and live-plot the spectrum
├── ttt/                    # hardware + data-processing library
│   ├── rtlsdr.py
│   ├── file_io.py
│   ├── plots.py
│   ├── interface.py
│   ├── utils.py
│   └── mount.py
├── assets/                 # static assets (e.g. alert sounds)
└── data/                   # observations, created on first run
```

## Applications (top level)

Each application is a standalone script run from the repository root.

- `on_off.py` — the main observing script. Opens the SDR, prompts you to point
  the antenna off-source and then on-source, saves both spectra under `data/`,
  and plots the on−off difference. Observing parameters (`INTEGRATION_TIME`,
  `GAIN`, `BIN_SIZE`) are constants at the top of the file.
- `on_off_plotter.py` — offline viewer. Lists the observation dates and
  observations found in `data/`, then plots the selected on−off spectrum
  alongside the raw on and off spectra.
- `gain_cal.py` — gain calibration helper. Steps the gain from `min_gain` to
  `max_gain` and updates a live spectrum plot at each step.

## Library (`ttt/`)

- `rtlsdr.py` — `RTLSDR` class wrapping [rtlobs](https://github.com/EmmanuelSchaan/rtlobs).
  Used as a context manager: entering acquires the device and turns the bias tee
  on to power the LNA, exiting turns it off and disconnects. `take_exposure()`
  returns `(freqs, powers, overhead_time)`; `set_gain()` adjusts gain in place.
- `file_io.py` — on-disk layout and I/O. Spectra are saved as `.npy` arrays of
  `[freqs, powers]` columns at
  `data/<YYYYMMDD>/<HH:MM:SS>_<gain>dB_<integration_time>s/{on,off}.npy`. Provides
  the path builders, `save_spectrum()`, and the loaders used by the plotter.
- `plots.py` — matplotlib helpers. `plot_spectrum()` draws (and can update, for
  live plotting) a single spectrum; `plot_on_off_spectrum()` overlays the on and
  off traces. Frequencies are converted from Hz to MHz for display.
- `interface.py` — terminal prompts. `print_instruction()` prints banner-padded
  lines and optionally waits for user input.
- `utils.py` — shared constants and enums: `H1_LINE` (the 1420.405751768 MHz
  hydrogen line, the default center frequency) and `SpectrumType`.
- `mount.py` — placeholder for future antenna-mount control.

