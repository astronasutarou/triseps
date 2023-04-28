#!/usr/bin/env python
# -*- coding: utf-8 -*-
import astropy.io.fits as fits
import sys

from ..assertion import quick_sanity_check
from ..database import compile_database
from ..dark import generate_darkframe
from ..flat import generate_flatframe
from ..compile import compile_as_fitsfile


def main():
  from argparse import ArgumentParser as ap
  parser = ap(
    description='compile TriCCS calibration database')

  parser.add_argument(
    'output', type=str,
    help='output filename')
  parser.add_argument(
    'fits', nargs='+', type=str,
    help='list of input FITS files')
  parser.add_argument(
    '-f', '--overwrite', action='store_true',
    help='overwrite the output file if exists')
  parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='enable debug messages')

  args = parser.parse_args(sys.argv[1:])

  hdu_list = list()
  for f in args.fits:
    hdu_list.append(fits.open(f)[0])

  database = compile_database(hdu_list)

  if args.verbose:
    print(database)

  quick_sanity_check(database)

  dark_list = generate_darkframe(hdu_list, database)
  flat_list = generate_flatframe(hdu_list, database)

  hdul = compile_as_fitsfile(database, dark_list, flat_list)
  hdul.writeto(args.output, overwrite=args.overwrite)
