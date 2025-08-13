from matplotlib import pyplot as plt

from ttt.rtlsdr import RTLSDR
from ttt.plots import plot_spectrum

min_gain = 5
max_gain = 100
gain_step = 5


if __name__ == "__main__":
    with RTLSDR(integration_time=1, gain=min_gain) as rtl:
        try:
            plt.ion()
            freqs, powers, _ = rtl.take_exposure()
            graph = plot_spectrum(freqs, powers, f"Spectrum for Gain {min_gain} dB")
            for gain in range(min_gain, max_gain + 1, gain_step):
                rtl.set_gain(gain)
                freqs, powers, overhead_time = rtl.take_exposure()
                print(f"Overhead time: {overhead_time.total_seconds()} seconds")
                graph = plot_spectrum(
                    freqs, powers, f"Spectrum for Gain {gain} dB", graph
                )
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            plt.ioff()
            plt.show()
