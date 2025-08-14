from datetime import datetime
from enum import Enum
import os

import numpy as np
from matplotlib import pyplot as plt

from ttt.rtlsdr import RTLSDR
from ttt.plots import plot_spectrum
from ttt.file_io import (
    save_spectrum,
    file_path,
    load_on_off_spectrum,
)
from ttt.utils import SpectrumType
from ttt.interface import print_instruction

INTEGRATION_TIME = 1  # seconds
GAIN = 50  # dB


if __name__ == "__main__":
    time_stamp = datetime.now()
    with RTLSDR(integration_time=INTEGRATION_TIME, gain=GAIN) as rtl:

        # off observation first:
        print_instruction(
            ["Taking Off Observation", "Point the antenna away from the source"]
        )

        freqs, powers, overhead_time = rtl.take_exposure()
        off_filename = file_path(SpectrumType.OFF, time_stamp, GAIN, INTEGRATION_TIME)
        save_spectrum(freqs, powers, off_filename)

        # take on observation:
        print_instruction(
            ["Taking On Observation", "Point the antenna towards the source"]
        )
        freqs, powers, overhead_time = rtl.take_exposure()
        on_filename = file_path(SpectrumType.ON, time_stamp, GAIN, INTEGRATION_TIME)
        save_spectrum(freqs, powers, on_filename)

    # load the on and off spectra
    freqs, on_off_powers = load_on_off_spectrum(time_stamp, GAIN, INTEGRATION_TIME)
    # plot the on-off spectrum
    plot_spectrum(freqs, on_off_powers, "On-Off Spectrum")
    plt.show()
