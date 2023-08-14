# Database

## Overview

The database file contains information that summarizes the observations and used to generate the observation log and to compile the calibration frames. This page provides a brief overview of the database file.

The database file is compiled as a FITS file. The second HDU extension contains the database in the FITS binary table format.


## Columns
The database contains several columns collected from FITS headers. This section explains the columns in the database made by `tripre`.

- `EXPID`
- `DETID`
- `FRAMEID`

These columns are used to uniquely identify the frame.

- `OBSERVER`
- `PROPID`
- `OBJECT`
- `RA`
- `DEC`

These columns briefly annotate the frames.

- `DATA-TYP`

`DATA-TYP` is used to check if frames are obtained for science or calibration.

- `DATE-OBS`
- `GEXP-STR`
- `GPSINFO1`
- `GPSTIME1`
- `GPSLATI1`
- `GPSLONG1`

The first two columns are the most reliable timestamps. The following columns are used to check the reliability of the timestamps.

- `FILDISP`

`FILDISP` contains the name of the photometric filter or disperser. This column is indispensable to identify the observation mode.

- `EXPTIME`
- `EXPTIME1`

The two columns are adopted to describe the exposure times of the frames.

- `EFP-AREA`
- `EFP-MIN1`
- `EFP-MIN2`
- `EFP-RNG1`
- `EFP-RNG2`

`EFP-AREA` is the
The following four columns specify the photo-sensitive area of the frames. If these columns change, the CMOS sensor may be driven in different modes and has a different dark-current pattern.

- `DEBIAS`
- `TRIMMING`

These two columns are supposed to be false. In case that the frames were already reduced by extra processes, they can be true.

- `POS-SHUT`
- `LAMP-HG`
- `LAMP-NE`
- `LAMP-XE`
- `LAMP-FLT`

These columns are used to check the validity of the calibration frames.

- `WCSVALID`

`WCSVALID` is stored to check if the astrometric calibration is already completed. This column is supposed to be false but reserved for future updates.
