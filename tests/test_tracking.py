import sys

import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import QTable
from astropy.time import Time
from astropy.wcs import WCS

from triseps.bin import trired
from triseps.tracking import (
    align_cube,
    frame_times,
    interpolate_track,
    read_track,
    shift_bilinear,
)


def make_header():
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crpix = [6, 6]
    wcs.wcs.crval = [120, 30]
    # Include rotation and unequal scales to catch axis/sign confusion.
    wcs.wcs.cd = [[-0.001, 0.0003], [0.0002, 0.001]]
    header = wcs.to_header()
    header['GEXP-STR'] = '2026-09-07T00:00:00'
    header['TIMESYS'] = 'UTC'
    header['TFRAME'] = 2.0
    header['EXPTIME1'] = 1.0
    return header


def make_track(path, header):
    times = frame_times(header, 3)
    # Sample at exposure midpoints with a margin, avoiding JD rounding
    # at the exact bounds of the file.
    seconds = np.array([-2, 0, 2, 4, 6])
    coords = WCS(header).pixel_to_world(5 + seconds / 2, 5 + seconds / 4)
    rows = ['target, start - end']
    for time, coord in zip(times[0] + seconds * u.s, coords):
        ra = coord.ra.to_string(unit=u.hourangle, sep=' ', precision=10)
        dec = coord.dec.to_string(unit=u.deg, sep=' ', precision=10)
        rows.append(f' date,{time.utc.jd:.12f},,,{ra},{dec},0,45,')
    path.write_text('\n'.join(rows))
    return path


def test_bilinear_flux_and_weights():
    data = np.zeros((9, 9))
    data[4, 4] = 100
    shifted = shift_bilinear(data, 0.25, -0.5)
    np.testing.assert_allclose(shifted[3:5, 4:6], [[37.5, 12.5]] * 2)
    assert np.nansum(shifted) == pytest.approx(100)
    assert np.isnan(shifted[:, 0]).all()
    assert np.isnan(shifted[-1]).all()


def test_zero_integer_and_large_shifts():
    data = np.arange(20.0).reshape(4, 5)
    data[2, 2] = np.nan
    np.testing.assert_equal(shift_bilinear(data, 0, 0), data)
    shifted = shift_bilinear(data, -1, 1)
    np.testing.assert_equal(shifted[1:, :-1], data[:-1, 1:])
    assert np.isnan(shifted[0]).all()
    assert np.isnan(shifted[:, -1]).all()
    assert np.isnan(shift_bilinear(data, 100, 0)).all()


def test_nan_contributors():
    data = np.ones((5, 5))
    data[2, 2] = np.nan
    shifted = shift_bilinear(data, 0.5, 0.5)
    assert np.isnan(shifted[2:4, 2:4]).all()
    assert shifted[1, 1] == 1


def test_midpoints_cross_midnight():
    header = make_header()
    header['GEXP-STR'] = '2026-09-07T23:59:59'
    result = frame_times(header, 2)
    assert result.utc.isot.tolist() == [
        '2026-09-07T23:59:59.500',
        '2026-09-08T00:00:01.500',
    ]


def test_ra_wrap_and_outside_range():
    times = Time([2460000, 2460001], format='jd', scale='utc')
    positions = SkyCoord([359.9, 0.1], [0, 0], unit='deg')
    midpoint = Time([2460000.5], format='jd', scale='utc')
    result = interpolate_track(times, positions, midpoint)
    assert result.separation(SkyCoord(0, 0, unit='deg')).deg[0] < 1e-10
    with pytest.raises(ValueError, match='outside'):
        interpolate_track(times, positions, times + 1 * u.d)


@pytest.mark.parametrize(
    'rows',
    [
        [' date,2460000,,,08 00 00,+30 00 00,0,45,'],
        [' date,2460000,,,08 00 00,+30 00 00,0,45,'] * 2,
        [' date,invalid'],
    ],
)
def test_invalid_track(tmp_path, rows):
    path = tmp_path / 'invalid.dat'
    path.write_text('target\n' + '\n'.join(rows))
    with pytest.raises(ValueError):
        read_track(path)


@pytest.mark.parametrize('reverse', [False, True])
def test_alignment_direction(tmp_path, reverse):
    header = make_header()
    track = make_track(tmp_path / 'target.dat', header)
    yy, xx = np.indices((15, 15))
    sign = -1 if reverse else 1
    cube = np.array([
        np.exp(-((xx - 6 - sign * i) ** 2 + (yy - 6 - sign * i / 2) ** 2) / 2)
        for i in range(3)
    ])
    hdu = fits.PrimaryHDU(cube.copy(), header)
    table = align_cube(hdu, track, reverse=reverse)
    np.testing.assert_array_equal(hdu.data[0], cube[0])
    expected = (-sign) * np.array([[0, 0], [1, 0.5], [2, 1]])
    np.testing.assert_allclose(table['dx'].value, expected[:, 0], atol=3e-5)
    np.testing.assert_allclose(table['dy'].value, expected[:, 1], atol=3e-5)
    for frame in hdu.data:
        assert np.unravel_index(np.nanargmax(frame), frame.shape) == (6, 6)
    assert hdu.header['TRKALIGN'] == ('SIDEREAL' if reverse else 'TARGET')


@pytest.mark.parametrize('stack', [False, True])
@pytest.mark.parametrize('reverse', [False, True])
def test_cli_output(tmp_path, monkeypatch, stack, reverse):
    header = make_header()
    header['FRAMEID'] = 'TEST'
    header['EFP-MIN1'] = 2
    header['EFP-MIN2'] = 2
    # Make the ephemeris in the trimmed coordinate system.
    trimmed = header.copy()
    trimmed['CRPIX1'] -= 1
    trimmed['CRPIX2'] -= 1
    track = make_track(tmp_path / 'target.dat', trimmed)
    source = tmp_path / 'source.fits'
    fits.PrimaryHDU(np.full((3, 12, 12), 10, dtype=np.uint16), header).writeto(
        source,
    )
    db = QTable({'frame_id': ['TEST'], 'effective_area': ['10x10+1+1']})
    database = tmp_path / 'db.fits'
    fits.HDUList([
        fits.PrimaryHDU(),
        fits.BinTableHDU(db, name='DATABASE'),
        fits.ImageHDU(np.ones((10, 10)), name='DARK'),
        fits.ImageHDU(np.full((10, 10), 2.0), name='FLAT'),
    ]).writeto(database)
    monkeypatch.setattr(trired, 'estimate_darkframe', lambda *args: 'DARK')
    monkeypatch.setattr(trired, 'estimate_flatframe', lambda *args: 'FLAT')
    output = tmp_path / 'output.fits'
    args = [
        'trired',
        str(database),
        str(source),
        str(output),
        '--track',
        str(track),
    ]
    if stack:
        args.append('--stack')
    if reverse:
        args.append('-r')
    monkeypatch.setattr(sys, 'argv', args)
    trired.main()
    with fits.open(output) as result:
        result.verify('exception')
        image = result[0].data
        assert image.shape == ((10, 10) if stack else (3, 10, 10))
        np.testing.assert_allclose(image[np.isfinite(image)], 4.5)
        if stack:
            assert np.isfinite(image).all()  # frame zero covers the edges
            assert 'NAXIS3' not in result[0].header
        assert result[0].header['CRPIX1'] == trimmed['CRPIX1']
        assert result['SHIFTS'].data.shape == (3,)


@pytest.mark.parametrize(
    'options',
    [
        ['-r'],
        ['--track', 'unused', '--ql'],
        ['--ql', '--stack'],
    ],
)
def test_invalid_cli_options(monkeypatch, options):
    monkeypatch.setattr(sys, 'argv', ['trired', 'db', 'src', 'out'] + options)
    with pytest.raises(SystemExit) as exc:
        trired.main()
    assert exc.value.code == 2


def test_time_axis_removed_from_wcs():
    from triseps.astrometry import drop_naxis3_keywords

    header = make_header()
    header['NAXIS'] = 3
    header['NAXIS3'] = 3
    header['WCSAXES'] = 3
    header['CTYPE3'] = 'TIME'
    header['CDELT3'] = 2
    header['PC3_3'] = 1
    header['PC1_3'] = 0
    drop_naxis3_keywords(header)
    assert WCS(header).pixel_n_dim == 2
    assert header['WCSAXES'] == 2
    assert 'NAXIS3' not in header


@pytest.mark.parametrize(
    'key,value',
    [
        ('TFRAME', 0),
        ('TFRAME', -1),
        ('TFRAME', float('nan')),
        ('EXPTIME1', 0),
    ],
)
def test_invalid_timing(key, value):
    header = dict(make_header())
    header[key] = value
    with pytest.raises(ValueError):
        frame_times(header, 2)


def test_missing_wcs_and_2d_input(tmp_path):
    header = make_header()
    track = make_track(tmp_path / 'track.dat', header)
    with pytest.raises(ValueError, match='3D'):
        align_cube(fits.PrimaryHDU(np.ones((5, 5)), header), track)
    del header['CTYPE1']
    del header['CTYPE2']
    with pytest.raises(ValueError, match='celestial WCS'):
        align_cube(fits.PrimaryHDU(np.ones((3, 5, 5)), header), track)
