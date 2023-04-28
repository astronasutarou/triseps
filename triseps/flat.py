#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable, unique
import astropy.io.fits as fits
import numpy as np
import sys, re

from .warnings import eprint


__unique_keys = (
  'filter',
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
  filter, area = setup
  return f'{filter}_{area}'


def chop_reference_pixels(data, key):
  reg = re.compile(r'.*_(\d+)x(\d+)\+(\d+)\+(\d+)')
  res = reg.match(key)
  if res is not None:
    ax1, ax2, cx1, cx2 = [int(n) for n in res.groups()]
    data = data[cx2:cx2+ax2, cx1:cx1+ax1]
  return data


def generate_flatframe(key, flat):
  phdu = fits.PrimaryHDU()
  data = []
  for d in flat:
    frame_id = d['frame_id']
    filename = f'{frame_id}.fits'
    phdu.header.add_history(f'{filename}')
    with fits.open(filename) as hdul:
      assert hdul[0].header['naxis'] == 3
      median = np.median(hdul[0].data, axis=0)
      chopped = chop_reference_pixels(median, key)
      data.append(chopped)
  data = np.sum(np.array(data), axis=0)
  phdu.data = np.array(data) / np.median(data)
  return phdu


def main(argv):
  from argparse import ArgumentParser as ap
  parser = ap(description='generate flat frame')
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
    flat = subset[subset['data_type'] == 'FLAT']
    if len(flat) == 0:
      eprint(f'Caution: no flat frames for {key}.')
      continue
    print(f'Generate flat_{key} from {len(flat)} frames.')

    phdu = generate_flatframe(key, flat)

    filename = f'flat_{key}.fits'
    phdu.writeto(filename, overwrite=args.overwrite)


if __name__ == '__main__':
  main(sys.argv)
