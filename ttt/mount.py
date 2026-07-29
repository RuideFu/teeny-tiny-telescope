"""Serial control for an Explore Scientific PMC-Eight mount (iEXOS-100-02).

Command syntax follows the PMC-Eight Programmer's Reference, DOC-ESPMC8-002
Rev. 1.2, 2019 March 07, written for firmware 09T10 / 10A01.

    ES{G,S,T,P}{p,r,t,d,v,i,x}(A)(XXXX)(YYYYYY)!

where A is the axis, XXXX a 4-hex-digit rate and YYYYYY a 6-hex-digit,
24-bit two's-complement motor count. SET commands echo the corresponding GET
response, so "ESSp0..." is answered by "ESGp0...".

Measured against firmware 20A01, which differs from the manual in four ways
worth knowing:

  * Unimplemented commands draw no reply at all rather than an error, and the
    documented "ESSt" has no opcode -- it is one of them.
  * ESGv returns a longer, multi-line string.
  * ESSr/ESGr are unscaled counts per second, not the x25 "precision" scale
    that ESTr/ESGx use.
  * ESSr sets a standing drive rate that ESPt ramps down to rather than
    stopping, and a non-zero value fights the point command: the axis either
    sails past the target or crawls at a twentieth of its normal speed. Every
    slew here zeroes it first. RA powers up with it at sidereal, so RA keeps
    moving after a slew until it is zeroed, and setting the ESTr tracking
    rate to zero does not stop it.
  * ESGr reports the *live* rate, which reads 0 whenever the axis is idle
    regardless of the commanded rate. You cannot test whether the rate needs
    zeroing by reading it -- just write it.
  * ESPt does not land exactly. A 100,000-count slew ramps to roughly 20,000
    counts/sec and overshoots by a few hundred, and RA resumes sidereal once
    it arrives. move_axis_to() re-points until it is inside tolerance rather
    than treating either as a failure; RA typically needs one extra pass and
    DEC none.
"""

import threading
import time

import serial

RA_AXIS = 0
DEC_AXIS = 1

# Mount gearing. These are the iEXOS-100 / EXOS-2 values from the reference's
# stepper drive parameter table: 144 primary teeth x 4.5 secondary x 200 steps
# x 32 microsteps = 4,147,200 counts per revolution, i.e. 0.3125 arcsec/count.
# Most worked examples in the manual use the ES/Losmandy G-11 instead
# (4,608,000 counts, 0.28125 arcsec/count) -- do not copy those numbers here.
COUNTS_PER_REVOLUTION = 4_147_200
ARCSEC_PER_COUNT = 360 * 60 * 60 / COUNTS_PER_REVOLUTION

# Positions are 24-bit two's complement.
COUNTS_MIN = -(1 << 23)
COUNTS_MAX = (1 << 23) - 1

# ESTr/ESGx take counts per second scaled by 25 (the "precision" scale).
# ESSr/ESGr do NOT: measured on firmware 20A01, RA tracking at sidereal reads
# back as 0x0030 = 48, which is 48 counts/sec unscaled.
RATE_SCALE = 25
RATE_MAX = 0xFFFF

# Sidereal is 15 arcsec/sec, so 48 counts/sec here, and 48 * 25 = 1200 =
# 0x04B0. The manual's 0x0535 is the G-11 figure and would track ~11% fast.
SIDEREAL_COUNTS_PER_SEC = 15.0 / ARCSEC_PER_COUNT
SIDEREAL_RATE = round(SIDEREAL_COUNTS_PER_SEC * RATE_SCALE)
TRACKING_OFF = 0

# The same rate as an unscaled ESSr value: 48, which is what RA's standing
# drive rate reads as when it is tracking.
SIDEREAL_DRIVE_RATE = round(SIDEREAL_COUNTS_PER_SEC)

# The mount has meaningful backlash and a servo deadband, and each count is
# only 0.31 arcsec, so demanding exact arrival is not achievable in practice.
DEFAULT_TOLERANCE_COUNTS = 20


class MountError(RuntimeError):
    """The mount replied, but not with what the command asked for."""


class PMCEight:
    """A class to communicate with an iEXOS-100-02 PMC-Eight mount via serial."""

    def __init__(
        self, port: str, timeout: float = 2.0, connect_timeout: float = 60.0
    ):
        self.timeout = timeout

        # Leave DTR/RTS asserted (pyserial's default). Deasserting them stops
        # this adapter talking to the controller entirely.
        self.serial = serial.Serial(
            port=port,
            baudrate=115_200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            write_timeout=timeout,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )

        self._lock = threading.Lock()

        # Discard anything left from a prior connection.
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        time.sleep(0.1)

        self._wait_until_responsive(connect_timeout)

    def _wait_until_responsive(self, connect_timeout: float) -> str:
        """
        Poll ESGv until the controller answers, and return its version.

        Opening the port asserts DTR, which resets the ESP8266 communications
        controller. It then swallows commands entirely for several seconds --
        longer when reopening the port soon after closing it. Without this
        wait the first handful of commands silently time out, which looks
        exactly like a dead cable. Deasserting DTR is not the fix: this
        adapter needs it asserted to talk to the controller at all.
        """
        started = time.monotonic()
        deadline = started + connect_timeout
        attempts = 0

        while True:
            attempts += 1

            try:
                version = self.firmware_version()

                if attempts > 1:
                    print(
                        f"Mount answered after {time.monotonic() - started:.1f}s "
                        f"({attempts} attempts) while its comm controller reset"
                    )

                return version
            except (MountError, TimeoutError):
                if time.monotonic() >= deadline:
                    self.close()
                    raise MountError(
                        f"No reply from the mount on {self.serial.port} after "
                        f"{attempts} attempts over {connect_timeout:.0f}s. "
                        f"Check power, cable and port, and note that the "
                        f"iEXOS-100 ships with WiFi as its primary interface "
                        f"(see PMC-Eight application note AN003)."
                    ) from None

                time.sleep(0.5)

    def __enter__(self) -> "PMCEight":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        # Closing the port does not stop a slew, so always try to halt first.
        try:
            self.halt_all()
        except (MountError, TimeoutError, serial.SerialException) as error:
            print(f"Warning: could not halt the mount on exit: {error}")
        finally:
            self.close()

    def close(self) -> None:
        self.serial.close()

    @staticmethod
    def _decode_counts(value: str) -> int:
        counts = int(value, 16)

        # Convert 24-bit two's complement to a signed integer.
        if counts & 0x800000:
            counts -= 1 << 24

        return counts

    @staticmethod
    def _encode_counts(counts: int) -> str:
        if not COUNTS_MIN <= counts <= COUNTS_MAX:
            raise ValueError(
                f"Position {counts} is outside the 24-bit range "
                f"[{COUNTS_MIN}, {COUNTS_MAX}]; encoding it would wrap and "
                f"send the mount the long way around"
            )

        return f"{counts & 0xFFFFFF:06X}"

    def command(self, request: str, expected_prefix: str) -> str:
        """
        Send a command and return the first response matching expected_prefix.

        Frames that do not match are discarded. That matters because a command
        that times out leaves its reply in flight: it arrives during the *next*
        exchange and, if accepted blindly, shifts every subsequent response one
        command behind forever. Matching on the prefix resynchronises instead.
        """
        if not request.startswith("ES") or not request.endswith("!"):
            raise ValueError("PMC-Eight commands must start with ES and end with !")

        with self._lock:
            self.serial.write(request.encode("ascii"))
            self.serial.flush()

            deadline = time.monotonic() + self.timeout
            discarded = []

            while True:
                remaining = deadline - time.monotonic()

                if remaining <= 0:
                    break

                self.serial.timeout = remaining
                frame = self.serial.read_until(b"!")

                if not frame.endswith(b"!"):
                    break

                response = frame.decode("ascii", errors="replace").strip()

                if response.startswith(expected_prefix):
                    return response

                discarded.append(response)

            self.serial.timeout = self.timeout

        if discarded:
            raise MountError(
                f"No response starting with {expected_prefix!r} to {request!r}; "
                f"discarded {discarded!r}"
            )

        raise MountError(
            f"The mount sent nothing at all in response to {request!r}. The "
            f"firmware ignores commands it does not implement without replying, "
            f"so check that this command has an opcode in your firmware version "
            f"before suspecting the link. If no command gets a reply, then it is "
            f"the link: check the port, cable and power, and note that the "
            f"iEXOS-100 ships with WiFi as its primary interface (see PMC-Eight "
            f"application note AN003)."
        )

    @staticmethod
    def _check_axis(axis: int) -> int:
        if axis not in (RA_AXIS, DEC_AXIS):
            raise ValueError("Axis must be 0 (RA) or 1 (DEC)")

        return axis

    def firmware_version(self) -> str:
        # "ESGv!" -> "ESGvES6B09U0!" on the firmware the reference documents.
        # Firmware 20A01 returns a longer, multi-line string, so collapse the
        # embedded newlines into a single printable line.
        version = self.command("ESGv!", "ESGv")[4:-1]

        return " ".join(version.split())

    def axis_position_counts(self, axis: int) -> int:
        # "ESGp0!" -> "ESGp0FF37DA!"
        self._check_axis(axis)
        prefix = f"ESGp{axis}"
        response = self.command(f"ESGp{axis}!", prefix)

        return self._decode_counts(response[len(prefix) : -1])

    def axis_target_counts(self, axis: int) -> int:
        # "ESGt0!" -> "ESGt062E4D7!"
        self._check_axis(axis)
        prefix = f"ESGt{axis}"
        response = self.command(f"ESGt{axis}!", prefix)

        return self._decode_counts(response[len(prefix) : -1])

    def axis_rate(self, axis: int) -> int:
        # "ESGr0!" -> "ESGr037DA!". This is the live drive rate, so a non-zero
        # value means the axis is still being driven right now.
        self._check_axis(axis)
        prefix = f"ESGr{axis}"
        response = self.command(f"ESGr{axis}!", prefix)

        return int(response[len(prefix) : -1], 16)

    def set_axis_rate(self, axis: int, rate: int) -> None:
        """
        Set an axis's standing drive rate ("ESSr"), in counts per second.

        This is the rate the axis runs at when it is not slewing, and ESPt
        ramps back down to it rather than to a stop. RA powers up with it at
        the sidereal rate, which is why RA keeps moving after a slew; DEC
        powers up at zero. The value persists across subsequent slews.

        Not the same scaling as set_tracking_rate(): this one is unscaled
        counts per second, so sidereal is SIDEREAL_DRIVE_RATE (48), not
        SIDEREAL_RATE (1200). Applied immediately, with no ramp.
        """
        self._check_axis(axis)

        if not 0 <= rate <= RATE_MAX:
            raise ValueError(f"Rate must be in [0, {RATE_MAX}]")

        expected = f"ESGr{axis}{rate:04X}!"
        response = self.command(f"ESSr{axis}{rate:04X}!", f"ESGr{axis}")

        if response != expected:
            raise MountError(
                f"Unexpected rate response: expected {expected!r}, "
                f"received {response!r}"
            )

    def point_to(self, axis: int, counts: int) -> None:
        """
        Slew an axis to an absolute position ("ESPt").

        The controller ramps the rate up and back down on its own, and returns
        the target immediately -- it does not wait for the slew to finish.

        Note that the reference defines this as slewing "from the current
        target to a new target". If the controller's stored target does not
        match where the mount actually is (it does not after a power cycle),
        the ramp is planned from that stale target. Callers should sync with
        sync_target_to_position() first.
        """
        self._check_axis(axis)
        target = self._encode_counts(counts)
        expected = f"ESGt{axis}{target}!"
        response = self.command(f"ESPt{axis}{target}!", f"ESGt{axis}")

        if response != expected:
            raise MountError(
                f"Unexpected point response: expected {expected!r}, "
                f"received {response!r}"
            )

    def sync_target_to_position(self, axis: int) -> int:
        """
        Point the controller's stored target at where the axis actually is.

        This uses ESPt to slew a distance of zero. The obvious command is
        ESSt ("set axis target"), but despite being documented on p. 29 of the
        reference it has no opcode in the firmware's own command table -- the
        list jumps 0x12 (ESSr) straight to 0x14 (ESSd). Firmware 20A01 ignores
        it silently, returning nothing at all.
        """
        position = self.axis_position_counts(axis)
        self.point_to(axis, position)

        return position

    def halt(self, axis: int) -> int:
        """
        Bring an axis to a controlled stop and return where it stopped.

        The ES command set has no halt command; retargeting a moving axis to
        its current position is the documented way to ramp it down. For a hard
        stop use set_axis_rate(axis, 0), at the cost of possibly losing counts.
        """
        return self.sync_target_to_position(axis)

    def stop_axis_drive(self, axis: int) -> int:
        """
        Zero an axis's drive rate, returning the rate it had been running at.

        This is what actually stops RA tracking on firmware 20A01. Setting the
        ESTr tracking rate to zero does not: ESGx reads back 0x0000 while the
        axis carries on at 48 counts/sec. Measured behaviour after zeroing RA:
        drift stops dead, ESPt slews still work normally, and the axis now
        stays put at the end of a slew instead of resuming sidereal.
        """
        rate = self.axis_rate(axis)

        if rate != 0:
            self.set_axis_rate(axis, 0)

        return rate

    def halt_all(self) -> None:
        """Ramp both axes down to a stop at their current positions."""
        errors = []

        for axis in (RA_AXIS, DEC_AXIS):
            try:
                self.halt(axis)
            except (MountError, TimeoutError) as error:
                errors.append(error)

        if errors:
            raise errors[0]

    def tracking_rate(self) -> int:
        # "ESGx!" -> "ESGx0535!". RA only; there is no axis argument.
        return int(self.command("ESGx!", "ESGx")[4:-1], 16)

    def set_tracking_rate(self, rate: int) -> None:
        # "ESTr0535!" -> "ESGx0535!". Note the response prefix is ESGx, not
        # ESGr -- ESTr is the one command whose reply letter differs.
        if not 0 <= rate <= RATE_MAX:
            raise ValueError(f"Tracking rate must be in [0, {RATE_MAX}]")

        expected = f"ESGx{rate:04X}!"
        response = self.command(f"ESTr{rate:04X}!", "ESGx")

        if response != expected:
            raise MountError(
                f"Unexpected tracking response: expected {expected!r}, "
                f"received {response!r}"
            )

    def disable_ra_tracking(self) -> None:
        """
        Stop the RA axis moving.

        Both registers are written because ESTr alone does not do it: on
        firmware 20A01 the axis keeps running at 48 counts/sec with ESGx
        reading 0x0000. Zeroing the standing drive rate is what stops it.
        """
        self.set_tracking_rate(TRACKING_OFF)
        self.set_axis_rate(RA_AXIS, 0)

    def enable_ra_tracking(self, rate: int = SIDEREAL_RATE) -> None:
        """
        Track in RA, by default at the sidereal rate.

        Sets the precision tracking rate and the standing drive rate together;
        see disable_ra_tracking() for why both are needed.
        """
        self.set_tracking_rate(rate)
        self.set_axis_rate(RA_AXIS, round(rate / RATE_SCALE))

    def _wait_for_axis_position(
        self,
        axis: int,
        target_counts: int,
        *,
        timeout: float,
        tolerance_counts: int = DEFAULT_TOLERANCE_COUNTS,
        poll_interval: float = 0.1,
        stall_polls: int = 20,
        diverge_polls: int = 30,
        progress_interval: float = 5.0,
    ) -> int:
        """
        Poll until the axis arrives, stalls, drifts away, or the timeout runs out.

        A bare timeout cannot distinguish "still slewing", "stopped short" and
        "moving the wrong way" -- three problems with three different fixes --
        so each is detected and reported separately.
        """
        started = time.monotonic()
        deadline = started + timeout
        samples = []
        previous = None
        unchanged = 0
        worsening = 0
        closest = None
        next_report = started + progress_interval

        while time.monotonic() < deadline:
            current = self.axis_position_counts(axis)
            error = current - target_counts
            samples.append((time.monotonic(), current))

            # A slew can run for a minute with nothing to show for it, which
            # is indistinguishable from a hang. Say something periodically.
            if time.monotonic() >= next_report:
                next_report = time.monotonic() + progress_interval
                print(
                    f"    axis {axis} at {current}, {abs(error)} counts to go "
                    f"({time.monotonic() - started:.0f}s elapsed)"
                )

            if abs(error) <= tolerance_counts:
                return current

            if closest is None or abs(error) < closest:
                closest = abs(error)
                worsening = 0
            else:
                worsening += 1

                if worsening >= diverge_polls:
                    raise MountError(
                        f"Axis {axis} is moving away from {target_counts} rather "
                        f"than toward it: now {current} ({error:+d} counts off), "
                        f"{self._describe_drift(samples)}"
                    )

            if current == previous:
                unchanged += 1

                if unchanged >= stall_polls:
                    raise MountError(
                        f"Axis {axis} stopped {error:+d} counts "
                        f"({error * ARCSEC_PER_COUNT:+.1f} arcsec) short of "
                        f"{target_counts}. The move is likely smaller than the "
                        f"servo deadband and backlash."
                    )
            else:
                unchanged = 0
                previous = current

            time.sleep(poll_interval)

        current = self.axis_position_counts(axis)
        samples.append((time.monotonic(), current))

        raise TimeoutError(
            f"Axis {axis} did not reach {target_counts} within {timeout}s; "
            f"current position is {current} "
            f"({current - target_counts:+d} counts away), "
            f"{self._describe_drift(samples)}"
        )

    @staticmethod
    def _describe_drift(samples: list, window: float = 3.0) -> str:
        """
        Describe an axis's recent speed, naming sidereal when it matches.

        Deliberately the last few seconds rather than the whole wait: a slew
        that ramps to 20,000 counts/sec and then creeps averages out to a
        number that describes neither phase.
        """
        if len(samples) < 2:
            return "no motion measured"

        cutoff = samples[-1][0] - window
        recent = [s for s in samples if s[0] >= cutoff] or samples[-2:]
        (t0, p0), (t1, p1) = recent[0], recent[-1]
        elapsed = max(t1 - t0, 1e-6)
        drift = (p1 - p0) / elapsed
        described = f"drifting {drift:+.1f} counts/sec over the last {elapsed:.1f}s"

        # Within 10%, rather than an absolute window: over a short sampling
        # period the estimate is coarse, and no other drive rate is close.
        if abs(abs(drift) - SIDEREAL_COUNTS_PER_SEC) <= 0.1 * SIDEREAL_COUNTS_PER_SEC:
            described += (
                f" -- that is the sidereal rate ({SIDEREAL_COUNTS_PER_SEC:.0f} "
                f"counts/sec), so the axis is still being driven; "
                f"call stop_axis_drive() after the slew"
            )

        return described

    def move_axis_by(
        self,
        axis: int,
        delta_counts: int,
        *,
        timeout: float = 120.0,
        tolerance_counts: int = DEFAULT_TOLERANCE_COUNTS,
    ) -> int:
        """
        Slew an axis by a relative number of counts and wait for arrival.

        The offset is measured from wherever the axis happens to be when the
        command is issued. On an axis that is still being driven, that
        reference point is already moving, so use move_axis_to() when you need
        to get back to a position recorded earlier.
        """
        self._check_axis(axis)

        if delta_counts == 0:
            raise ValueError("delta_counts must not be zero")

        start = self.axis_position_counts(axis)

        return self.move_axis_to(
            axis,
            start + delta_counts,
            timeout=timeout,
            tolerance_counts=tolerance_counts,
        )

    def move_axis_to(
        self,
        axis: int,
        target_counts: int,
        *,
        timeout: float = 120.0,
        tolerance_counts: int = DEFAULT_TOLERANCE_COUNTS,
        corrections: int = 3,
    ) -> int:
        """
        Slew an axis to an absolute position and wait for it to arrive.

        A long slew ramps to ~20,000 counts/sec and does not stop on a pin:
        100,000 counts overshoots by a couple of hundred. RA then resumes
        sidereal and keeps sliding. Both are corrected by simply pointing
        again -- each pass re-zeroes the rate and covers a shorter distance,
        so it converges -- rather than treating the overshoot as a failure.
        """
        self._check_axis(axis)

        last_error = None

        for attempt in range(corrections + 1):
            # Zero the drive rate first, unconditionally. A non-zero rate
            # fights the point command: at ESSr0=480 the axis sails past the
            # target and never arrives, and against the slew direction it
            # drags a 4-second move out to 50. This cannot be skipped by
            # checking first, because ESGr reports the *live* rate, which
            # reads 0 whenever the axis is idle no matter what the commanded
            # rate is. Writing 0 takes RA from ~95 counts/sec to ~1300.
            self.set_axis_rate(axis, 0)

            # Deliberately a single ESPt. An earlier version synced the target
            # to the current position first, on the theory that ESPt plans its
            # ramp from a stale target; that turned out to be wrong and
            # actively harmful. Two ESPt commands back to back leave RA stuck
            # one count from where it started, because the second lands while
            # the first is still ramping. DEC tolerates it, which is what made
            # this look like an RA-specific fault.
            self.point_to(axis, target_counts)

            try:
                arrived = self._wait_for_axis_position(
                    axis,
                    target_counts,
                    timeout=timeout,
                    tolerance_counts=tolerance_counts,
                )
            except (MountError, TimeoutError) as error:
                last_error = error

                if attempt == corrections:
                    raise

                position = self.axis_position_counts(axis)
                print(
                    f"    axis {axis} missed by "
                    f"{position - target_counts:+d} counts; correcting "
                    f"({attempt + 1}/{corrections})"
                )
                continue

            # Stop the axis sliding on past what we just lined it up with.
            self.set_axis_rate(axis, 0)

            return arrived

        raise last_error

    def test_axis_motion(
        self,
        axis: int = DEC_AXIS,
        delta_counts: int = 5_000,
        *,
        timeout: float = 120.0,
        tolerance_counts: int = DEFAULT_TOLERANCE_COUNTS,
    ) -> None:
        """
        Move one axis by a relative number of motor counts and return.

        Axis 0 is RA and axis 1 is DEC. DEC is the easier axis to test, because
        RA is handed back to the tracking drive at the end of every slew and
        has to be stopped again before the return leg has a fixed reference.

        The default of 5,000 counts is about 26 arcmin -- small, but large
        enough to clear backlash. Sub-arcsecond moves will not register.
        """
        self._check_axis(axis)

        origin = self.axis_position_counts(axis)
        arcmin = abs(delta_counts) * ARCSEC_PER_COUNT / 60

        print(
            f"Axis {axis}: {origin} -> {origin + delta_counts} -> {origin} "
            f"({arcmin:.1f} arcmin each way)"
        )

        # move_axis_to() zeroes the drive rate before each leg, which stops RA
        # tracking. Remember the tracking rate -- ESGx, unlike ESGr, is
        # readable while the axis is idle -- so it can be put back afterwards.
        entry_tracking = self.tracking_rate() if axis == RA_AXIS else TRACKING_OFF

        try:
            # Both legs are absolute, against the position recorded up front.
            # A relative -delta would measure from wherever the axis had
            # drifted to by then, which is not where the test started.
            for target in (origin + delta_counts, origin):
                self.move_axis_to(
                    axis,
                    target,
                    timeout=timeout,
                    tolerance_counts=tolerance_counts,
                )

        except (MountError, TimeoutError):
            # Do not leave the axis slewing toward a target nobody is watching.
            self.halt(axis)
            raise
        finally:
            if entry_tracking != TRACKING_OFF:
                self.enable_ra_tracking(entry_tracking)
                print(f"  RA tracking restored to 0x{entry_tracking:04X}")


if __name__ == "__main__":
    """
    `ls /dev/cu.usb*` to find the correct serial port for your PMC-Eight mount.
    """
    with PMCEight("/dev/cu.usbserial-AK06KWLC") as mount:
        print("Firmware:", mount.firmware_version())
        print("RA counts:", mount.axis_position_counts(RA_AXIS))
        print("DEC counts:", mount.axis_position_counts(DEC_AXIS))

        # Remember both rate registers so they can be put back afterwards.
        initial_tracking_rate = mount.tracking_rate()
        initial_ra_drive = mount.axis_rate(RA_AXIS)
        print(f"Tracking rate: 0x{initial_tracking_rate:04X}, "
              f"RA standing drive: 0x{initial_ra_drive:04X}")

        try:
            mount.test_axis_motion(axis=DEC_AXIS, delta_counts=100_000)
            print("DEC axis motion test passed")

            mount.test_axis_motion(axis=RA_AXIS, delta_counts=100_000)
            print("RA axis motion test passed")
        finally:
            mount.set_tracking_rate(initial_tracking_rate)
            mount.set_axis_rate(RA_AXIS, initial_ra_drive)
            print(f"Rates restored to 0x{initial_tracking_rate:04X} / "
                  f"0x{initial_ra_drive:04X}")
