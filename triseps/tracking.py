"""Align equally spaced exposures using a Seimei ``_tk.dat`` ephemeris."""

import csv

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable
from astropy.time import Time, TimeDelta
from astropy.wcs.utils import skycoord_to_pixel

from .astrometry import wcs_without_naxis3


def read_track(filename):
    """Read UTC JD and ICRS astrometric RA/Dec from a Seimei track file.

    The first line is the target/range description. Subsequent CSV rows
    contain calendar date, JD, Sun, Moon, RA (hour angle), Dec, Az, El.
    """
    jd, ra, dec = [], [], []
    with open(filename, encoding='utf-8') as stream:
        next(stream, None)
        for line, row in enumerate(csv.reader(stream), start=2):
            if not row or not any(field.strip() for field in row):
                continue
            try:
                jd.append(float(row[1]))
                ra.append(row[4].strip())
                dec.append(row[5].strip())
            except (IndexError, ValueError) as exc:
                raise ValueError(f'invalid tracking row {line}') from exc
    if len(jd) < 2:
        raise ValueError('tracking file must contain at least two positions')
    if not np.all(np.isfinite(jd)) or np.any(np.diff(jd) <= 0):
        raise ValueError(
            'tracking times must be finite and strictly increasing'
        )
    positions = SkyCoord(ra, dec, unit=(u.hourangle, u.deg), frame='icrs')
    if not np.all(np.isfinite(positions.cartesian.xyz.value)):
        raise ValueError('tracking coordinates must be finite')
    return Time(jd, format='jd', scale='utc'), positions


def frame_times(header, count):
    """Return exposure midpoints; GEXP-STR is the first exposure start."""
    if count < 1:
        raise ValueError('image cube must contain at least one frame')
    interval = float(header['TFRAME'])
    exposure = float(header['EXPTIME1'])
    if not np.isfinite(interval) or interval <= 0:
        raise ValueError('TFRAME must be finite and positive')
    if not np.isfinite(exposure) or exposure <= 0:
        raise ValueError('EXPTIME1 must be finite and positive')
    scale = header.get('TIMESYS', 'UTC').lower()
    start = Time(header['GEXP-STR'], scale=scale)
    seconds = np.arange(count) * interval + exposure / 2
    return start + TimeDelta(seconds, format='sec')


def interpolate_track(times, positions, requested):
    """Interpolate unit vectors, avoiding the RA wrap discontinuity."""
    samples = (times - times[0]).to_value(u.s)
    query = (requested - times[0]).to_value(u.s)
    if np.any(query < samples[0]) or np.any(query > samples[-1]):
        raise ValueError('exposure midpoints fall outside the tracking file')
    xyz = np.array([
        np.interp(query, samples, axis)
        for axis in positions.cartesian.xyz.value
    ])
    norm = np.linalg.norm(xyz, axis=0)
    if np.any(norm < 1e-12):
        raise ValueError('cannot interpolate antipodal tracking coordinates')
    xyz /= norm
    return SkyCoord(
        x=xyz[0],
        y=xyz[1],
        z=xyz[2],
        representation_type='cartesian',
        frame=positions.frame.replicate_without_data(),
    )


def tracking_offsets(header, count, filename, reverse=False):
    """Return applied (x, y) pixel translations relative to frame zero."""
    times, positions = read_track(filename)
    midpoints = frame_times(header, count)
    targets = interpolate_track(times, positions, midpoints)
    wcs = wcs_without_naxis3(header)
    if not wcs.has_celestial:
        raise ValueError('tracking requires a celestial WCS')
    x, y = skycoord_to_pixel(targets, wcs, origin=0, mode='all')
    pixels = np.column_stack((x, y))
    if not np.all(np.isfinite(pixels)):
        raise ValueError('tracking positions cannot be projected onto the WCS')
    offsets = pixels - pixels[0]
    if not reverse:
        offsets *= -1
    # Suppress projection roundoff at exact integer translations.
    rounded = np.round(offsets)
    offsets = np.where(np.abs(offsets - rounded) < 1e-8, rounded, offsets)
    return midpoints, offsets


def shift_bilinear(data, dx, dy):
    """Translate a 2D image without wrapping, retaining its original size.

    A destination pixel is NaN if any contributor with nonzero weight is
    outside the image or nonfinite. Zero-weight neighbours do not invalidate
    pixels, so a zero/integer shift preserves valid boundary pixels.
    """
    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or not np.all(np.isfinite([dx, dy])):
        raise ValueError(
            'bilinear shift requires a 2D image and finite offsets'
        )
    height, width = data.shape
    if abs(dx) >= width or abs(dy) >= height:
        return np.full(data.shape, np.nan)
    x = np.arange(width, dtype=float) - dx
    y = np.arange(height, dtype=float) - dy
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    result = np.zeros(data.shape, dtype=float)
    valid = np.ones(data.shape, dtype=bool)
    for ox, wx in ((0, 1 - fx), (1, fx)):
        for oy, wy in ((0, 1 - fy), (1, fy)):
            ix, iy = x0 + ox, y0 + oy
            weight = wy[:, None] * wx[None, :]
            inside = ((iy >= 0) & (iy < height))[:, None] & (
                (ix >= 0) & (ix < width)
            )[None, :]
            values = data[
                np.clip(iy, 0, height - 1)[:, None],
                np.clip(ix, 0, width - 1)[None, :],
            ]
            good = inside & np.isfinite(values)
            valid &= good | (weight == 0)
            result += np.where(good, values, 0) * weight
    result[~valid] = np.nan
    return result


def align_cube(hdu, filename, reverse=False):
    """Shift a floating-point cube in place and return a provenance table.

    Spatial WCS describes the first frame. For target alignment it is only
    a reference-time sky mapping, not the sky mapping of every shifted frame.
    """
    if hdu.data.ndim != 3:
        raise ValueError('tracking requires a 3D FITS image cube')
    times, offsets = tracking_offsets(
        hdu.header,
        len(hdu.data),
        filename,
        reverse=reverse,
    )
    if not np.issubdtype(hdu.data.dtype, np.floating):
        hdu.data = hdu.data.astype(float)
    for i, (dx, dy) in enumerate(offsets):
        hdu.data[i] = shift_bilinear(hdu.data[i], dx, dy)
    hdu.header['TRKALIGN'] = 'SIDEREAL' if reverse else 'TARGET'
    hdu.header['TRKINTER'] = 'BILINEAR'
    hdu.header['TRKREF'] = (0, 'Zero-based reference frame')
    hdu.header['TRKMJD'] = (times[0].utc.mjd, 'Reference midpoint, UTC MJD')
    hdu.header.add_history(f'tracking ephemeris: {filename}')
    hdu.header.add_history(
        'Spatial WCS refers to the first exposure midpoint.'
    )
    return QTable({
        'frame': np.arange(len(times)),
        'mjd_utc': times.utc.mjd * u.d,
        'dx': offsets[:, 0] * u.pix,
        'dy': offsets[:, 1] * u.pix,
    })
