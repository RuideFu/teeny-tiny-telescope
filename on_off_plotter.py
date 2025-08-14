import os

from matplotlib import pyplot as plt

from ttt.file_io import (
    load_observation_dates,
    load_observation_paths,
    load_on_off_spectrum_from_observation,
)
from ttt.interface import print_instruction
from ttt.plots import plot_spectrum


if __name__ == "__main__":
    date_dirs = load_observation_dates()
    if not date_dirs:
        print_instruction(
            ["No observation dates found.", "Please take observations first."], False
        )
        exit(0)
    else:
        print_instruction(["Available Observation Dates:"], False)
        for date in date_dirs:
            print(f" - {date}")

    user_date = print_instruction(["Select a date to view the on-off spectra."])
    if user_date not in date_dirs:
        print_instruction(
            [f"Date {user_date} not found.", "Please select a valid date."], False
        )
        exit(1)

    print_instruction(["Available Observations for", user_date], False)
    observation_dirs = load_observation_paths(user_date)
    if not observation_dirs:
        print_instruction(["No observations found for the selected date."], False)
        exit(0)
    for obs in observation_dirs:
        print(f" - {obs}")

    user_obs = print_instruction(["Select an observation to view the on-off spectrum."])
    if user_obs not in observation_dirs:
        print_instruction(
            [
                f"Observation {user_obs} not found.",
                "Please select a valid observation.",
            ],
            False,
        )
        exit(1)

    print_instruction(["Loading on-off spectrum for", user_obs], False)
    freqs, powers = load_on_off_spectrum_from_observation(user_date, user_obs)

    # plot the on-off spectrum
    plot_spectrum(freqs, powers, f"On-Off Spectrum for {user_obs}")
    plt.show()
