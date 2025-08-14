from matplotlib import pyplot as plt
import numpy as np


def plot_spectrum(freqs: np.ndarray, powers: np.ndarray, title: str, graph=None):
    """
    Plot the spectrum with frequency on the x-axis and power on the y-axis.
    """
    if graph is not None:
        graph.remove()
    graph = plt.plot(freqs, powers / 1e6, color="b")[0]

    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Power (dB)")
    plt.title(title)
    plt.pause(0.1)

    return graph

def plot_on_off_spectrum(freqs: np.ndarray, 
                         on_powers: np.ndarray,
                         off_powers: np.ndarray):
    fig, axis = plt.subplots()
    axis.plot(freqs, on_powers / 1e6, color="blue", label="On Spectrum")
    axis.plot(freqs, off_powers / 1e6, color="red", label="Off Spectrum")
    axis.set_xlabel("Frequency (MHz)")
    axis.set_ylabel("Power (dB)")
    axis.legend()
    axis.set_title("On and Off Spectrum")
