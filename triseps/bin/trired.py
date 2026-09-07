#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable
from astropy.stats import sigma_clipped_stats
import astropy.io.fits as fits
import numpy as np
import sys

from ..utils import pick, chop_reference_pixels, timestamp
from ..dark import estimate_darkframe
from ..flat import estimate_flatframe
from ..astrometry import (
    solve_field,
    drop_naxis3_keywords,
    add_astrometry_arguments,
    astrometry_options,
)
from ..tracking import align_cube
from ..warnings import eprint


def main():
    from argparse import ArgumentParser as ap

    parser = ap(description='reduce TriCCS data usnig calibration database')

    parser.add_argument('database', type=str, help='calibratoin database file')
    parser.add_argument('fits', type=str, help='input FITS file')
    parser.add_argument('output', type=str, help='output FITS file')
    parser.add_argument(
        '-w',
        '--wcs',
        action='store_true',
        help='calibrate the WCS using Gaia DR3',
    )
    parser.add_argument(
        '-q',
        '--ql',
        action='store_true',
        help='generate a stacked image cube for quick look',
    )
    parser.add_argument(
        '-s',
        '--stack',
        action='store_true',
        help='generate a stacked image using 3-sigma clipped mean',
    )
    parser.add_argument(
        '--track',
        action='store',
        type=str,
        help='Seimei _tk.dat ephemeris; align sidereal data on the target',
    )
    parser.add_argument(
        '-r',
        '--reverse',
        action='store_true',
        help='align non-sidereal observations on stars (requires --track)',
    )
    parser.add_argument(
        '-f',
        '--overwrite',
        action='store_true',
        help='overwrite the output file if exists',
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='enable debug messages'
    )

    add_astrometry_arguments(parser)
    args = parser.parse_args(sys.argv[1:])

    if args.reverse and not args.track:
        parser.error('--reverse requires --track')
    if args.track and args.ql:
        parser.error('--track cannot be combined with --ql; use --stack')
    if args.ql and args.stack:
        parser.error('--ql and --stack are mutually exclusive')

    db = QTable.read(args.database)
    hdul = fits.open(args.database)

    input = fits.open(args.fits)[0]
    frame_id = input.header['frameid']

    output = fits.PrimaryHDU(data=None, header=input.header)
    shifts = None
    if args.track and input.data.ndim != 3:
        parser.error('--track requires a 3D FITS image cube')

    dark_id = estimate_darkframe(db, frame_id)
    dark_hdu = hdul[dark_id]

    flat_id = estimate_flatframe(db, frame_id)
    flat_hdu = hdul[flat_id]

    with timestamp(output):

        def hist(message):
            output.header.add_history(message)
            eprint(f'INFO: {message}')

        area = pick(db, frame_id=frame_id)['effective_area']
        output.data = chop_reference_pixels(input.data, area).astype(float)
        # Translate both the linear and SIP reference pixel via CRPIX.
        for axis in (1, 2):
            key = f'CRPIX{axis}'
            if key in output.header:
                output.header[key] -= input.header[f'EFP-MIN{axis}'] - 1
        hist(f'photo-sensitive area {area} is extracted.')

        output.data -= dark_hdu.data
        hist(f'dark current subtracted with {dark_id}.')

        valid_flat = np.isfinite(flat_hdu.data) & (flat_hdu.data != 0)
        np.divide(
            output.data, flat_hdu.data, out=output.data, where=valid_flat
        )
        output.data[..., ~valid_flat] = np.nan
        hist(f'flat frame corrected with {flat_id}.')

        if args.wcs is True:
            output = solve_field(
                output,
                verbose=args.verbose,
                **astrometry_options(args),
            )

        if args.track:
            shifts = align_cube(output, args.track, reverse=args.reverse)
            hist(
                f'frames aligned on {output.header["TRKALIGN"]} '
                'with bilinear interpolation.'
            )

        if args.ql is True:
            assert output.data.ndim == 3
            output.data = output.data.mean(axis=0)
            hist('image cube is stacked for quick look.')
        elif args.stack is True:
            assert output.data.ndim == 3
            masked = np.ma.masked_invalid(output.data)
            stats = sigma_clipped_stats(masked, axis=0)
            output.data = np.ma.filled(stats[0], np.nan)
            hist('3-sigma clipped mean is calculated.')

        if args.ql or args.stack:
            drop_naxis3_keywords(output.header)
            output.header['WCSAXES'] = 2

    result = fits.HDUList([output])
    if shifts is not None:
        result.append(fits.BinTableHDU(shifts, name='SHIFTS'))
    result.writeto(args.output, overwrite=args.overwrite)
