#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable
import sys

from ..utils import split_dataset


def display(database, verbose=False):
  columns = (
    'frame_id', 'observer', 'timestamp',
    'object', 'filter', 'ra', 'dec',
    'exptime', 'exptime_single',
    'shutter', 'effective_area'
  ) if verbose is False else database.colnames

  print(database[columns])
  print('')


def main():
  from argparse import ArgumentParser as ap
  parser = ap(
    description='view TriCCS calibration database')

  parser.add_argument(
    'database', type=str,
    help='calibratoin database file')
  parser.add_argument(
    '--category', type=str, action='store',
    choices=('OBJECT', 'DARK', 'FLAT'),
    help='specify "data_type"')
  parser.add_argument(
    '-k', '--key', type=str, nargs='+', action='store',
    help='display separately by keys')
  parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='enable debug messages')

  args = parser.parse_args(sys.argv[1:])

  db = QTable.read(args.database)

  if args.category is not None:
    db = db[db['data_type'] == args.category]

  if args.key is None:
    display(db, verbose=args.verbose)
  else:
    for k, sub in split_dataset(db, args.key):
      print(f'## {k}')
      display(sub, verbose=args.verbose)
