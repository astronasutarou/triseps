# triview &ndash; inspect the database file

Inspect a [tripre](tripre.md) calibration database from the terminal, or
extract one of its calibration images into a separate FITS file.

## Usage

``` text
triview {frame,calib,extract} ...
```

A subcommand is required. `triview --help` lists the subcommands, and
`triview SUBCOMMAND --help` shows the arguments for that subcommand.
This command prints tables; it does not display image pixels graphically.

## frame &ndash; list input observations

``` text
triview frame [-c {OBJECT,DARK,FLAT,ALL}] [-k KEY [KEY ...]] [-v] DATABASE
```

| Argument or option | Description |
| --- | --- |
| `DATABASE` | Calibration database FITS file. |
| `-c`, `--category` | Filter rows by `data_type`. Choices are `OBJECT`, `DARK`, `FLAT`, and `ALL`. Default: `OBJECT`. Values are case-sensitive. |
| `-k`, `--key` | One or more database column names used to group the display. Each distinct combination is printed separately, preceded by a group label. Without this option, print one table. |
| `-v`, `--verbose` | Select all database columns instead of the default subset. Astropy's terminal formatting may still abbreviate a large table. |
| `-h`, `--help` | Show subcommand help and exit. |

The default display includes:

``` text
frame_id, observer, timestamp, object, filter, ra, dec,
exptime, exptime_single, shutter, effective_area
```

Use database column names such as `object`, `filter`, and `det_id` for `--key`,
not the corresponding raw FITS header keywords. Category filtering is applied
before grouping. `ALL` disables category filtering.

Examples:

``` console
$ triview frame database.fits
$ triview frame database.fits --category DARK
$ triview frame database.fits --category ALL --verbose
$ triview frame database.fits --key object filter
```

## calib &ndash; list generated calibrations

``` text
triview calib DATABASE
```

| Argument or option | Description |
| --- | --- |
| `DATABASE` | Calibration database FITS file. |
| `-h`, `--help` | Show subcommand help and exit. |

Lists HDUs whose header has `CATEGORY=CALIBRATION`.

| Output column | Source and meaning |
| --- | --- |
| `type` | `OBJECT` header value, normally `DARK` or `FLAT`. |
| `n_frame` | `NFRAME`: the number of accepted input cubes used to construct the calibration image, not the number of individual exposures. |
| `key` | `EXTNAME`: the extension name to pass to `extract`. |

For an HDU marked as a calibration but missing these metadata, `type` and
`key` default to `ERROR`, and `n_frame` defaults to `-1`.

``` console
$ triview calib database.fits
```

## extract &ndash; write a calibration image

``` text
triview extract [-f] DATABASE KEY OUTPUT
```

| Argument or option | Description |
| --- | --- |
| `DATABASE` | Calibration database FITS file. |
| `KEY` | Extension name, as displayed by `triview calib`. |
| `OUTPUT` | Destination FITS file containing the selected HDU. |
| `-f`, `--overwrite` | Replace an existing output file. |
| `-h`, `--help` | Show subcommand help and exit. |

The selected HDU's data and header are written to a standalone FITS file.
For an image extension, Astropy supplies an empty Primary HDU before the
extracted Image Extension. Other database HDUs are not copied. The command
looks up the extension by name; it does not require its category to be
`CALIBRATION`.

First list the available keys, then select the one to extract. For example,
if the listing contains `DARK_0_00004992_076_2160X1280+60+0`:

``` console
$ triview extract database.fits DARK_0_00004992_076_2160X1280+60+0 dark.fits
```

The `calib` and `extract` subcommands do not accept `--verbose`, `--category`,
or `--key`; those options belong to `frame`.
