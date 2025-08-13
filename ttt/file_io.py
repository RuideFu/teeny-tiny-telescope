from datetime import datetime
import os

import numpy as np

from .utils import SpectrumType

DATA_PATH = "data"


def print_instruction(content: list[str]):
    """
    Print instructions for the user.
    Args:
        content (str): The content to print.
    """
    _width = 80
    content.append("Press *enter* to continue...")
    for line in content:
        line = line.center(_width, "=")
        print(line)
    if input():
        print("Continuing...".center(_width, "="))
        return


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
    date = time_stamp.strftime("%Y%m%d")
    date_path = os.path.join(DATA_PATH, date)
    if not os.path.exists(date_path):
        os.makedirs(date_path)
    return os.path.join(
        date,
        f"{time_stamp.strftime('%Y%m%d_%H%M%S')}_{spectrum_type.value}_{gain}db_{integration_time}s.npy",
    )


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


def load_on_off_spectrum(time_stamp: datetime, gain: int, integration_time: float):
    """
    Load the on and off spectrum data based on the timestamp, gain, and integration time.
    Args:
        time_stamp (datetime): The timestamp of the observation.
        gain (int): Gain in dB.
        integration_time (float): Integration time in seconds.
    Returns:
        tuple: Frequencies and the difference in powers between on and off observations.
    """
    on_filename = file_name(SpectrumType.ON, time_stamp, gain, integration_time)
    off_filename = file_name(SpectrumType.OFF, time_stamp, gain, integration_time)

    on_data = np.load(os.path.join(DATA_PATH, on_filename))
    off_data = np.load(os.path.join(DATA_PATH, off_filename))
    on_freqs, on_powers = on_data[:, 0], on_data[:, 1]
    off_powers = off_data[:, 1]
    return on_freqs, on_powers - off_powers
