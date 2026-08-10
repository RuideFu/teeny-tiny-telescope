import win32com.client

def connect(telescope_prog_id):
    telescope = win32com.client.Dispatch(telescope_prog_id)
    telescope.Connected = True
    print("Connected to telescope: " + telescope.Name)
    print("CanSlewAltAz: " + str(telescope.CanSlewAltAz))
    print("CanSlewAltAzAsync: " + str(telescope.CanSlewAltAzAsync))
    print("currentAltitude: " + str(telescope.Altitude))
    print("currentAzimuth: " + str(telescope.Azimuth))
    return telescope

def slew(telescope, altitude, azimuth):
    if telescope.atPark:
        telescope.Unpark()
    print("Slewing to Altitude: " + str(altitude) + ", Azimuth: " + str(azimuth))
    telescope.SlewToAltAzAsync(altitude, azimuth)
    while telescope.Slewing:
        pass
    print("Slew complete")
    

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
    slew(telescope, 45.0, 45.0)
    disconnect(telescope)

    
