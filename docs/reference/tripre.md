# tripre &ndash; build a database file

Build a calibration database from TriCCS FITS files. The output combines
observation metadata and generated dark and flat images in one FITS file for
use with [trired](trired.md) and [triview](triview.md).

## Usage

``` text
tripre [-f] [-v] DATABASE FITS [FITS ...]
```

### Arguments

| Argument | Description |
| --- | --- |
| `DATABASE` | Destination calibration database FITS file. |
| `FITS` | One or more input FITS files. Only the Primary HDU of each file is read. Include the science files to be reduced, as well as their dark and flat observations. |

Inputs must contain the TriCCS metadata described in the
[FITS header reference](../inst/header.md). Calibration inputs must be
3D image cubes. Science images are registered by their headers; their pixel
data are not copied into the database.

### Options

| Option | Description |
| --- | --- |
| `-f`, `--overwrite` | Replace an existing output file. Otherwise, writing to an existing file fails. |
| `-v`, `--verbose` | Print the observation table and output HDU summary. Calibration progress messages and warnings can also appear without this option. |
| `-h`, `--help` | Show help and exit. |

## Processing

1. Collect observation information from each input header into a table.
2. Check the shutter status against `DATA-TYP`: dark observations should have
   `POS-SHUT=close`; flat and object observations should have `POS-SHUT=open`.
   Inconsistencies produce warnings, rather than removing table entries.
3. Group calibration observations by the conditions listed below.
4. Reject saturated calibration cubes. The current check uses the 95th
   percentile of the entire input cube and rejects values greater than
   `0.9 * 13000` ADU for `GAINCNFG=x1`, or `0.9 * 16383` ADU otherwise.
5. Take the median along the time axis of each accepted calibration cube,
   then extract its effective photo-sensitive area.
6. Combine these 2D images into dark and flat calibration images.

| Calibration | Grouping columns | Combination |
| --- | --- | --- |
| Dark | `det_id`, `exptime_single`, `gain`, `effective_area` | Arithmetic mean of the per-cube median images. |
| Flat | `det_id`, `filter`, `effective_area` | Sum of the per-cube median images, divided by the spatial median of that sum. |

Flat generation does not subtract a dark image. Reference pixels are cropped;
they are not used for bias estimation.

A group without dark or flat inputs is skipped with an informational message.
Database creation does not guarantee that every science observation has both
required calibrations. Check the output with `triview calib` before reduction.
Groups in which all calibration cubes are rejected are not handled as a usable
calibration product.

## Output

| HDU | Contents |
| --- | --- |
| Primary | Empty Primary HDU. |
| `DATABASE` | Binary table of input observation metadata, including science and calibration observations. |
| `DARK_*` | Generated 2D dark images. |
| `FLAT_*` | Generated normalized 2D flat images. |

Calibration extensions have `CATEGORY=CALIBRATION`, `OBJECT=DARK` or `FLAT`,
and `NFRAME` equal to the number of accepted input cubes used in that image.
`NFRAME` is not the total number of individual exposures in those cubes.
Their `HISTORY` records the contributing frame IDs.

Dark extension names encode detector, single-exposure time in rounded
milliseconds (eight digits), gain multiplied by 100 (three digits), and
photo-sensitive area. Flat names encode detector, filter, and area. Use
`triview calib` to obtain the actual extension keys.

## Examples

Build a database from a night's science and calibration files:

``` console
$ tripre database.fits TRCS*.fits
$ triview calib database.fits
```

Regenerate it and print the observation table and HDU summary:

``` console
$ tripre --overwrite --verbose database.fits TRCS*.fits
```

See the [preparation tutorial](../tutorial/preparation.md) for the workflow.
