from datetime import datetime, timedelta, timezone

from rtlobs import collect, utils

from .utils import H1_LINE


class RTLSDR:

    def __init__(
        self,
        sample_size: int = 4096,
        bin_size: int = 1024,
        gain: float = 49.6,
        sample_rate: float = 2.048e6,
        center_freq: float = H1_LINE,
        integration_time: int = 1,
    ):
        """
        Initialize the RTLSDR parameters.
        Args:
            sample_size (int): Number of samples to collect.
            bin_size (int): Size of each frequency bin.
            gain (float): Gain level for the RTL-SDR.
            sample_rate (float): Sample rate in Hz.
            center_freq (float): Center frequency in MHz.
            integration_time (int): Integration time in seconds.
        """
        # initialize the parameters for the RTL-SDR
        self._sample_size = sample_size
        self._bin_size = bin_size
        self._gain = gain
        self._sample_rate = sample_rate
        self._center_freq = center_freq
        self._integration_time = integration_time

    def __enter__(self):
        """
        Enter the context manager for RTLSDR.
        Returns:
            self: The instance of RTLSDR.
        """
        self.sdr = collect.get_sdr(self._sample_rate, self.get_center_freq, self._gain)
        self.bias_tee_on()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager for RTLSDR.
        Args:
            exc_type: Exception type.
            exc_value: Exception value.
            traceback: Traceback object.
        """
        self.bias_tee_off()
        self.disconnect()

    @property
    def get_center_freq(self):
        """
        Get the center frequency of the RTL-SDR.
        Returns:
            float: Center frequency in Hz.
        """
        return self._center_freq * 1e6  # Convert MHz to Hz

    @property
    def get_gain(self):
        """
        Get the current gain of the RTL-SDR.
        Returns:
            float: Current gain in dB to 2 decimal places.
        """
        return round(self._gain, 2)
        

    def set_gain(self, gain: float):
        """
        Set the gain for the RTL-SDR.
        Args:
            gain (float): Gain level to set.
        """
        self._gain = gain
        self.sdr.set_gain(gain)
        print(f"Gain set to {gain} dB")

    def bias_tee_on(self):
        """
        Turn on the bias tee to power the LNA.
        """
        # Code to turn on the bias tee
        try:
            utils.biast(1, index=0)
            print("Bias Tee turned on.")
        except Exception as e:
            print(f"Error turning on bias tee: {e}")

    def bias_tee_off(self):
        """
        Turn off the bias tee to power off the LNA.
        """
        # Code to turn off the bias tee
        try:
            utils.biast(0, index=0)
            print("Bias Tee turned off.")
        except Exception as e:
            print(f"Error turning off bias tee: {e}")

    def take_exposure(self):
        """
        Take an exposure with the RTL-SDR.
        Returns:
            freqs: float[] Frequencies in MHz.
            powers: float[] Powers in dB.
            overhead_time: datetime.timedelta Overhead time taken for the exposure.
        """

        start_time = datetime.now(timezone.utc)

        try:
            freqs, powers = collect.run_spectrum_int(
                self._sample_size,
                self._bin_size,
                self._gain,
                self._sample_rate,
                self.get_center_freq,
                self._integration_time,
                self.sdr,
            )
            end_time = datetime.now(timezone.utc)
            return freqs, powers, end_time - start_time - timedelta(seconds=self._integration_time)
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            print(f"Error taking exposure: {e}")
            return None, None, end_time - start_time - timedelta(seconds=self._integration_time)

    def disconnect(self):
        """
        Disconnect the RTL-SDR.
        """
        if self.sdr:
            self.sdr.close()
            print("RTL-SDR disconnected.")
        else:
            print("RTL-SDR is not connected.")
