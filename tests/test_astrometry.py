import sys
import types

import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table, MaskedColumn
from astropy.time import Time
from astropy.wcs import WCS, Sip

from triseps import astrometry, gaia
from triseps.bin import triwcs


def make_field(seed=42, cube=False, distorted=False):
    rng = np.random.default_rng(seed)
    truth = WCS(naxis=2)
    truth.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    truth.wcs.radesys = 'ICRS'
    truth.wcs.crpix = [128.5, 128.5]
    truth.wcs.crval = [359.99, 35.0]
    angle = np.deg2rad(23)
    truth.wcs.cd = (
        np.array([
            [-np.cos(angle), np.sin(angle)],
            [np.sin(angle), np.cos(angle)],
        ])
        / 3600
    )
    if distorted:
        a, b = np.zeros((4, 4)), np.zeros((4, 4))
        a[2, 0], a[1, 1], a[0, 2] = 1e-5, -2e-5, 1.5e-5
        b[2, 0], b[1, 1], b[0, 2] = -1e-5, 1e-5, -2e-5
        a[3, 0], a[2, 1], a[1, 2], a[0, 3] = 2e-7, -1e-7, 1e-7, -2e-7
        b[3, 0], b[2, 1], b[1, 2], b[0, 3] = -1e-7, 2e-7, -2e-7, 1e-7
        truth.sip = Sip(a, b, None, None, truth.wcs.crpix)
        truth.wcs.ctype = ['RA---TAN-SIP', 'DEC--TAN-SIP']
    grid = np.array(
        [(x, y) for x in (35, 80, 125, 170, 215) for y in (35, 90, 145, 205)],
        dtype=float,
    )
    xy = grid + rng.uniform(-8, 8, grid.shape)
    stars = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    # Realistic high proper motions, back-propagated from the image epoch.
    epoch = Time('2026-09-07T00:00:01', scale='utc')
    current = SkyCoord(
        stars.ra,
        stars.dec,
        pm_ra_cosdec=rng.uniform(-500, 500, len(xy)) * u.mas / u.yr,
        pm_dec=rng.uniform(-500, 500, len(xy)) * u.mas / u.yr,
        obstime=epoch,
    )
    import warnings
    from erfa import ErfaWarning

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', ErfaWarning)
        reference = current.apply_space_motion(
            new_obstime=Time(2016, format='jyear', scale='tcb'),
        )
    catalog = Table({
        'source_id': np.arange(len(xy), dtype=np.int64) + 10**17,
        'ra': reference.ra.deg,
        'dec': reference.dec.deg,
        'ref_epoch': np.full(len(xy), 2016.0),
        'pmra': reference.pm_ra_cosdec.to_value(u.mas / u.yr),
        'pmdec': reference.pm_dec.to_value(u.mas / u.yr),
        'phot_g_mean_mag': np.linspace(11, 17, len(xy)),
        'ruwe': np.ones(len(xy)),
    })
    y, x = np.indices((256, 256))
    data = rng.normal(100, 2, x.shape)
    for (sx, sy), amplitude in zip(xy, np.linspace(1000, 200, len(xy))):
        data += amplitude * np.exp(
            -((x - sx) ** 2 + (y - sy) ** 2) / (2 * 1.3**2)
        )
    # False detection and masked pixels.
    data += 500 * np.exp(-((x - 20) ** 2 + (y - 230) ** 2) / (2 * 1.3**2))
    data[:5] = np.nan
    header = truth.to_header(relax=True)
    # Preserve scale/orientation, but introduce a 25-pixel pointing error.
    pointing = truth.pixel_to_world(152.5, 110.5)
    header['RA'] = pointing.ra.to_string(unit=u.hourangle, sep=':')
    header['DEC'] = pointing.dec.to_string(unit=u.deg, sep=':')
    header['GEXP-STR'] = '2026-09-07T00:00:00'
    header['EXPTIME1'] = 2.0
    header['EXPTIME'] = 2.0
    header['TFRAME'] = 2.0
    if cube:
        data = np.array([data, data + rng.normal(0, 1, data.shape)])
        header['WCSAXES'] = 3
        header['CTYPE3'] = 'TIME'
        header['CUNIT3'] = 's'
        header['CRPIX3'] = 1.0
        header['CRVAL3'] = 0.0
        header['CDELT3'] = 2.0
        header['PC3_3'] = 1.0
    return fits.PrimaryHDU(data, header), catalog, truth, xy


@pytest.mark.parametrize(
    'cube,image', [(False, 'first'), (True, 'first'), (True, 'mean')]
)
def test_solve_image_and_cube(cube, image):
    hdu, catalog, truth, xy = make_field(cube=cube)
    before = hdu.data.copy()
    original_cd = astrometry.wcs_without_naxis3(hdu.header).pixel_scale_matrix
    astrometry.solve_field(hdu, catalog=catalog, image=image)
    fitted = astrometry.wcs_without_naxis3(hdu.header)
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    x, y = fitted.world_to_pixel(sky)
    np.testing.assert_allclose(np.column_stack((x, y)), xy, atol=0.05)
    np.testing.assert_equal(hdu.data, before)
    assert hdu.header['WCSORIG'] == 'Gaia DR3'
    assert hdu.header['WCSVALID']
    assert hdu.header['WCSNSTAR'] >= 16
    assert hdu.header['WCSRMS'] < 0.05
    assert WCS(hdu.header, naxis=2).pixel_n_dim == 2
    assert hdu.header['WCSAXES'] == (3 if cube else 2)
    np.testing.assert_array_equal(fitted.wcs.crpix, [128.5, 128.5])
    np.testing.assert_array_equal(fitted.pixel_scale_matrix, original_cd)
    assert hdu.header['A_ORDER'] == hdu.header['B_ORDER'] == 3
    if cube:
        assert hdu.header['CD3_3'] == 2.0
        assert hdu.header['CTYPE3'] == 'TIME'


def test_proper_motion_and_masked_rows():
    hdu, table, _, _ = make_field()
    table['pmra'] = MaskedColumn(table['pmra'], mask=[True] + [False] * 19)
    table['ruwe'][1] = 3.0
    filtered, sky = gaia.gaia_at_epoch(table, Time(2026, format='jyear'))
    assert len(filtered) == 18
    assert table['source_id'][0] not in filtered['source_id']
    original = SkyCoord(filtered['ra'], filtered['dec'], unit='deg')
    assert np.median(original.separation(sky).arcsec) > 1


def test_pm_ra_cosdec():
    table = Table({
        'ra': [359.999],
        'dec': [60.0],
        'pmra': [1000.0],
        'pmdec': [0.0],
        'ref_epoch': [2016.0],
        'phot_g_mean_mag': [12.0],
    })
    _, moved = gaia.gaia_at_epoch(
        table, Time(2026, format='jyear', scale='tcb')
    )
    origin = SkyCoord(359.999, 60, unit='deg')
    lon, lat = origin.spherical_offsets_to(moved)
    assert lon.arcsec[0] == pytest.approx(10, abs=1e-3)
    assert abs(lat.arcsec[0]) < 1e-3
    assert moved.ra.deg[0] < 1  # crosses RA zero


def test_fetch_query(monkeypatch):
    captured = {}

    def launch(query, verbose):
        captured['query'] = query
        return types.SimpleNamespace(get_results=lambda: Table({'ra': []}))

    monkeypatch.setitem(
        sys.modules,
        'astroquery.gaia',
        types.SimpleNamespace(
            Gaia=types.SimpleNamespace(launch_job_async=launch),
        ),
    )
    gaia.fetch_gaia(SkyCoord(12, -30, unit='deg'), 0.2, mag_limit=17)
    assert 'gaiadr3.gaia_source' in captured['query']
    assert 'TOP 1000' in captured['query']
    assert 'phot_g_mean_mag <= 17.000000' in captured['query']
    assert 'pmra IS NOT NULL' in captured['query']
    assert (
        "CIRCLE('ICRS', 12.000000000000, -30.000000000000" in captured['query']
    )


def test_online_solver_uses_pointing(monkeypatch):
    hdu, catalog, _, _ = make_field()
    called = {}

    def fetch(center, radius, mag_limit):
        called.update(center=center, radius=radius)
        return catalog

    monkeypatch.setattr(astrometry, 'fetch_gaia', fetch)
    astrometry.solve_field(hdu)
    expected = SkyCoord(
        hdu.header['RA'], hdu.header['DEC'], unit=(u.hourangle, u.deg)
    )
    assert called['center'].separation(expected).arcsec < 1e-6
    assert called['radius'] > 0.1


def test_matching_translation_with_outliers():
    rng = np.random.default_rng(55)
    predicted = rng.uniform(0, 500, (45, 2))
    detected = predicted[:30] + [47, -31] + rng.normal(0, 0.1, (30, 2))
    detected = np.concatenate((detected, rng.uniform(0, 500, (15, 2))))
    di, ci = astrometry.match_sources(detected, predicted)
    assert len(di) >= 30
    assert (ci[di < 30] == di[di < 30]).all()


def test_robust_fit_rejects_mismatches():
    _, _, truth, xy = make_field()
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    bad = xy.copy()
    bad[0] += [10, 8]
    fit, keep, rms = astrometry.fit_solution(bad, sky, truth, (256, 256))
    assert not keep[0]
    assert keep.sum() == len(xy) - 1
    assert rms < 1e-5


def test_failed_fit_preserves_header():
    hdu, catalog, _, _ = make_field()
    before = hdu.header.copy()
    with pytest.raises(ValueError, match='few'):
        astrometry.solve_field(hdu, catalog=catalog[:3])
    assert hdu.header == before


def test_update_clears_sip_and_pc():
    hdu, _, truth, _ = make_field(cube=True)
    hdu.header['CTYPE1'] = 'RA---TAN-SIP'
    hdu.header['CTYPE2'] = 'DEC--TAN-SIP'
    hdu.header['A_ORDER'] = 2
    hdu.header['B_ORDER'] = 2
    hdu.header['A_2_0'] = 1e-4
    hdu.header['B_0_2'] = 1e-4
    hdu.header['PV1_1'] = 1
    astrometry.update_wcs(hdu.header, truth, 3)
    assert 'A_2_0' not in hdu.header
    assert 'PV1_1' not in hdu.header
    assert 'PC1_1' not in hdu.header
    assert 'PC3_3' not in hdu.header
    assert hdu.header['CTYPE1'] == 'RA---TAN'
    result = WCS(hdu.header)
    assert result.pixel_n_dim == 3
    assert result.wcs.cd[2, 2] == 2


def test_observation_midpoints():
    hdu, _, _, _ = make_field(cube=True)
    first = astrometry.observation_time(hdu.header, 3, 'first')
    mean = astrometry.observation_time(hdu.header, 3, 'mean')
    assert first.isot == '2026-09-07T00:00:01.000'
    assert mean.isot == '2026-09-07T00:00:02.000'
    hdu.header['TELAPSE'] = 4.0
    assert astrometry.observation_time(hdu.header, 2).isot == mean.isot


def test_triwcs_local_catalog(tmp_path, monkeypatch):
    hdu, catalog, _, _ = make_field()
    source = tmp_path / 'input.fits'
    output = tmp_path / 'output.fits'
    catfile = tmp_path / 'gaia.ecsv'
    catalog.write(catfile)
    fits.HDUList([hdu, fits.ImageHDU(np.ones((2, 2)), name='EXTRA')]).writeto(
        source
    )
    monkeypatch.setattr(
        sys,
        'argv',
        ['triwcs', str(source), str(output), '--gaia-catalog', str(catfile)],
    )
    triwcs.main()
    with fits.open(output) as result:
        result.verify('exception')
        assert result[0].header['WCSORIG'] == 'Gaia DR3'
        np.testing.assert_equal(result[0].data, hdu.data)
        np.testing.assert_array_equal(result['EXTRA'].data, 1)


def test_trired_wcs_with_local_catalog(tmp_path, monkeypatch):
    from triseps.bin import trired

    hdu, catalog, _, _ = make_field(cube=True)
    hdu.header['FRAMEID'] = 'TEST'
    hdu.header['EFP-MIN1'] = 1
    hdu.header['EFP-MIN2'] = 1
    source = tmp_path / 'input.fits'
    output = tmp_path / 'output.fits'
    catfile = tmp_path / 'gaia.ecsv'
    database = tmp_path / 'database.fits'
    hdu.writeto(source)
    catalog.write(catfile)
    table = Table({'frame_id': ['TEST'], 'effective_area': ['256x256+0+0']})
    fits.HDUList([
        fits.PrimaryHDU(),
        fits.BinTableHDU(table, name='DATABASE'),
        fits.ImageHDU(np.zeros((256, 256)), name='DARK'),
        fits.ImageHDU(np.ones((256, 256)), name='FLAT'),
    ]).writeto(database)
    monkeypatch.setattr(trired, 'estimate_darkframe', lambda *args: 'DARK')
    monkeypatch.setattr(trired, 'estimate_flatframe', lambda *args: 'FLAT')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'trired',
            str(database),
            str(source),
            str(output),
            '--wcs',
            '--gaia-catalog',
            str(catfile),
        ],
    )
    trired.main()
    with fits.open(output) as hdus:
        assert hdus[0].header['WCSORIG'] == 'Gaia DR3'
        assert hdus[0].header['WCSNSTAR'] >= 16
        assert hdus[0].data.shape == hdu.data.shape


def test_unrelated_field_fails():
    hdu, catalog, _, _ = make_field()
    rng = np.random.default_rng(333)
    catalog['ra'] += rng.uniform(-0.03, 0.03, len(catalog))
    catalog['dec'] += rng.uniform(-0.03, 0.03, len(catalog))
    with pytest.raises(ValueError):
        astrometry.solve_field(hdu, catalog=catalog)


def test_reject_wrong_scale():
    _, _, truth, xy = make_field()
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    with pytest.raises(ValueError):
        astrometry.fit_solution(xy * 2, sky, truth, (512, 512))


def test_reject_bad_fit_rms():
    _, _, truth, xy = make_field()
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    rng = np.random.default_rng(44)
    distorted = xy + rng.uniform(-2, 2, xy.shape)
    with pytest.raises(ValueError):
        astrometry.fit_solution(distorted, sky, truth, (256, 256), max_rms=0.1)


def test_reject_collinear_stars():
    _, _, truth, _ = make_field()
    xy = np.column_stack((np.linspace(10, 200, 20), np.linspace(20, 210, 20)))
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    with pytest.raises(ValueError, match='collinear'):
        astrometry.fit_solution(xy, sky, truth, (256, 256))


def test_fk5_pointing_and_wcs_fallback():
    from astropy.coordinates import FK5

    hdu, _, truth, _ = make_field()
    hdu.header['RA'] = '08:00:00'
    hdu.header['DEC'] = '+30:00:00'
    hdu.header['RADESYS'] = 'FK5'
    hdu.header['EQUINOX'] = 2000.0
    _, center = astrometry.initial_wcs(hdu.header, hdu.data.shape)
    expected = SkyCoord(
        '08:00:00',
        '+30:00:00',
        unit=(u.hourangle, u.deg),
        frame=FK5(equinox=Time('J2000')),
    ).icrs
    assert center.separation(expected).arcsec < 1e-6
    del hdu.header['RA']
    del hdu.header['DEC']
    hdu.header['RADESYS'] = 'ICRS'
    _, center = astrometry.initial_wcs(hdu.header, hdu.data.shape)
    expected = truth.pixel_to_world(127.5, 127.5)
    assert center.separation(expected).arcsec < 1e-6


@pytest.mark.parametrize(
    'data', [np.ones((30, 30)), np.full((30, 30), np.nan)]
)
def test_reject_unusable_images(data):
    with pytest.raises(ValueError):
        astrometry.detect_sources(data)


def test_gaia_failure_message(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')

    monkeypatch.setitem(
        sys.modules,
        'astroquery.gaia',
        types.SimpleNamespace(
            Gaia=types.SimpleNamespace(launch_job_async=fail),
        ),
    )
    with pytest.raises(RuntimeError, match='Gaia DR3 query failed'):
        gaia.fetch_gaia(SkyCoord(12, 30, unit='deg'), 0.1)


@pytest.mark.parametrize('cube,image', [(False, 'first'), (True, 'mean')])
def test_reject_target_stack(cube, image):
    hdu, catalog, _, _ = make_field(cube=cube)
    hdu.header['TRKALIGN'] = 'TARGET'
    with pytest.raises(ValueError, match='before target stacking'):
        astrometry.solve_field(hdu, catalog=catalog, image=image)


@pytest.mark.parametrize('shape,dec', [((240, 320), 35), ((241, 321), 75)])
def test_cubic_sip_recovery_fixed_cd_and_center(shape, dec):
    _, _, truth, _ = make_field(distorted=True)
    truth.wcs.crpix = (np.array(shape[::-1]) + 1) / 2
    truth.wcs.crval = [359.999, dec]
    truth.sip = Sip(truth.sip.a, truth.sip.b, None, None, truth.wcs.crpix)
    rng = np.random.default_rng(777)
    xy = rng.uniform([5, 5], np.array(shape[::-1]) - 5, (100, 2))
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    seed = truth.deepcopy()
    seed.sip = None
    seed.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    seed.wcs.crval = truth.wcs_pix2world(
        [truth.wcs.crpix - 1 + [25, -18]],
        0,
    )[0]
    # Deliberately supply off-center CRPIX; the fit must still fix the center.
    seed.wcs.crpix += [15, -20]
    fixed_cd = seed.pixel_scale_matrix.copy()
    solution, keep, rms = astrometry.fit_solution(xy, sky, seed, shape)
    np.testing.assert_array_equal(solution.pixel_scale_matrix, fixed_cd)
    np.testing.assert_array_equal(solution.wcs.crpix, truth.wcs.crpix)
    assert keep.all()
    assert rms < 1e-5
    actual = SkyCoord(*solution.wcs.crval, unit='deg')
    expected = SkyCoord(*truth.wcs.crval, unit='deg')
    assert actual.separation(expected).arcsec < 1e-4
    np.testing.assert_allclose(solution.sip.a, truth.sip.a, atol=1e-10)
    np.testing.assert_allclose(solution.sip.b, truth.sip.b, atol=1e-10)
    # Check independent positions, including image edges, not just fit stars.
    sample = rng.uniform([0, 0], np.array(shape[::-1]) - 1, (100, 2))
    actual = solution.pixel_to_world(sample[:, 0], sample[:, 1])
    expected = truth.pixel_to_world(sample[:, 0], sample[:, 1])
    assert np.max(actual.separation(expected).arcsec) < 1e-4
    assert solution.sip.ap is None and solution.sip.bp is None


@pytest.mark.parametrize('cube', [False, True])
def test_distorted_image_pipeline_and_serialization(tmp_path, cube):
    hdu, catalog, truth, xy = make_field(distorted=True, cube=cube)
    old_cd = astrometry.wcs_without_naxis3(hdu.header).pixel_scale_matrix
    old_crval = SkyCoord(
        hdu.header['RA'], hdu.header['DEC'], unit=(u.hourangle, u.deg)
    )
    astrometry.solve_field(hdu, catalog=catalog)
    filename = tmp_path / 'sip.fits'
    hdu.writeto(filename)
    with fits.open(filename) as result:
        result.verify('exception')
        header = result[0].header
        fitted = WCS(header, naxis=2)
        np.testing.assert_array_equal(fitted.pixel_scale_matrix, old_cd)
        np.testing.assert_array_equal(fitted.wcs.crpix, [128.5, 128.5])
        assert header['WCSSIP'] == 3
        assert 'AP_ORDER' not in header and 'BP_ORDER' not in header
        assert (
            SkyCoord(*fitted.wcs.crval, unit='deg')
            .separation(old_crval)
            .arcsec
            > 20
        )
        sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
        x, y = fitted.world_to_pixel(sky)
        np.testing.assert_allclose(np.column_stack((x, y)), xy, atol=0.05)


def test_insufficient_stars_does_not_lower_degree():
    _, _, truth, xy = make_field()
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    with pytest.raises(ValueError, match='need 12'):
        astrometry.fit_solution(xy[:11], sky[:11], truth, (256, 256))


@pytest.mark.parametrize('degree', [0, 2])
def test_explicit_lower_sip_degree(degree):
    _, _, truth, xy = make_field()
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    solution, _, rms = astrometry.fit_solution(
        xy,
        sky,
        truth,
        (256, 256),
        sip_degree=degree,
    )
    np.testing.assert_array_equal(
        solution.pixel_scale_matrix, truth.pixel_scale_matrix
    )
    np.testing.assert_array_equal(solution.wcs.crpix, [128.5, 128.5])
    assert rms < 1e-5
    if degree == 0:
        assert solution.sip is None
    else:
        assert solution.sip.a_order == 2


def test_sip_rank_deficiency():
    _, _, truth, _ = make_field()
    angle = np.linspace(0, 2 * np.pi, 20, endpoint=False)
    xy = np.column_stack((128 + 80 * np.cos(angle), 128 + 80 * np.sin(angle)))
    sky = truth.pixel_to_world(xy[:, 0], xy[:, 1])
    with pytest.raises(ValueError, match='constrain|ill-conditioned'):
        astrometry.fit_solution(xy, sky, truth, (256, 256))
