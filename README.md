# Teeny Tiny Telescope (`ttt`)

Software for the ERIRA teeny tiny radio telescope: acquire 21 cm hydrogen-line
spectra with an RTL-SDR, save and compare on/off-source observations, and
optionally control an Explore Scientific PMC-Eight telescope mount.

The repository is organized as standalone applications at the project root and
reusable hardware, storage, plotting, and terminal helpers in `ttt/`.

## Hardware

The observing scripts are built around:

- an antenna and low-noise amplifier (exact models are not yet documented);
- a [Nooelec NESDR SMArTee XTR SDR](https://www.nooelec.com/store/nesdr-smartee-xtr-sdr.html), including its bias tee for powering the amplifier; and
- optionally, an Explore Scientific PMC-Eight mount (tested with the
  iEXOS-100-02 and firmware 20A01).

The SDR wrapper enables the bias tee when it connects and disables it before
disconnecting. Verify that the attached RF hardware can safely accept bias-tee
power before running an acquisition script.

## Setup

The project requires Python 3.14 or newer and uses
[`uv`](https://docs.astral.sh/uv/) for dependency management.

1. Install `uv` by following the
   [official installation guide](https://docs.astral.sh/uv/getting-started/installation/).
2. From the repository root, create and synchronize the environment:

   ```bash
   uv sync
   ```

3. Run scripts through the managed environment:

   ```bash
   uv run on_off.py
   ```

`pyproject.toml` and `uv.lock` are the authoritative dependency definitions.
The older `requirements.txt` does not contain every current dependency and
should not be used to reproduce the complete environment.

### Optional mount setup

There are two mount-control backends:

- `ttt/mount.py` communicates directly with a PMC-Eight controller over a
  115200-baud serial connection and works through `pyserial`.
- `ttt/mount_ascom.py` uses the Windows ASCOM platform and the ES PMC-Eight
  ASCOM driver. Its scripts require Windows, a configured ASCOM driver, and
  `pywin32`, which is intentionally not part of the cross-platform dependency
  set. Install it in the project environment with `uv pip install pywin32`.

The ASCOM scripts currently use the driver ID
`ASCOM.ES_PMC8.Telescope`. Update that value in the script if the installed
driver exposes a different ID.

## Applications

Run every application from the repository root so relative `data/` paths
resolve consistently. Acquisition constants such as integration time, gain,
bin size, and target coordinates are defined near the top of each script.

| Command | Purpose | Hardware |
| --- | --- | --- |
| `uv run on_off.py` | Prompt for manual off-source and on-source pointing, acquire both spectra, save them, and plot their difference. | RTL-SDR |
| `uv run quick_exposure.py` | Take and plot one short spectrum without saving it. It pauses after enabling the bias tee so its unloaded voltage can be measured. | RTL-SDR |
| `uv run gain_cal.py` | Sweep SDR gain from 5 to 100 dB and update a live spectrum plot. | RTL-SDR |
| `uv run on_off_plotter.py` | Browse saved observation dates and plot the selected difference plus its raw on/off spectra. | None |
| `uv run galactic.py` | Slew through ASCOM to configured off/on equatorial coordinates, acquire both spectra, save them, and plot the difference. | RTL-SDR, Windows ASCOM mount |
| `uv run sync_telescope.py` | Configure the Green Bank site coordinates and synchronize a physically aligned ASCOM mount at the north celestial pole. | Windows ASCOM mount |
| `uv run ttt/mount.py` | Run the direct-serial PMC-Eight motion self-test. Set the serial port at the bottom of the module first. | Serial PMC-Eight mount |

`main.py` is currently a project scaffold only; it does not launch the
observing workflow. The `ttt/mount.py` self-test physically moves both mount
axes; clear the mount's travel path and be ready to cut power before running
it.

## Observation data

Acquisition scripts create the ignored `data/` directory on first save. Each
on/off pair is stored as two NumPy arrays:

```text
data/
`-- YYYYMMDD/
    `-- HHMMSS_<gain>dB_<integration-time>s/
        |-- off.npy
        `-- on.npy
```

Each `.npy` file contains a two-column array of frequency in Hz and power in
dB. The processed spectrum is calculated when loaded as `on - off`; it is not
written as a separate file.

## Repository structure

```text
.
|-- main.py                 # Placeholder entry point
|-- on_off.py               # Manual on/off acquisition
|-- on_off_plotter.py       # Saved-observation browser and plotter
|-- quick_exposure.py       # Unsaved single exposure
|-- gain_cal.py             # Live SDR gain sweep
|-- galactic.py             # ASCOM-controlled on/off acquisition
|-- sync_telescope.py       # ASCOM mount site setup and synchronization
|-- ttt/
|   |-- rtlsdr.py           # rtlobs wrapper and bias-tee lifecycle
|   |-- file_io.py          # Observation paths and NumPy persistence
|   |-- plots.py            # Matplotlib spectrum helpers
|   |-- interface.py        # Terminal instruction prompts
|   |-- utils.py            # Hydrogen-line constant and spectrum types
|   |-- mount.py            # Direct serial PMC-Eight driver
|   `-- mount_ascom.py      # Windows ASCOM mount helpers
|-- assets/                 # Static assets
|-- pyproject.toml          # Project metadata and dependencies
|-- uv.lock                 # Reproducible dependency lockfile
`-- requirements.txt        # Legacy, incomplete pip dependency list
```

The default SDR center frequency is the neutral hydrogen line at
1420.405751768 MHz. `ttt.rtlsdr.RTLSDR` is a context manager so the SDR and
bias tee are cleaned up on normal exit; mount interfaces should likewise be
used with their provided cleanup paths to stop motion and disconnect safely.

## License

This project is distributed under the terms in [LICENSE](LICENSE).
