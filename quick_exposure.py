from matplotlib import pyplot as plt

from ttt.interface import print_instruction
from ttt.plots import plot_spectrum
from ttt.rtlsdr import RTLSDR

INTEGRATION_TIME = 15  # seconds
GAIN = 50  # dB
BIN_SIZE = 512


if __name__ == "__main__":
    print_instruction(["Taking Quick Exposure", "Point the antenna at the target"])

    with RTLSDR(
        integration_time=INTEGRATION_TIME,
        gain=GAIN,
        bin_size=BIN_SIZE,
    ) as rtl:
        input(
            "Bias tee is ON. Measure the unloaded SMA voltage now, "
            "then press Enter to expose..."
        )
        freqs, powers, overhead_time = rtl.take_exposure()

    print(f"Overhead time: {overhead_time.total_seconds():.3f} seconds")
    plot_spectrum(freqs, powers, "Quick Exposure")
    plt.show()
