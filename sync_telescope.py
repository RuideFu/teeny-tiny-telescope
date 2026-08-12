"""Synchronize the ASCOM mount at its north-celestial-pole position."""

from astropy import units as u
from astropy.time import Time

from ttt.mount_ascom import choose_driver, connect


# Green Bank Telescope coordinates published by Green Bank Observatory.
GREEN_BANK_LATITUDE = 38 + 25 / 60 + 59.236 / 3600
GREEN_BANK_LONGITUDE = -(79 + 50 / 60 + 23.406 / 3600)
GREEN_BANK_ELEVATION = 807.43
NORTH_CELESTIAL_POLE_DEC = 90.0


def format_hours(hours: float) -> str:
    total_seconds = round((hours % 24) * 3600) % (24 * 3600)
    hour, remainder = divmod(total_seconds, 3600)
    minute, second = divmod(remainder, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def green_bank_lst() -> float:
    return Time.now().sidereal_time(
        "apparent", longitude=GREEN_BANK_LONGITUDE * u.deg
    ).hour


def main() -> None:
    # telescope_prog_id = choose_driver("Telescope")
    # print(telescope_prog_id)
    telescope = connect("ASCOM.ES_PMC8.Telescope")
    

    try:
        if not telescope.CanSync:
            raise RuntimeError("The selected ASCOM telescope driver cannot synchronize.")
        if telescope.Slewing:
            raise RuntimeError("The telescope is slewing; stop it before synchronizing.")

        telescope.SiteLatitude = GREEN_BANK_LATITUDE
        telescope.SiteLongitude = GREEN_BANK_LONGITUDE
        telescope.SiteElevation = GREEN_BANK_ELEVATION

        print("\nPhysically place the mount in its neutral position:")
        print("  - polar axis aligned with the north celestial pole")
        print("  - telescope pointing at the north celestial pole")
        print("  - counterweight shaft in the neutral/home orientation")
        confirmation = input("Type SYNC when the mount is positioned correctly: ").strip()
        if confirmation != "SYNC":
            print("Synchronization cancelled.")
            return

        if telescope.AtPark:
            telescope.Unpark()

        lst = green_bank_lst()
        print(
            "Synchronizing to "
            f"RA {format_hours(lst)} LST, Dec {NORTH_CELESTIAL_POLE_DEC:+.1f} deg"
        )
        telescope.SyncToCoordinates(lst, GREEN_BANK_LATITUDE)
        telescope.SetPark()
        print(
            "Synchronization complete and current position set as park. Mount reports "
            f"RA {format_hours(telescope.RightAscension)}, "
            f"Dec {telescope.Declination:+.4f} deg."
        )
    finally:
        # Do not call disconnect(): it parks the mount and may move it after sync.
        telescope.Connected = False
        print("Disconnected from telescope without parking.")


if __name__ == "__main__":
    main()
