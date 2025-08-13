import numpy as np
from matplotlib import pyplot as plt

from ttt.plots import plot_on_off_spectrum

on_path = "data/20250812_233031_on_50db_300.npy"
off_path = "data/20250812_232216_off_50db_300.npy"

on_data = np.load(on_path)
on_freqs, on_powers = on_data[:, 0], on_data[:, 1]

off_data = np.load(off_path)
off_freqs, off_powers = off_data[:, 0], off_data[:, 1]

on_off_powers = (on_powers - off_powers) / off_powers

plot_on_off_spectrum(on_freqs, on_powers, off_powers)
plt.show()
