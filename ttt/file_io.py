from datetime import datetime
import os

import numpy as np

from .utils import SpectrumType

DATA_PATH = "data"


def date_path(date: datetime) -> str:
    """
    Generate a path for the observation date.
    Args:
        date (datetime): The date of the observation.
    Returns:
        str: The path for the observation date.
    """
    return os.path.join(DATA_PATH, date.strftime("%Y%m%d"))


def observation_path(date: datetime, gain: int, integration_time: float) -> str:
    """
    Generate a path for the observation based on date, gain, and integration time.
    Args:
        date (datetime): The date of the observation.
        gain (int): Gain in dB.
        integration_time (float): Integration time in seconds.
    Returns:
        str: The path for the observation.
    """
    return os.path.join(
        date_path(date), f"{date.strftime('%H:%M:%S')}_{gain}dB_{integration_time}s"
    )


def file_path(
    spectrum_type: SpectrumType, date: datetime, gain: int, integration_time: float
) -> str:
    """
    Generate a file path for the spectrum data.
    Args:
        spectrum_type (SpectrumType): The type of spectrum (ON or OFF).
        date (datetime): The date of the observation.
        gain (int): Gain in dB.
        integration_time (float): Integration time in seconds.
    Returns:
        str: The file path for the spectrum data.
    """
    _observation_path = observation_path(date, gain, integration_time)
    if not os.path.exists(_observation_path):
        os.makedirs(_observation_path, exist_ok=True)
    return os.path.join(_observation_path, f"{spectrum_type.value}.npy")


def save_spectrum(freqs: np.ndarray, powers: np.ndarray, filename: str):
    """
    Save the spectrum data to a file.
    Args:
        freqs (np.ndarray): Frequencies in MHz.
        powers (np.ndarray): Powers in dB.
        filename (str): The name of the file to save the data.
    """
    # Transpose to have freqs and powers in columns
    table = np.array([freqs, powers]).T
    np.save(filename, table)
    print(f"Spectrum saved to {filename}")


def load_observation_dates() -> list[str]:
    """
    Load the observation dates from the data directory.
    Returns:
        list[str]: List of observation dates in YYYYMMDD format.
    """
    if not os.path.exists(DATA_PATH):
        return []
    return sorted(
        [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))]
    )


def load_observation_paths(date_str: str) -> list[str]:
    """
    Load the observations for a specific date.
    Args:
        date_str (str): The date in YYYYMMDD format.
    Returns:
        list[str]: List of observation files for the specified date.
    """
    date_path = os.path.join(DATA_PATH, date_str)
    if not os.path.exists(date_path):
        return []
    return sorted([f for f in os.listdir(date_path)])


def load_on_off_spectrum(time_stamp: datetime, gain: int,
                         integration_time: float):
    """
    Load the on and off spectrum data based on the timestamp, gain, and integration time.
    Args:
        time_stamp (datetime): The timestamp of the observation.
        gain (int): Gain in dB.
        integration_time (float): Integration time in seconds.
    Returns:
        tuple: Frequencies and the difference in powers between on and off observations.
    """
    on_data = np.load(
        file_path(SpectrumType.ON, time_stamp, gain, integration_time))
    off_data = np.load(
        file_path(SpectrumType.OFF, time_stamp, gain, integration_time))
    on_freqs, on_powers = on_data[:, 0], on_data[:, 1]
    off_powers = off_data[:, 1]
    return on_freqs, on_powers - off_powers


def load_on_off_spectrum_from_observation(
    date_str: str,
    observation_str: str,
): 
    """
    Load the on and off spectrum data from a specific observation.
    Args:
        date_str (str): The date in YYYYMMDD format.
        observation_str (str): The observation identifier.
    Returns:
        tuple: Frequencies and the difference in powers between on and off observations.
    """
    date_path = os.path.join(DATA_PATH, date_str, observation_str)
    on_data = np.load(os.path.join(date_path, SpectrumType.ON.value + ".npy"))
    off_data = np.load(os.path.join(date_path, SpectrumType.OFF.value + ".npy"))
    on_freqs, on_powers = on_data[:, 0], on_data[:, 1]
    off_powers = off_data[:, 1]
    return on_freqs, on_powers - off_powers