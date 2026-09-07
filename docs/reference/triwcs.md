# triwcs &ndash; calibrate WCS with Gaia DR3

Calibrate a TriCCS image against Gaia DR3 stars using `astroquery`, `photutils`,
and Astropy. The approximate plate scale and orientation in the FITS header
are trusted; the solver estimates a pointing translation, matches stars, and
fits CRVAL and third-order SIP distortion with CD and central CRPIX fixed. No astrometry.net executable or index files are used.

## Usage

``` text
triwcs [-f] [-v] [--wcs-image {first,mean}] [--gaia-catalog FILE]
       [--gaia-mag-limit MAG] [--wcs-fwhm PIXELS] [--wcs-threshold SIGMA]
       [--wcs-match-radius PIXELS] [--wcs-max-rms PIXELS]
       [--wcs-sip-degree {0,2,3}] INPUT OUTPUT
```

### Arguments and options

| Argument or option | Description |
| --- | --- |
| `INPUT` | FITS file with a 2D image or 3D image cube in its Primary HDU. |
| `OUTPUT` | Destination FITS file. |
| `-f`, `--overwrite` | Replace an existing output file. |
| `-v`, `--verbose` | Print reference, detection, and inlier counts, fit RMS, and the output HDU summary. |
| `--wcs-image {first,mean}` | Detection image for a cube: its first frame (default) or a 3-sigma-clipped mean of the cube. Does not change the output pixel data or dimensionality. For a 2D input the image itself is used. |
| `--wcs-sip-degree {0,2,3}` | Forward SIP degree. Default: `3`. Use `2` for quadratic distortion, or `0` to fit CRVAL alone. CD and central CRPIX remain fixed in every mode. |
| `--gaia-catalog FILE` | Read a local Gaia table instead of querying the archive. ECSV and FITS tables are supported by Astropy. |
| `--gaia-mag-limit MAG` | Faint limit in Gaia G magnitude. Default: `18`. Online queries accept values greater than zero and at most `21`. |
| `--wcs-fwhm PIXELS` | Expected stellar FWHM for DAOStarFinder. Default: `3` pixels. |
| `--wcs-threshold SIGMA` | Detection threshold in units of the sigma-clipped background standard deviation. Default: `5`. |
| `--wcs-match-radius PIXELS` | Maximum pixel separation for matching after a candidate pointing translation. Default: `3` pixels. |
| `--wcs-max-rms PIXELS` | Maximum accepted radial RMS of the fitted stellar positions. Default: `1` pixel. |
| `-h`, `--help` | Show help and exit. |

## Requirements and observation time

The input must contain an approximate celestial WCS with a finite,
nonsingular spatial CD matrix or equivalent PC/CDELT representation. The
solver uses its scale and orientation, and constructs an initial ICRS TAN
projection centered on the telescope pointing. `RA` and `DEC` specify that
pointing when present; otherwise the image center from the original WCS is
used. String RA values are hour angles, numeric RA values are degrees, and
Dec is in degrees. ICRS, FK5, and FK4 pointing frames are supported through
`RADESYS`, with `EQUINOX` used for FK5/FK4 conversion.

The exposure start is read from `GEXP-STR`, then `MJD-STR`, then `DATE-OBS`
(with `UT-STR` appended if the date has no time). `TIMESYS` defaults to UTC.
The astrometric epoch is the midpoint of the detection image:

| Detection image | Midpoint relative to exposure start |
| --- | --- |
| First cube frame | `EXPTIME1 / 2`. |
| Mean of a cube | `((NAXIS3 - 1) * TFRAME + EXPTIME1) / 2`. Equally spaced exposures are assumed. |
| 2D image | Half of `TELAPSE`, if present; otherwise half the interval to `MJD-END` when `MJD-STR` is present; otherwise `EXPTIME / 2`. |

Use images that have undergone basic calibration. `triwcs` does not crop
reference pixels, subtract dark current, or flat-field images; those operations
are provided by [trired](trired.md). The default first-frame detection is
appropriate for non-sidereal observations, where stars move between frames.
Mean-image detection is suitable when stars remain aligned. It does not
perform image registration before averaging.

## Gaia DR3 reference catalog

An online query uses `astroquery.gaia.Gaia.launch_job_async` against
`gaiadr3.gaia_source`. The search radius covers the nominal image corners,
plus a six-arcminute margin for pointing error and stellar motion. At most
1000 sources are returned, ordered from bright to faint, with G magnitude
numerically at most the requested limit and `ruwe <= 1.4`. Sources without both
proper-motion components are excluded. A network connection to the Gaia
archive is required unless `--gaia-catalog` is supplied.

The required local-table columns are:

| Column | Meaning and units |
| --- | --- |
| `ra`, `dec` | ICRS coordinates in degrees at `ref_epoch`. |
| `ref_epoch` | Julian year in TCB; Gaia DR3 uses J2016.0. |
| `pmra` | Proper motion in RA including cos(Dec), in mas/year. |
| `pmdec` | Proper motion in Dec, in mas/year. |
| `phot_g_mean_mag` | Gaia G magnitude. |
| `ruwe` | Optional astrometric quality indicator. When present, require a finite value at most `1.4`. |
| `source_id` | Gaia source identifier; returned by the online query, but not required for fitting. |

Missing or nonfinite positions, epochs, proper motions, and magnitudes are
rejected. Local tables are also filtered by the G magnitude limit and sorted
by brightness. Missing proper motions are not treated as zero.

Astropy `SkyCoord.apply_space_motion` propagates positions from each source's
TCB reference epoch to the observation time, using `pm_ra_cosdec` and `pm_dec`.
This implementation uses angular proper motion only; it does not include
parallax, radial velocity, perspective acceleration, or atmospheric refraction.

## Detection, matching, and fitting

1. Estimate a global background median and standard deviation with sigma
   clipping. Mask nonfinite image pixels.
2. Detect stars with `photutils.detection.DAOStarFinder`, applying its default
   shape filters and excluding image-border detections. Retain up to 300
   positive-flux, finite detections ordered by brightness.
3. Project the epoch-corrected Gaia positions through the initial WCS.
4. Vote for pointing translations using offsets between up to 80 bright
   detections and 200 bright catalog stars. Score candidate translations
   using mutual nearest neighbours within `--wcs-match-radius`, then refine
   translations with median matched offsets.
5. Fit CRVAL and the forward SIP coefficients with SciPy least squares.
   Use a robust loss while removing outliers, then ordinary least squares
   on the inliers. Rematch using the fitted WCS and fit again.
6. Validate the result before replacing the header.

### Fitted and fixed parameters

The default model is TAN-SIP of degree 3:

| Parameters | Treatment |
| --- | --- |
| `CD1_1`, `CD1_2`, `CD2_1`, `CD2_2` | Fixed to the input spatial transformation (or its equivalent PC/CDELT matrix). |
| `CRPIX1`, `CRPIX2` | Fixed at `((NAXIS1 + 1) / 2, (NAXIS2 + 1) / 2)` in FITS one-based coordinates. In `trired`, these dimensions refer to the cropped image. |
| `CRVAL1`, `CRVAL2` | Fitted ICRS coordinates at the fixed image center. Telescope pointing is the initial estimate. |
| `A_2_0`, `A_1_1`, `A_0_2`, `A_3_0`, `A_2_1`, `A_1_2`, `A_0_3` | Fitted forward SIP terms for the first pixel axis. |
| Corresponding seven `B_*` coefficients | Fitted forward SIP terms for the second pixel axis. |
| Constant and linear SIP terms | Fixed to zero. |
| Inverse SIP (`AP_*`, `BP_*`) | Not fitted or copied; inverse transformations use numerical iteration. |

This gives 16 free parameters by default: two CRVAL values and 14 SIP
coefficients. Coefficients are fitted using normalized detector coordinates
for numerical stability, then stored in standard SIP pixel units. Existing
SIP/PV terms are replaced by the new model.

At least 12 matched inliers are required for degree 3, or six for degree 2
and degree 0. The degree is never reduced automatically when there are too few
stars. Matches must span at least 10% of each image dimension, must not be
nearly collinear, and must constrain the polynomial basis without rank
deficiency or severe ill-conditioning. The final radial RMS in detector pixels
must not exceed `--wcs-max-rms`. A grid spanning the image is checked for
folding and for convergence of the numerical inverse. Failure raises an error
without applying a partial WCS update or writing a new output file.

This is a pointed-field solver, not a blind sky search. Incorrect header
orientation/scale, severe trails, crowded fields, saturation, or too few
usable stars can prevent a solution. CD is not adjusted to compensate for an
incorrect plate scale. The detection background is global; strongly varying
backgrounds may require preprocessing.

## Output

Pixel data and dimensionality are retained, including a cube processed with
`--wcs-image mean`. Existing extension HDUs are preserved. Only the Primary
HDU's spatial WCS and calibration metadata are updated. For a cube, its time
axis is retained with a consistent CD-matrix representation. Astropy's
high-level WCS object supports SIP only in two dimensions. Read the spatial
WCS of an output cube using `WCS(header, naxis=2)` or
`triseps.astrometry.wcs_without_naxis3(header)`, rather than `WCS(header)`.
The FITS data remain three-dimensional and the time-axis header is retained.

| Header keyword | Meaning |
| --- | --- |
| `WCSVALID` | `True` after a successful, validated solution. |
| `WCSORIG` | `Gaia DR3`. |
| `WCSSIP` | Forward SIP degree (`3` by default); CD and CRPIX are fixed. |
| `WCSNSTAR` | Number of inliers in the final fit. |
| `WCSRMS` | Radial RMS residual in pixels. |
| `WCSMJD` | Observation epoch used for propagation, as UTC MJD. |
| `WCSIMAGE` | `FIRST` or `MEAN` for cube detection, or `IMAGE` for a 2D input. |

The output spatial coordinate system is ICRS. `HISTORY` records the catalog,
proper-motion propagation, fixed parameters, SIP degree, fit star count,
RMS, and omitted motion terms.
A cube receives one spatial WCS; individual frames are not solved or shifted.
Target-aligned 2D stacks and mean detection on target-aligned cubes are rejected;
use the first cube frame before target stacking.

## Examples

Solve a reduced image, querying Gaia online:

``` console
$ triwcs reduced.fits reduced_wcs.fits
```

Detect stars in the mean of a sidereally tracked cube, retaining the cube:

``` console
$ triwcs cube.fits cube_wcs.fits --wcs-image mean --verbose
```

Use a saved Gaia catalog and adjust the detection FWHM:

``` console
$ triwcs reduced.fits reduced_wcs.fits --gaia-catalog gaia.ecsv --wcs-fwhm 4
```

Perform basic reduction and WCS calibration together:

``` console
$ trired database.fits science.fits reduced_wcs.fits --wcs
```

All Gaia solver options above are also accepted by `trired`; they take effect
with `--wcs`. In `trired`, WCS calibration occurs after cropping and calibration,
and before tracking or output stacking.

## References

- [Gaia TAP+ interface in astroquery](https://astroquery.readthedocs.io/en/latest/gaia/gaia.html)
- [Gaia DR3 reference epoch and coordinate conventions](https://www.cosmos.esa.int/web/gaia/dr3)
- [Astropy space-motion propagation](https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html)
- [Photutils DAOStarFinder](https://photutils.readthedocs.io/en/stable/api/photutils.detection.DAOStarFinder.html)
- [Astropy SIP convention](https://docs.astropy.org/en/stable/api/astropy.wcs.Sip.html)
- [SciPy least-squares fitting](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
