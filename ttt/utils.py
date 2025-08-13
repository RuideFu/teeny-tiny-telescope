from enum import Enum

H1_LINE = 1420.405751768  # Hydrogen line frequency in MHz


class SpectrumType(Enum):
    ON = "on"
    OFF = "off"
    PROCESSED = "processed"
