from datetime import datetime
from enum import Enum
import os

import numpy as np
from matplotlib import pyplot as plt

from ttt.rtlsdr import RTLSDR
from ttt.plots import plot_spectrum

INTEGRATION_TIME = 10  # seconds
GAIN = 50  # dB
DATA_PATH = "data"  # Directory to save data files


def print_instruction(content: list[str]):
    """
    Print instructions for the user.
    Args:
        content (str): The content to print.
    """
    _width = 100
    content.append("Press *enter* to continue...")
    for line in content:
        line = line.center(_width, "=")
        print(line)
    if input():
        return


class SpectrumType(Enum):
    ON = "on"
    OFF = "off"

    PROCESSED = "processed"


def file_name(
    spectrum_type: SpectrumType,
    time_stamp: datetime,
    gain: int,
    integration_time: float,
) -> str:
    """
    Generate a file name based on the spectrum type, gain, and integration time.
    Args:
        spectrum_type (SpectrumType): The type of spectrum.
        gain (int): Gain in dB.
        integration_time (float): Integration time in seconds.
    Returns:
        str: Generated file name.
    """

    return f"{time_stamp.strftime('%Y%m%d_%H%M%S')}_{spectrum_type.value}_{gain}db_{integration_time}.npy"


def save_spectrum(freqs: np.ndarray, powers: np.ndarray, filename: str):
    """
    Save the spectrum data to a file.
    Args:
        freqs (np.ndarray): Frequencies in MHz.
        powers (np.ndarray): Powers in dB.
        filename (str): The name of the file to save the data.
    """
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    # Transpose to have freqs and powers in columns
    table = np.array([freqs, powers]).T
    np.save(os.path.join(DATA_PATH, filename), table)
    print(f"Spectrum saved to {filename}")


if __name__ == "__main__":
    time_stamp = datetime.now()
    with RTLSDR(integration_time=INTEGRATION_TIME, gain=GAIN) as rtl:

        # off observation first:
        print_instruction(
            ["Taking Off Observation", "Point the antenna away from the source"]
        )

        freqs, powers, overhead_time = rtl.take_exposure()
        off_filename = file_name(SpectrumType.OFF, time_stamp, GAIN, INTEGRATION_TIME)
        save_spectrum(freqs, powers, off_filename)

        # take on observation:
        print_instruction(
            ["Taking On Observation", "Point the antenna towards the source"]
        )
        freqs, powers, overhead_time = rtl.take_exposure()
        on_filename = file_name(SpectrumType.ON, time_stamp, GAIN, INTEGRATION_TIME)
        save_spectrum(freqs, powers, on_filename)

    # open off observation file
    off_data = np.load(os.path.join(DATA_PATH, off_filename))
    off_freqs, off_powers = off_data[:, 0], off_data[:, 1]

    # open on observation file
    on_data = np.load(os.path.join(DATA_PATH, on_filename))
    on_freqs, on_powers = on_data[:, 0], on_data[:, 1]

    # calculate on-off spectrum
    on_off_powers = (on_powers - off_powers) / off_powers

    # plot the on-off spectrum
    plot_spectrum(on_freqs, on_off_powers, "On-Off Spectrum")
    plt.show()
