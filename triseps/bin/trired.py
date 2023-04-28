#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable
import astropy.io.fits as fits
import sys

from ..utils import pick, chop_reference_pixels, timestamp
from ..dark import estimate_darkframe
from ..flat import estimate_flatframe


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
  area = pick(db, frame_id=frame_id)['effective_area']
  data = chop_reference_pixels(input.data, area)

  output = fits.PrimaryHDU(data=data, header=input.header)

  dark_id = estimate_darkframe(db, frame_id)
  dark_hdu = hdul[dark_id]

  flat_id = estimate_flatframe(db, frame_id)
  flat_hdu = hdul[flat_id]

  with timestamp(output):
    output.data -= dark_hdu.data
    output.header.add_history(f'dark current subtracted with "{dark_id}".')
    output.data /= flat_hdu.data
    output.header.add_history(f'flat frame corrected with "{dark_id}".')

  output.writeto(args.output, overwrite=args.overwrite)
