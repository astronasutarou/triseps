# triwcs &ndash; solve a field using astrometry.net

Solve the spatial world coordinate system (WCS) of a TriCCS FITS image using
the external astrometry.net `solve-field` executable, and write a FITS file
with updated astrometric metadata.

## Usage

``` text
triwcs [-f] [-v] INPUT OUTPUT
```

### Arguments

| Argument | Description |
| --- | --- |
| `INPUT` | FITS file with a 2D image or 3D image cube in its Primary HDU. |
| `OUTPUT` | Destination FITS file. |

### Options

| Option | Description |
| --- | --- |
| `-f`, `--overwrite` | Replace an existing output file. |
| `-v`, `--verbose` | Show output from both astrometry.net calls and print the output HDU summary. Solver output is suppressed by default. |
| `-h`, `--help` | Show help and exit. |

## Requirements

The `solve-field` executable must be available on `PATH`, with suitable
astrometry.net index files installed and configured. These external resources
are not installed by the `triseps` Python package.

The input must have an approximate celestial WCS and a `CD1_1` header value
for estimating the image scale. A WCS encoded only with `PC` and `CDELT`,
without `CD1_1`, does not satisfy the current scale estimator. `FRAMEID` is
used to name intermediate files. Image dimensions come from the Primary HDU.

The current directory must be writable: the solver runs in a temporary
`wcs.*` directory beneath it, which is normally removed after processing.

Use an image that has already undergone basic calibration. `triwcs` itself
does not crop reference pixels, subtract a dark image, or apply a flat image.
These operations are provided by [trired](trired.md).

## Processing

1. Remove the time-axis WCS terms from a header copy and estimate the pointing
   from the spatial WCS at the image center.
2. Select the 2D input image, or only the **first frame** of a 3D cube.
3. Estimate lower and upper image-width bounds in arcminutes from `CD1_1`
   and the image dimensions.
4. Run `solve-field` with the estimated position, a search radius of one
   degree, positive parity, up to 400 objects, and depth values
   `20,40,80,160,320,640`. The first pass disables tweaking.
5. Run `solve-field` again to verify/refine the initial solution, using a
   pixel-error setting of `0.2`.
6. Copy the solved spatial WCS and supported SIP coefficients into the
   original Primary HDU header, and append solver history and comments.

Search radius, parity, scale bounds, and solver settings are not exposed as
command-line options. A failed solver invocation aborts the command.

## Output

The Primary HDU's pixel data and dimensionality are retained. Existing
extension HDUs are also preserved. A cube receives one spatial WCS based on
its first frame; the remaining frames are not solved independently or shifted.

The updated header includes the spatial projection, reference coordinates,
reference pixels, and CD matrix. For a SIP solution, the implementation copies
its supported coefficient set through second order, including inverse terms;
it does not copy arbitrary higher-order distortion terms.

`WCSVALID` is set to `True`. The implementation also sets `WCSORIG` to
`Gaia EDR3` unconditionally: this is not a check of which catalog was used to
build the installed astrometry.net indexes. Solver `HISTORY` entries are
appended with a `[wcs]` prefix.

## Examples

Solve an already reduced image:

``` console
$ triwcs reduced.fits reduced_wcs.fits
```

Regenerate an output and show the solver messages:

``` console
$ triwcs --overwrite --verbose reduced.fits reduced_wcs.fits
```

To perform basic reduction and solve the WCS in one command, use:

``` console
$ trired database.fits science.fits reduced_wcs.fits --wcs
```

With `trired`, WCS solving takes place after cropping and calibration, but
before ephemeris alignment or stacking.
