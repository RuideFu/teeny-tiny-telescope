
from datetime import datetime

from matplotlib import pyplot as plt

from ttt.mount_ascom import choose_driver, connect, slew_ra_dec, disconnect

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
BIN_SIZE = 512

OFF_RA = 20
OFF_DEC = 40

TARGET_RA = 18.0  # Right Ascension in hours
TARGET_DEC = -20.0  # Declination in degrees

if __name__ == "__main__":

    # set up mount
    telescope_prog_id = choose_driver("Telescope")
    telescope = connect(telescope_prog_id)

    try:
        time_stamp = datetime.now()
        with RTLSDR(
            integration_time=INTEGRATION_TIME, gain=GAIN, bin_size=BIN_SIZE
        ) as rtl:

            print("Pointing the antenna at the off position (RA: {}, Dec: {})".format(OFF_RA, OFF_DEC))
            # slew to off coordinates (RA, Dec)
            slew_ra_dec(telescope, OFF_RA, OFF_DEC)
            print("Taking Off Observation")
            freqs, powers, overhead_time = rtl.take_exposure()
            off_filename = file_path(SpectrumType.OFF, time_stamp, GAIN, INTEGRATION_TIME)
            save_spectrum(freqs, powers, off_filename)

            # take on observation:
            print("Pointing the antenna at the on position (RA: {}, Dec: {})".format(TARGET_RA, TARGET_DEC))
            slew_ra_dec(telescope, TARGET_RA, TARGET_DEC)
            print("Taking On Observation")
            freqs, powers, overhead_time = rtl.take_exposure()
            on_filename = file_path(SpectrumType.ON, time_stamp, GAIN, INTEGRATION_TIME)
            save_spectrum(freqs, powers, on_filename)
    finally:
        disconnect(telescope)

    # load the on and off spectra
    freqs, on_off_powers = load_on_off_spectrum(time_stamp, GAIN, INTEGRATION_TIME)
    # plot the on-off spectrum
    plot_spectrum(freqs, on_off_powers, "On-Off Spectrum")
    plt.show()
