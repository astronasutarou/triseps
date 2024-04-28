#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable
import astropy.io.fits as fits
import sys

from ..utils import split_dataset


def display_frame(database, verbose=False):
  ''' Display the frames in the database '''
  columns = (
    'frame_id', 'observer', 'timestamp',
    'object', 'filter', 'ra', 'dec',
    'exptime', 'exptime_single',
    'shutter', 'effective_area'
  ) if verbose is False else database.colnames

  print(database[columns])
  print('')


def setup_frame_parser(parser):
  ''' Setup argument parser for "frame" command '''
  parser.add_argument(
    'database', type=str,
    help='calibration database file')
  parser.add_argument(
    '-c', '--category', type=str, action='store', default='OBJECT',
    choices=('OBJECT', 'DARK', 'FLAT', 'ALL'),
    help='specify "data_type"')
  parser.add_argument(
    '-k', '--key', type=str, nargs='+', action='store',
    help='display separately by keys')
  parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='enable debug messages')

  def handler_frame(args):
      db = QTable.read(args.database)

      if args.category != 'ALL':
        db = db[db['data_type'] == args.category]

      if args.key is None:
        display_frame(db, verbose=args.verbose)
      else:
        for k, sub in split_dataset(db, args.key):
          print(f'## {k}')
          display_frame(sub, verbose=args.verbose)

  parser.set_defaults(handler=handler_frame)


def setup_calib_parser(parser):
  ''' Setup argument parser for "calib" command '''
  parser.add_argument(
    'database', type=str,
    help='calibration database file')

  def handler_calib(args):
    db = []
    hdul = fits.open(args.database)

    for hdu in hdul:
      header = hdu.header
      if header.get('CATEGORY') == 'CALIBRATION':
        db.append({
          'type': header.get('OBJECT', 'ERROR'),
          'n_frame': header.get('NFRAME', -1),
          'key': header.get('EXTNAME', 'ERROR'),
        })
    db = QTable(db)
    print(db)

  parser.set_defaults(handler=handler_calib)


def setup_extract_parser(parser):
  ''' Setup argument parser for "extract" command '''
  parser.add_argument(
    'database', type=str,
    help='calibration database file')
  parser.add_argument(
    'key', type=str,
    help='calibration file key')
  parser.add_argument(
    'output', type=str,
    help='output filename')
  parser.add_argument(
    '-f', '--overwrite', action='store_true',
    help='overwrite the output file if exists')

  def handler_extract(args):
    hdul = fits.open(args.database)

    hdu = hdul[args.key]
    hdu.writeto(args.output, overwrite=args.overwrite)

  parser.set_defaults(handler=handler_extract)


def main():
  from argparse import ArgumentParser as ap
  parser = ap(
    description='view TriCCS calibration database')

  subparser = parser.add_subparsers(required=True)
  frame = subparser.add_parser(
    'frame', help='display the source frames')
  calib = subparser.add_parser(
    'calib', help='display the generated calibration frames')
  extract = subparser.add_parser(
    'extract', help='extract a calibration frame bye key')

  setup_frame_parser(frame)
  setup_calib_parser(calib)
  setup_extract_parser(extract)

  args = parser.parse_args(sys.argv[1:])

  if hasattr(args, 'handler'):
    args.handler(args)
  else:
    parser.print_help()
