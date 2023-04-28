#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable, unique
import astropy.io.fits as fits
import numpy as np
import sys, re

from .warnings import eprint

__unique_keys = (
    'exptime_single',
    'gain',
    'effective_area',
)

__display_keys = (
    'data_type',
    'frame_id',
    'observer',
    'observation_date',
    'proposal_id',
    'object',
    'exptime_single',
    'gain',
    'shutter',
    'dome_slit',
    'effective_area',
)


def split_dataset(database):
    ''' Split the database into subset by unique keys. '''
    unique_setups = unique(database, __unique_keys)[__unique_keys]
    for setup in unique_setups:
        key = generate_key(setup)
        yield key, database[database[__unique_keys] == setup]


def generate_key(setup):
    texp, gain, area = setup
    return f't{texp*1000:08.0f}_g{gain*100:04.0f}_{area}'


def chop_reference_pixels(data, key):
    reg = re.compile(r'.*_(\d+)x(\d+)\+(\d+)\+(\d+)')
    res = reg.match(key)
    if res is not None:
        ax1, ax2, cx1, cx2 = [int(n) for n in res.groups()]
        data = data[cx2:cx2+ax2, cx1:cx1+ax1]
    return data


def generate_darkframe(key, dark):
    phdu = fits.PrimaryHDU()
    data = []
    for d in dark:
        frame_id = d['frame_id']
        filename = f'{frame_id}.fits'
        phdu.header.add_history(f'{filename}')
        with fits.open(filename) as hdul:
            assert hdul[0].header['naxis'] == 3
            median = np.median(hdul[0].data, axis=0)
            chopped = chop_reference_pixels(median, key)
            data.append(chopped)
    phdu.data = np.mean(np.array(data), axis=0)
    return phdu


def main(argv):
    from argparse import ArgumentParser as ap
    parser = ap(description='generate dark frame')
    parser.add_argument(
        'input', type=str,
        help='observation database')
    parser.add_argument(
        '-f', '--overwrite', action='store_true',
        help='overwrite the output file if exists')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='enable debug messages')

    args = parser.parse_args(argv[1:])

    database = QTable.read(args.input)

    for key, subset in split_dataset(database):
        dark = subset[subset['data_type'] == 'DARK']
        if len(dark) == 0:
            eprint(f'Caution: no DARK frames for {key}.')
            continue
        print(f'Generate dark_{key} from {len(dark)} frames.')

        phdu = generate_darkframe(key, dark)

        filename = f'dark_{key}.fits'
        phdu.writeto(filename, overwrite=args.overwrite)


if __name__ == '__main__':
    main(sys.argv)
