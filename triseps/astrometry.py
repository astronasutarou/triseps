"""Gaia DR3 astrometric calibration using the approximate header WCS."""

import re
import warnings

import numpy as np
from astropy import units as u
from astropy.coordinates import FK4, FK5, SkyCoord
from astropy.stats import sigma_clip, sigma_clipped_stats
from astropy.table import Table
from astropy.time import Time, TimeDelta
from astropy.wcs import WCS as wcsobj, Sip, NoConvergence
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

from .gaia import fetch_gaia, gaia_at_epoch
from .warnings import eprint

__keywords_naxis3 = (
    'NAXIS3',
    'CTYPE3',
    'CRPIX3',
    'CRVAL3',
    'CUNIT3',
    'CDELT3',
    'CROTA3',
    'CD1_3',
    'CD2_3',
    'CD3_3',
    'CD3_2',
    'CD3_1',
    'PC1_3',
    'PC2_3',
    'PC3_3',
    'PC3_2',
    'PC3_1',
)


def drop_naxis3_keywords(header):
    """remove NAXIS3 keywords from a fits header

    This function drops NAXIS3 keywords from a header object.
    This operation alters the header object in place.

    Paramters:
      header (Header): a fits header object

    Return:
      Header: a FITS header object without NAXIS3 keywords
    """

    header.set('NAXIS', 2)
    if 'WCSAXES' in header:
        header['WCSAXES'] = 2
    for key in __keywords_naxis3:
        header.remove(key, ignore_missing=True)
    return header


def wcs_without_naxis3(header):
    """drop naxis3 keywords from header

    Paramters:
      header (Header): fits header object

    Return:
      WCSObj: a wcs object without NAXIS3 keywords
    """

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore')
        hdr = header.copy()
        drop_naxis3_keywords(hdr)
        return wcsobj(header=hdr)


def observation_time(header, ndim, image='first'):
    """Choose the midpoint of the first exposure or of the image sequence."""

    scale = header.get('TIMESYS', 'UTC').lower()
    if 'GEXP-STR' in header:
        start = Time(header['GEXP-STR'], scale=scale)
    elif 'MJD-STR' in header:
        start = Time(header['MJD-STR'], format='mjd', scale=scale)
    else:
        date = header['DATE-OBS']
        if 'T' not in date:
            date += 'T' + header['UT-STR']
        start = Time(date, scale=scale)
    if ndim == 3 and image == 'first':
        duration = float(header['EXPTIME1'])
    elif ndim == 3:
        duration = (int(header['NAXIS3']) - 1) * float(
            header['TFRAME']
        ) + float(header['EXPTIME1'])
    elif 'TELAPSE' in header:
        duration = float(header['TELAPSE'])
    elif 'MJD-END' in header and 'MJD-STR' in header:
        end = Time(header['MJD-END'], format='mjd', scale=scale)
        duration = (end - start).to_value(u.s)
    else:
        duration = float(header['EXPTIME'])
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError('observation duration must be finite and positive')
    return start + TimeDelta(duration / 2, format='sec')


def initial_wcs(header, shape):
    """Build an ICRS TAN seed with header pointing, scale, and orientation."""

    original = wcs_without_naxis3(header)
    if not original.has_celestial or original.wcs.lng != 0:
        raise ValueError('an approximate RA/Dec WCS is required')
    matrix = original.pixel_scale_matrix
    if (
        matrix.shape != (2, 2)
        or not np.all(np.isfinite(matrix))
        or abs(np.linalg.det(matrix)) < 1e-16
    ):
        raise ValueError('header WCS must have a nonsingular pixel scale')
    if 'RA' in header and 'DEC' in header:
        system = header.get('RADESYS', 'ICRS').upper()
        if system == 'FK5':
            frame = FK5(
                equinox=Time(header.get('EQUINOX', 2000.0), format='jyear')
            )
        elif system == 'FK4':
            frame = FK4(
                equinox=Time(header.get('EQUINOX', 1950.0), format='byear')
            )
        elif system == 'ICRS':
            frame = 'icrs'
        else:
            raise ValueError(
                f'unsupported pointing coordinate system: {system}'
            )
        ra_unit = u.hourangle if isinstance(header['RA'], str) else u.deg
        center = SkyCoord(
            header['RA'], header['DEC'], unit=(ra_unit, u.deg), frame=frame
        ).icrs
    else:
        center = original.pixel_to_world(
            (shape[1] - 1) / 2,
            (shape[0] - 1) / 2,
        ).icrs
    seed = wcsobj(naxis=2)
    seed.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    seed.wcs.radesys = 'ICRS'
    seed.wcs.crval = [center.ra.deg, center.dec.deg]
    seed.wcs.crpix = [(shape[1] + 1) / 2, (shape[0] + 1) / 2]
    seed.wcs.cd = matrix
    return seed, center


def detect_sources(data, fwhm=3.0, threshold=5.0, max_sources=300):
    """Return bright DAOStarFinder centroids in zero-based (x, y) pixels."""

    from photutils.detection import DAOStarFinder

    if fwhm <= 0 or threshold <= 0:
        raise ValueError('detection FWHM and threshold must be positive')
    invalid = ~np.isfinite(data)
    if invalid.all():
        raise ValueError('image has no finite pixels')
    _, median, noise = sigma_clipped_stats(data, mask=invalid)
    if not np.isfinite(noise) or noise <= 0:
        raise ValueError('image has no measurable background noise')
    background_subtracted = np.where(invalid, 0, data - median)
    finder = DAOStarFinder(
        threshold=threshold * noise, fwhm=fwhm, exclude_border=True
    )
    found = finder(background_subtracted, mask=invalid)
    if found is None or len(found) == 0:
        raise ValueError('no usable stars detected')
    # DAO morphology filters reject many cosmic rays and saturated plateaus.
    xy = np.column_stack((found['x_centroid'], found['y_centroid']))
    flux = np.asarray(found['flux'])
    good = np.all(np.isfinite(xy), axis=1) & np.isfinite(flux) & (flux > 0)
    order = np.argsort(flux[good])[::-1][:max_sources]
    return xy[good][order]


def unique_matches(detected, predicted, radius):
    """Find mutual nearest neighbours within a pixel-distance threshold."""

    distance, cat_index = cKDTree(predicted).query(detected)
    _, det_index = cKDTree(detected).query(predicted)
    index = np.arange(len(detected))
    good = (distance <= radius) & (det_index[cat_index] == index)
    return index[good], cat_index[good], distance[good]


def match_sources(detected, predicted, radius=3.0, min_matches=6):
    """Estimate pointing translation, trusting header scale and orientation.

    Candidate offsets are voted into radius-sized bins. Adjacent bins are
    combined so a true offset at a bin boundary is not lost. Candidates are
    scored with mutual nearest-neighbour matches, then refined by medians.
    """

    if not np.isfinite(radius) or radius <= 0:
        raise ValueError('matching radius must be finite and positive')
    if min(len(detected), len(predicted)) < min_matches:
        raise ValueError('too few stars for astrometric matching')
    differences = (detected[:80, None, :] - predicted[None, :200, :]).reshape(
        -1, 2
    )
    bins = np.floor(differences / radius).astype(int)
    keys, counts = np.unique(bins, axis=0, return_counts=True)
    vote_tree = cKDTree(keys)
    scores = np.array([
        counts[vote_tree.query_ball_point(key, 1, p=np.inf)].sum()
        for key in keys
    ])
    candidates = [np.zeros(2)]
    for index in np.argsort(scores)[-40:]:
        nearby = np.max(np.abs(bins - keys[index]), axis=1) <= 1
        candidates.append(np.median(differences[nearby], axis=0))
    best = None
    best_score = (-1, -np.inf)
    for shift in candidates:
        for _ in range(3):
            di, ci, residual = unique_matches(
                detected, predicted + shift, radius
            )
            if len(di) < min_matches:
                break
            shift = np.median(detected[di] - predicted[ci], axis=0)
        di, ci, residual = unique_matches(detected, predicted + shift, radius)
        score = (len(di), -np.median(residual) if len(di) else -np.inf)
        if score > best_score:
            best_score = score
            best = (di, ci)
    if best_score[0] < min_matches:
        raise ValueError('no consistent Gaia/image translation found')
    return best


def sip_terms(degree):
    """Return only the forward SIP terms of total degree two and above."""

    if degree not in (0, 2, 3):
        raise ValueError('SIP degree must be 0, 2, or 3')
    return [
        (i, order - i)
        for order in range(2, degree + 1)
        for i in range(order + 1)
    ]


def fit_solution(
    detected, sky, seed, shape, max_rms=1.0, min_matches=6, sip_degree=3
):
    """Fit CRVAL and forward SIP with CD and central CRPIX strictly fixed.

    CRVAL is parameterized as a displacement in the seed tangent plane.
    Polynomial coefficients are scaled by the image half-width/half-height
    during optimization, then converted back to standard SIP pixel units.
    """

    terms = sip_terms(sip_degree)
    minimum = max(min_matches, int(np.ceil(1.5 * (len(terms) + 1))))
    crpix = (np.array(shape[::-1], dtype=float) + 1) / 2
    scale = np.array(shape[::-1], dtype=float) / 2
    uv = (detected + 1 - crpix) / scale
    design = (
        np.column_stack([uv[:, 0] ** i * uv[:, 1] ** j for i, j in terms])
        if terms
        else np.empty((len(detected), 0))
    )
    sky_degrees = np.column_stack((sky.icrs.ra.deg, sky.icrs.dec.deg))
    projection = seed.deepcopy()
    projection.sip = None
    projection.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    projection.wcs.crpix = crpix
    projection.wcs.cd = seed.pixel_scale_matrix.copy()
    origin = projection.deepcopy()
    predicted = origin.wcs_world2pix(sky_degrees, 0)
    parameters = np.zeros(2 + 2 * len(terms))
    parameters[:2] = np.median(predicted - detected, axis=0)

    def set_center(values):
        """Set CRVAL without changing the linear pixel transformation."""

        projection.wcs.crval = origin.wcs_pix2world(
            [crpix - 1 + values[:2]],
            0,
        )[0]
        projection.wcs.set()

    def residuals(values, mask):
        """Measure discrepancies in the undistorted pixel plane."""

        set_center(values)
        target = projection.wcs_world2pix(sky_degrees[mask], 0)
        coefficients = values[2:].reshape(2, len(terms)).T
        return (detected[mask] + design[mask] @ coefficients - target).ravel()

    keep = np.ones(len(detected), dtype=bool)
    for _ in range(8):
        points = detected[keep]
        if len(points) < minimum:
            raise ValueError(
                f'too few astrometric inliers: need {minimum} '
                f'for SIP degree {sip_degree}'
            )
        span = np.ptp(points, axis=0)
        if np.any(span < 0.1 * np.array(shape[::-1])):
            raise ValueError('matched stars cover too little of the image')
        singular = np.linalg.svd(
            points - points.mean(axis=0), compute_uv=False
        )
        if singular[-1] < 0.05 * singular[0]:
            raise ValueError('matched stars are nearly collinear')
        basis = np.column_stack((np.ones(keep.sum()), design[keep]))
        if np.linalg.matrix_rank(basis) < len(terms) + 1:
            raise ValueError(
                'matched positions do not constrain the SIP terms'
            )
        if np.linalg.cond(basis) > 1e4:
            raise ValueError('SIP fit is ill-conditioned for these positions')
        fit = least_squares(
            residuals,
            parameters,
            args=(keep,),
            x_scale='jac',
            loss='soft_l1',
            f_scale=max_rms,
            max_nfev=300,
            ftol=1e-10,
            xtol=1e-10,
            gtol=1e-10,
        )
        if not fit.success or not np.all(np.isfinite(fit.x)):
            raise ValueError('CRVAL/SIP fit failed to converge')
        parameters = fit.x
        residual = np.linalg.norm(
            residuals(parameters, np.ones(len(keep), dtype=bool)).reshape(
                -1, 2
            ),
            axis=1,
        )
        median = np.median(residual[keep])
        mad = 1.4826 * np.median(np.abs(residual[keep] - median))
        new_keep = keep & (
            residual <= min(3 * max_rms, max(0.25, median + 3 * mad))
        )
        if np.array_equal(keep, new_keep):
            break
        keep = new_keep
    else:
        raise ValueError('astrometric outlier rejection did not converge')
    # Remove robust-loss weighting after rejecting the outliers.
    fit = least_squares(
        residuals,
        parameters,
        args=(keep,),
        x_scale='jac',
        max_nfev=300,
        ftol=1e-10,
        xtol=1e-10,
        gtol=1e-10,
    )
    if not fit.success or not np.all(np.isfinite(fit.x)):
        raise ValueError('final CRVAL/SIP fit failed to converge')
    set_center(fit.x)
    solution = projection.deepcopy()
    if terms:
        a = np.zeros((sip_degree + 1, sip_degree + 1))
        b = np.zeros_like(a)
        coefficients = fit.x[2:].reshape(2, len(terms))
        for n, (i, j) in enumerate(terms):
            a[i, j] = coefficients[0, n] / scale[0] ** i / scale[1] ** j
            b[i, j] = coefficients[1, n] / scale[0] ** i / scale[1] ** j
        solution.sip = Sip(a, b, None, None, crpix)
        solution.wcs.ctype = ['RA---TAN-SIP', 'DEC--TAN-SIP']
    try:
        x, y = solution.all_world2pix(
            sky_degrees[keep], 0, tolerance=1e-8, maxiter=100
        ).T
    except NoConvergence as exc:
        raise ValueError('fitted SIP inverse does not converge') from exc
    residual = np.linalg.norm(np.column_stack((x, y)) - detected[keep], axis=1)
    rms = float(np.sqrt(np.mean(residual**2)))
    if not np.isfinite(rms) or rms > max_rms:
        raise ValueError(f'astrometric RMS {rms:.3f} exceeds {max_rms} pixels')
    validate_sip(solution, shape)
    return solution, keep, rms


def validate_sip(solution, shape):
    """Reject folding or noninvertible SIP mappings across the field."""

    if solution.sip is None:
        return
    gx, gy = np.meshgrid(
        np.linspace(0, shape[1] - 1, 9), np.linspace(0, shape[0] - 1, 9)
    )
    xy = np.column_stack((gx.ravel(), gy.ravel()))
    uv = xy + 1 - solution.wcs.crpix
    jac = np.tile(np.eye(2), (len(xy), 1, 1))
    for axis, coefficients in enumerate((solution.sip.a, solution.sip.b)):
        for i, j in np.ndindex(coefficients.shape):
            if i:
                jac[:, axis, 0] += (
                    i
                    * coefficients[i, j]
                    * uv[:, 0] ** (i - 1)
                    * uv[:, 1] ** j
                )
            if j:
                jac[:, axis, 1] += (
                    j
                    * coefficients[i, j]
                    * uv[:, 0] ** i
                    * uv[:, 1] ** (j - 1)
                )
    if np.any(np.linalg.det(jac) <= 0):
        raise ValueError('fitted SIP folds within the image')
    try:
        roundtrip = solution.all_world2pix(
            solution.all_pix2world(xy, 0),
            0,
            tolerance=1e-8,
            maxiter=100,
        )
    except NoConvergence as exc:
        raise ValueError('fitted SIP inverse fails across the image') from exc
    if (
        not np.all(np.isfinite(roundtrip))
        or np.max(np.linalg.norm(roundtrip - xy, axis=1)) > 1e-3
    ):
        raise ValueError('fitted SIP fails the image round-trip check')


def update_wcs(header, solution, ndim):
    """Replace spatial WCS, clearing old distortion and retaining cube time."""

    # Spatial PC/CD must not coexist with incompatible old normalizations.
    pattern = re.compile(
        r'^(CTYPE[12]|CUNIT[12]|CRVAL[12]|CRPIX[12]|CDELT[12]|CROTA[12]'
        r'|(?:PC|CD)[12]_[12]|(?:PV|PS)[12]_\d+'
        r'|(?:A|B|AP|BP)_(?:ORDER|DMAX|\d+_\d+)'
        r'|LONPOLE|LATPOLE|RADESYS|EQUINOX)$'
    )
    time_scale = header.get(
        'CD3_3', header.get('CDELT3', 1.0) * header.get('PC3_3', 1.0)
    )
    for key in list(header):
        if pattern.match(key):
            header.remove(key, remove_all=True, ignore_missing=True)
    spatial = solution.to_header(relax=True)
    # Store CD consistently, including the temporal axis of a cube.
    for key in list(spatial):
        if key.startswith(('PC', 'CDELT')):
            del spatial[key]
    header.update(spatial)
    for i in range(2):
        for j in range(2):
            header[f'CD{i + 1}_{j + 1}'] = solution.pixel_scale_matrix[i, j]
    if ndim == 3:
        for key in list(header):
            if re.match(r'^PC(?:3_\d|\d_3)$', key):
                del header[key]
        for key in ('CD1_3', 'CD2_3', 'CD3_1', 'CD3_2'):
            header[key] = 0.0
        header['CD3_3'] = time_scale
        header['WCSAXES'] = 3
    else:
        drop_naxis3_keywords(header)
        header['WCSAXES'] = 2


def solve_field(
    src,
    verbose=False,
    *,
    image='first',
    catalog=None,
    mag_limit=18.0,
    fwhm=3.0,
    threshold=5.0,
    match_radius=3.0,
    max_rms=1.0,
    sip_degree=3,
):
    """Calibrate a Primary/Image HDU against epoch-corrected Gaia DR3 stars.

    Cube detection uses its first frame, or a clipped mean when image='mean'.
    The pixel data are never altered. Header writes occur only after a fit
    passes source-count, geometry, residual, and invertibility checks.
    CD stays fixed; CRPIX is fixed at the spatial image center.
    Supply a Gaia table (or filename) to avoid an online query.
    """

    sip_terms(sip_degree)
    if image not in ('first', 'mean'):
        raise ValueError('astrometric image must be first or mean')
    if src.data is None or src.data.ndim not in (2, 3):
        raise ValueError('astrometry requires a 2D image or 3D cube')
    for name, value in (
        ('mag_limit', mag_limit),
        ('fwhm', fwhm),
        ('threshold', threshold),
        ('match_radius', match_radius),
        ('max_rms', max_rms),
    ):
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be finite and positive')
    if src.header.get('TRKALIGN') == 'TARGET' and (
        src.data.ndim == 2 or image == 'mean'
    ):
        raise ValueError('use the first cube frame before target stacking')
    if src.data.ndim == 3:
        if image == 'first':
            data = src.data[0]
        else:
            data = (
                sigma_clip(
                    np.ma.masked_invalid(src.data),
                    axis=0,
                )
                .mean(axis=0)
                .filled(np.nan)
            )
    else:
        data = src.data
    epoch = observation_time(src.header, src.data.ndim, image)
    seed, center = initial_wcs(src.header, data.shape)
    corners = seed.pixel_to_world(
        [0, data.shape[1] - 1, 0, data.shape[1] - 1],
        [0, 0, data.shape[0] - 1, data.shape[0] - 1],
    )
    # Six arcminutes of pointing/motion margin around the nominal footprint.
    radius = float(np.max(center.separation(corners).deg)) + 0.1
    if catalog is None:
        catalog = fetch_gaia(center, radius, mag_limit=mag_limit)
    elif isinstance(catalog, (str, bytes)) or hasattr(catalog, '__fspath__'):
        catalog = Table.read(catalog)
    reference, sky = gaia_at_epoch(catalog, epoch, mag_limit=mag_limit)
    detected = detect_sources(data, fwhm=fwhm, threshold=threshold)
    x, y = seed.world_to_pixel(sky)
    predicted = np.column_stack((x, y))
    finite = np.all(np.isfinite(predicted), axis=1)
    predicted, sky = predicted[finite], sky[finite]
    di, ci = match_sources(detected, predicted, radius=match_radius)
    solution, inliers, rms = fit_solution(
        detected[di],
        sky[ci],
        seed,
        data.shape,
        max_rms=max_rms,
        sip_degree=sip_degree,
    )
    # Rematch once using the fitted WCS, admitting fainter consistent stars.
    x, y = solution.world_to_pixel(sky)
    di, ci, _ = unique_matches(detected, np.column_stack((x, y)), match_radius)
    solution, inliers, rms = fit_solution(
        detected[di],
        sky[ci],
        seed,
        data.shape,
        max_rms=max_rms,
        sip_degree=sip_degree,
    )
    header = src.header.copy()
    update_wcs(header, solution, src.data.ndim)
    header['WCSVALID'] = True
    header['WCSORIG'] = 'Gaia DR3'
    header['WCSSIP'] = (sip_degree, 'Forward SIP degree; CD and CRPIX fixed')
    header['WCSNSTAR'] = (int(inliers.sum()), 'Number of astrometric inliers')
    header['WCSRMS'] = (rms, 'Radial RMS residual in pixels')
    header['WCSMJD'] = (epoch.utc.mjd, 'Astrometric epoch, UTC MJD')
    header['WCSIMAGE'] = image.upper() if src.data.ndim == 3 else 'IMAGE'
    header.add_history('[wcs] Gaia DR3 proper motions propagated to WCSMJD.')
    header.add_history(
        f'[wcs] CRVAL/SIP degree {sip_degree} fit; CD fixed; CRPIX at center.'
    )
    header.add_history('[wcs] Parallax and radial velocity omitted.')
    header.add_history(f'[wcs] {inliers.sum()} stars; RMS {rms:.4f} pixels.')
    src.header = header
    if verbose:
        eprint(
            f'INFO: Gaia DR3: {len(reference)} references, '
            f'{len(detected)} detections, {inliers.sum()} inliers; '
            f'RMS {rms:.4f} pixels.'
        )
    return src


def add_astrometry_arguments(parser):
    """Add shared Gaia solver settings to triwcs and trired."""

    parser.add_argument(
        '--wcs-image',
        choices=('first', 'mean'),
        default='first',
        help='cube image for WCS detection (default: first)',
    )
    parser.add_argument(
        '--wcs-sip-degree',
        type=int,
        choices=(0, 2, 3),
        default=3,
        help='forward SIP degree; 0 disables distortion (default: 3)',
    )
    parser.add_argument(
        '--gaia-catalog', help='local Gaia table instead of query'
    )
    parser.add_argument(
        '--gaia-mag-limit',
        type=float,
        default=18.0,
        help='Gaia G magnitude limit (default: 18)',
    )
    parser.add_argument(
        '--wcs-fwhm',
        type=float,
        default=3.0,
        help='detection FWHM in pixels (default: 3)',
    )
    parser.add_argument(
        '--wcs-threshold',
        type=float,
        default=5.0,
        help='detection threshold in background sigma (default: 5)',
    )
    parser.add_argument(
        '--wcs-match-radius',
        type=float,
        default=3.0,
        help='matching tolerance in pixels (default: 3)',
    )
    parser.add_argument(
        '--wcs-max-rms',
        type=float,
        default=1.0,
        help='maximum fit RMS in pixels (default: 1)',
    )


def astrometry_options(args):
    """Translate shared CLI settings into solve_field keyword arguments."""

    return dict(
        image=args.wcs_image,
        catalog=args.gaia_catalog,
        mag_limit=args.gaia_mag_limit,
        fwhm=args.wcs_fwhm,
        threshold=args.wcs_threshold,
        match_radius=args.wcs_match_radius,
        max_rms=args.wcs_max_rms,
        sip_degree=args.wcs_sip_degree,
    )
