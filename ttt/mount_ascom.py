import win32com.client
from astropy.coordinates import SkyCoord

def connect(telescope_prog_id):
    telescope = win32com.client.Dispatch(telescope_prog_id)
    telescope.Connected = True
    print("Connected to telescope: " + telescope.Name)
    print("CanSlewAltAz: " + str(telescope.CanSlewAltAz))
    print("CanSlewAltAzAsync: " + str(telescope.CanSlewAltAzAsync))
    print("currentAltitude: " + str(telescope.Altitude))
    print("currentAzimuth: " + str(telescope.Azimuth))
    return telescope

def slew_alt_az(telescope, altitude, azimuth):
    if telescope.atPark:
        telescope.Unpark()
    print("Slewing to Altitude: " + str(altitude) + ", Azimuth: " + str(azimuth))
    telescope.SlewToAltAzAsync(altitude, azimuth)
    while telescope.Slewing:
        pass
    print("Slew complete")

def slew_ra_dec(telescope, right_ascension, declination):
    if telescope.atPark:
        telescope.Unpark()
    print("Slewing to Right Ascension: " + str(right_ascension) + ", Declination: " + str(declination))
    telescope.SlewToCoordinatesAsync(right_ascension, declination)
    while telescope.Slewing:
        pass
    print("Slew complete")    

def slew_galactic(telescope, galactic_longitude, galactic_latitude):
    coordinate = SkyCoord(l=galactic_longitude, b=galactic_latitude, frame='galactic', unit='deg')
    ra_dec = coordinate.icrs
    right_ascension = ra_dec.ra.deg
    declination = ra_dec.dec.deg
    slew_ra_dec(telescope, right_ascension, declination)

def disconnect(telescope):
    telescope.Park()
    telescope.Connected = False
    del telescope
    print("Disconnected from telescope")

def choose_driver(device_type):
    print("Choose a " + device_type + " driver")
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = device_type
    return chooser.Choose(None)

if __name__ == "__main__":
    telescope_prog_id = choose_driver("Telescope")
    telescope = connect(telescope_prog_id)
    # slew_alt_az(telescope, 90.0, 0.0)
    # telescope.SetPark()
    slew_ra_dec(telescope, 18, -20.0)
    disconnect(telescope)
