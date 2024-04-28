#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable
from astropy.stats import sigma_clipped_stats
import astropy.io.fits as fits
import sys

from ..utils import pick, chop_reference_pixels, timestamp
from ..dark import estimate_darkframe
from ..flat import estimate_flatframe
from ..astrometry import solve_field
from ..warnings import eprint


def main():
  from argparse import ArgumentParser as ap
  parser = ap(
    description='reduce TriCCS data usnig calibration database')

  parser.add_argument(
    'database', type=str,
    help='calibratoin database file')
  parser.add_argument(
    'fits', type=str,
    help='input FITS file')
  parser.add_argument(
    'output', type=str,
    help='output FITS file')
  parser.add_argument(
    '-w', '--wcs', action='store_true',
    help='calibrate the wcs info using astrometry.net')
  parser.add_argument(
    '-q', '--ql', action='store_true',
    help='generate a stacked image cube for quick look')
  parser.add_argument(
    '-s', '--stack', action='store_true',
    help='generate a stacked image')
  parser.add_argument(
    '--track', action='store', type=str,
    help='tracking file')
  parser.add_argument(
    '-f', '--overwrite', action='store_true',
    help='overwrite the output file if exists')
  parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='enable debug messages')

  args = parser.parse_args(sys.argv[1:])

  db = QTable.read(args.database)
  hdul = fits.open(args.database)

  input = fits.open(args.fits)[0]
  frame_id = input.header['frameid']

  output = fits.PrimaryHDU(data=None, header=input.header)

  dark_id = estimate_darkframe(db, frame_id)
  dark_hdu = hdul[dark_id]

  flat_id = estimate_flatframe(db, frame_id)
  flat_hdu = hdul[flat_id]

  with timestamp(output):
    def hist(message):
      output.header.add_history(message)
      eprint(f'INFO: {message}')

    area = pick(db, frame_id=frame_id)['effective_area']
    output.data = chop_reference_pixels(input.data, area)
    hist(f'photo-sensitive area {area} is extracted.')

    output.data -= dark_hdu.data
    hist(f'dark current subtracted with {dark_id}.')

    output.data /= flat_hdu.data
    hist(f'flat frame corrected with {flat_id}.')

    if args.wcs is True:
      output = solve_field(output, verbose=args.verbose)

    if args.ql is True:
      assert output.data.ndim == 3
      output.data = output.data.mean(axis=0)
      hist('image cube is stacked for quick look.')
    elif args.stack is True:
      assert output.data.ndim == 3
      if args.track is None:
        stats = sigma_clipped_stats(output.data, axis=0)
        output.data = stats[0]
        hist('3-sigma clipped mean is calculated.')
      else:
        pass

  output.writeto(args.output, overwrite=args.overwrite)
