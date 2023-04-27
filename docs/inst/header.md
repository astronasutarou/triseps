# FITS Header

## Fundamental Section

SIMPLE
: True if the FITS file follows the FITS standard (should be `T`).

BITPIX
: Bit depth per pixel (should be `16`).

NAXIS
: The number of axes (`2` or `3` for TriCCS).

NAXIS1
: The image length along with NAXIS1.

NAXIS2
: The image length along with NAXIS2.

NAXIS3
: The number of frames.

EXTEND
: False if the file has no extension HDU (should e `F`).

BZERO
: The offset level of the data.

BSCALE
: The scale factor of the data.


## Observation Section
### Time

DATE-OBS
: Observation start date in `yyyy-mm-dd`.

JST-STR
: Exposure Start Time in Japan Standard Time in `HH:MM:SS.ss`.

JST-END
: Exposure End Time in Japan Standard Time in `HH:MM:SS.ss`.

UT-STR
: Exposure Start Time in Coordinated Universal Time in `HH:MM:SS.ss`.

UT-END
: Exposure End Time in Coordinated Universal Time in `HH:MM:SS.ss`.

LST-STR
: Exposure Start Time in Local Sidereal Time in `HH:MM:SS.ss`.

LST-END
: Exposure End Time in Local Sidereal Time in `HH:MM:SS.ss`.

MJD-STR
: Exposure Start Time in Modified Julian Day.

MJD-END
: Exposure End Time in Modified Julian Day.

TIMESYS
: Time system used in the header (basically `UTC`).


### Target/Telescope

DATA-TYP
: Type of the observation (`OBJECT`, `DARK`, `FLAT`).

RA
: Right Ascension of the telescope pointing in `HH:MM:SS.ss`.

DEC
: Declination of the telescope pointing in `[+-]DD:MM:SS.s`.

PA
: Position angle in degree.

OBJECT
: Name of the object.

OBJ-RA
: Right Ascension of the target in `HH:MM:SS.ss`.

OBJ-DEC
: Declination of the target in `[+-]DD:MM:SS.ss`.

RADESYS
: Coordinate system used in the header (basically `FK5`).

EQUINOX
: Equinox used in the header|basically `2000.0` (FK5)|

HA-STR
: Hour angle at exposure start in `[+-]HH:MM:SS.s`.

HA-END
: Hour angle at exposure end in `[+-]HH:MM:SS.s`.

ZD-STR
: Zenith distance angle at exposure start in degree.

ZD-END
: Zenith distance angle at exposure end in degree.

SECZ-STR
: $\sec{z}$ at exposure start, where $z$ is the zenith distance.

SECZ-END
: $\sec{z}$ at exposure end, where $z$ is the zenith distance.

AZ-STR
: Azimurthal angle at exposure start in degree.

AZ-END
: Azimurthal angle at exposure end in degree.

FOC-VAL
: Encoder value of the focal plane unit.

M3-STR
: M3 position angle at exposure start in degree.

M3-END
: M3 position angle at exposure end in degree.



### Dome

DOM-PSTR
: Dome position angle at exposure start.

DOM-PEND
: Dome position angle at exposure end.

DOM-SSTR
: Dome slit status at exposure start (e.g., `Opened`, `Closed`).

DOM-SEND
: Dome slit status at exposure end (e.g., `Opened`, `Closed`).



### Calibration Lamp

LAMP-HG
: Status of the Hg lamp (`0`=OFF, `1`=ON).

LAMP-NE
: Status of the Ne lamp (`0`=OFF, `1`=ON).

LAMP-XE
: Status of the Xe lamp (`0`=OFF, `1`=ON).

LAMP-FLT
: Status of the flat lamp (`0`=OFF, `1`=ON).



## Weather Section

WEA-STR
: Time stamp of the weather info at exposure start in `YYYY-MM-DDTHH:MM`.

WEA-END
: Time stamp of the weather info at exposure end in `YYYY-MM-DDTHH:MM`.

DOM-TSTR
: Dome temperature at exposure start in C&deg;.

DOM-TEND
: Dome temperature at exposure end in C&deg;.

DOM-HSTR
: Dome humidity at exposure start in percent.

DOM-HEND
: Dome humidity at exposure end in percent.

DOM-WSTR
: Wet sensor status at exposure start (e.g., `Fine`).

DOM-WEND
: Wet sensor status at exposure end (e.g., `Fine`).

OUT-TSTR
: Outside temperature at exposure start in C&deg;.

OUT-TEND
: Outside temperature at exposure end in C&deg;.

OUT-HSTR
: Outside humidity at exposure start in percent.

OUT-HEND
: Outside humidity at exposure end in percent.

OUT-PSTR
: Outside atmospheric pressure at exposure start in hPa.

OUT-PEND
: Outside atmospheric pressure at exposure end in hPa.

OUT-WSTR
: Outside wind speed at exposure start in m/s.

OUT-WEND
: Outside wind speed at exposure end in m/s.

OUT-WDIS
: Outside wind direction at exposure start.

OUT-WDIE
: Outside wind direction at exposure end.



## Observatory Section

OBSERVAT
: Observatory name.

TELESCOP
: Telescope name.

INSTRUME
: Instrument name (e.g., `TriCCS`).

OBSERVER
: Observer names.

PROP-ID
: Proposal ID code.

DAT-PUB
: Public data flag (e.g., `Open`).

OBS-MOD
: Observation mode (e.g., `Imaging`, `Spectroscopy`).


## Data Section

EXPID
: Unique sequential ID for exposure.

DETID
: CMOS detector ID (`0`, `1`, or `2`).

CMOSID
: CMOS vendor serial ID (e.g., `FK???????`).

FRAMEID
: Unique frame ID in the format of `TRCS{DETID:1d}{EXPID:08d}`.

BUNIT
: Unit of the data (basically `ADU`).

GMT
: Timestamp for FITS file creation in UTC.

GEXP-STR
: GPS timestamp at exposure start.

EXPTIME
: Total exposure time in second.

TELAPSE
: Total elapsed time in second.

EXPTIME1
: Exposure time of a single frame in second.

TFRAME
: Time interval between frames in second.

DAT-FPS
: Data frame rate in Hz.

FILTDISP
: Filter or disperser name.



## Instrument Section

### TriCCS

GAINCNFG
: Sensor gain setting (e.g., `x1`, `x2`).

GAIN
: Inverse gain value in electron/ADU.

RDNOISE
: Typical readout noise in electron.

H_FLIP
: `1` if the image is horizontally flipped.

V_FLIP
: `1` if the image is vertically flipped.

EFP-MIN1
: Starting pixel of the photo-sensitive area (NAXIS1).

EFP-MIN2
: Starting pixel of the photo-sensitive area (NAXIS1).

EFP-RNG1
: Length of the photo-sensitive area along NAXIS1.

EFP-RNG2
: Length of the photo-sensitive area along NAXIS2.

POS-SHUT
: Status of the shutter (e.g., `open`, `close`)

POS-COL
: Status of the collimator (e.g., `image`).

POS-ARMA
: Status of the ARM-A (e.g., `PS1-g2`).

POS-ARMB
: Status of the ARM-B (e.g., `PS1-r2`).

POS-ARMC
: Status of the ARM-C (e.g., `PS1-i2`).

POS-SLPO
: Status of the slit position (e.g., `out`).

POS-SLFO
: Status of the slit focus (e.g., `home`).

POS-VIPO
: Status of the slit viewer position (e.g., `home`).

POS-VIFO
: Status of the slit viewer focus (e.g., `home`).


### GPS

GPSINFO1
: Status of the GPS receiver (should be `GPSInfoEmbedded`).

GPSINST1
: `1` if the GPS receiver is successfully installed.

GPSPOSV1
: `1` if the GPS receiver is successfully installed.

GPSPPSD1
: `1` if Pulse-per-second signals are successfully detected.

GPSTIME1
: Name of the GPS timer mode (should be `GPSTimerSynced`).

GPSTIME2
: `1` if the GPS time seems valid.

GPSLSVA1
: `1` if the GPS leap second flag seems valid.

GPSFIXM1
: Name of the GPS fix mode (?).

GPSUTCD1
: UTC date given by the GPS receiver in the `YYYYMMDD` format.

GPSUTCT1
: UTC time given by the GPS receiver in the `HHMMSS` format.

GPSWEEK
: GPS week (week number since 1980-01-06T00:00:00).

GPSSECO1
: GPS second (elapsed seconds within a GPS week).

GPSLEAP1
: GPS leap second counter.

GPSLATI1
: Latitude of the GPS receiver in degree.

GPSLONG1
: Longitude of the GPS receiver in degree.

GPSSATE1
: Current Sattelite Selector ID.


### Image Manipulation

DEBIAS
: `T` if the bias signal is automatically subtracted.

TRIMMING
: `T` if the photo-insensitive region is automatically trimmed out.


## WCS Section

CRVAL1
: Cellestial coordinate of the NAXIS1 reference pixel.

CRVAL2
: Cellestial coordinate of the NAXIS2 reference pixel.

CRVAL3
: Time offset of the NAXIS3 reference pixel.

CRPIX1
: Reference pixel along NAXIS1.

CRPIX2
: Reference pixel along NAXIS2.

CRPIX3
: Reference pixel along NAXIS3.

CTYPE1
: Pixel coordinate system descriptor (e.g., `RA---TAN`).

CTYPE2
: Pixel coordinate system descriptor (e.g., `DEC--TAN`).

CTYPE3
: Pixel coordinate sysmte descriptor (e.g., `TIME`).

CUNIT1
: Units of `CRVAL1` (e.g., `degree`).

CUNIT2
: Units of `CRVAL2` (e.g., `degree`).

CUNIT3
: Units of `CRVAL3` (e.g., `s`).

CDa_b
: Pixel coordinate transformation matrix.
  `CD1_1`, `CD1_2`, `CD2_1`, and `CD2_2` are used to rotate the
  field of view. They are given in the same unit as `CUNIT1` and `CUNIT2`.
  `CD1_3`, `CD2_3`, `CD3_1`, and `CD3_2` are kept zero, since there is
  no appropriate transformation. `CD3_3` should be the same as `TFRAME`.

LONPOLE
: Native longitude pole of the celestial coordinate
 (`180.0` for the gnomonic projection, `TAN`).

LATPOLE
: Native latitude pole of the celestial coordinate
  (`0.0` for the gnomonic projection, `TAN`).

WCSVALID
: `T` if the wcs information is successfully updated.
