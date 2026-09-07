"""Gaia DR3 reference stars and observation-epoch coordinates."""

import warnings

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.time import Time
from erfa import ErfaWarning


def fetch_gaia(center, radius, mag_limit=18.0, max_sources=1000):
    """Query bright sources with usable proper motions using astroquery.

    Radius is in degrees. The explicit ADQL TOP limit avoids astroquery's
    default cone-search row limit. No login or external index files are needed.
    """

    radius = float(radius)
    mag_limit = float(mag_limit)
    if not np.isfinite(radius) or not 0 < radius <= 5:
        raise ValueError('Gaia query radius must be in (0, 5] degrees')
    if not np.isfinite(mag_limit) or not 0 < mag_limit <= 21:
        raise ValueError('Gaia magnitude limit must be in (0, 21]')
    if not isinstance(max_sources, int) or max_sources < 1:
        raise ValueError('max_sources must be a positive integer')
    center = center.icrs
    ra, dec = float(center.ra.deg), float(center.dec.deg)
    if not np.all(np.isfinite([ra, dec])):
        raise ValueError('Gaia query center must be finite')
    query = f"""
        SELECT TOP {max_sources}
            source_id, ra, dec, ref_epoch, pmra, pmdec,
            phot_g_mean_mag, ruwe
        FROM gaiadr3.gaia_source
        WHERE 1 = CONTAINS(
            POINT('ICRS', ra, dec),
            CIRCLE('ICRS', {ra:.12f}, {dec:.12f}, {radius:.12f}))
          AND phot_g_mean_mag <= {mag_limit:.6f}
          AND pmra IS NOT NULL AND pmdec IS NOT NULL
          AND ruwe <= 1.4
        ORDER BY phot_g_mean_mag ASC
    """
    # Import lazily: basic reduction/tracking must not contact the archive.
    from astroquery.gaia import Gaia

    try:
        table = Gaia.launch_job_async(query, verbose=False).get_results()
    except Exception as exc:
        raise RuntimeError(f'Gaia DR3 query failed: {exc}') from exc
    table.meta['catalog'] = 'Gaia DR3'
    return table


def gaia_at_epoch(catalog, obstime, mag_limit=18.0):
    """Filter reference stars and propagate their ICRS proper motions.

    Missing proper motions are rejected, not replaced by zero. Gaia's
    ref_epoch is a Julian year in TCB; pmra already includes cos(dec).
    This angular-motion model omits parallax and perspective acceleration.
    Return the filtered table and coordinates in the same brightness order.
    """

    catalog = Table(catalog, copy=True)
    required = ('ra', 'dec', 'ref_epoch', 'pmra', 'pmdec', 'phot_g_mean_mag')
    missing = set(required) - set(catalog.colnames)
    if missing:
        raise ValueError(f'missing Gaia columns: {sorted(missing)}')
    values = {
        key: np.asarray(
            np.ma.filled(
                np.ma.asarray(catalog[key], dtype=float),
                np.nan,
            )
        )
        for key in required
    }
    good = np.ones(len(catalog), dtype=bool)
    for value in values.values():
        good &= np.isfinite(value)
    good &= (values['ra'] >= 0) & (values['ra'] < 360)
    good &= np.abs(values['dec']) <= 90
    good &= values['phot_g_mean_mag'] <= mag_limit
    if 'ruwe' in catalog.colnames:
        ruwe = np.ma.filled(np.ma.asarray(catalog['ruwe']), np.nan)
        good &= np.isfinite(ruwe) & (ruwe <= 1.4)
    catalog = catalog[good]
    catalog.sort('phot_g_mean_mag')
    if len(catalog) == 0:
        raise ValueError('no Gaia sources with usable proper motions')
    stars = SkyCoord(
        ra=np.asarray(catalog['ra']) * u.deg,
        dec=np.asarray(catalog['dec']) * u.deg,
        pm_ra_cosdec=np.asarray(catalog['pmra']) * u.mas / u.yr,
        pm_dec=np.asarray(catalog['pmdec']) * u.mas / u.yr,
        obstime=Time(
            np.asarray(catalog['ref_epoch']), format='jyear', scale='tcb'
        ),
        frame='icrs',
    )
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore',
            message='.*distance overridden.*',
            category=ErfaWarning,
        )
        moved = stars.apply_space_motion(new_obstime=obstime)
    # Return positions only; the WCS fit needs neither velocity nor distance.
    return catalog, SkyCoord(moved.ra, moved.dec, frame='icrs')
