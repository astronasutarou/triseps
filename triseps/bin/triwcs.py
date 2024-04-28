#!/usr/bin/env python
# -*- coding: utf-8 -*-
import astropy.io.fits as fits
import sys

from ..astrometry import solve_field


def main():
  from argparse import ArgumentParser as ap
  parser = ap(
    description='update the wcs info of TriCCS images')

  parser.add_argument(
    'input', type=str,
    help='input FITS image')
  parser.add_argument(
    'output', type=str,
    help='output FITS image')
  parser.add_argument(
    '-f', '--overwrite', action='store_true',
    help='overwrite the output file if exists')
  parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='enable debug messages')

  args = parser.parse_args(sys.argv[1:])

  hdul = fits.open(args.input)
  hdul[0] = solve_field(hdul[0])

  hdul.writeto(args.output, overwrite=args.overwrite)

  if args.verbose: hdul.info()
