#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import unique
import re


def generate_calib_id(unique_key):
  def convert(key, value):
    if key in ('exptime_single'):
      return f'{value * 1000:08.0f}'
    elif key in ('gain'):
      return f'{value * 100:03.0f}'
    else:
      return str(value)

  def items(row):
    return zip(row.keys(), row.values())

  return '_'.join([convert(k, v) for k, v in items(unique_key)])


def chop_reference_pixels(data, key):
  reg = re.compile(r'.*_(\d+)x(\d+)\+(\d+)\+(\d+)')
  res = reg.match(key)
  if res is not None:
    ax1, ax2, cx1, cx2 = [int(n) for n in res.groups()]
    data = data[cx2:cx2+ax2, cx1:cx1+ax1]
  return data


def split_dataset(database, keys):
  ''' Split the database into subset by unique keys. '''
  unique_setups = unique(database, keys)[keys]
  for setup in unique_setups:
    calib_id = generate_calib_id(setup)
    yield calib_id, database[database[keys] == setup]


def pickup_data(hdu_list, **options):
  res = []
  for hdu in hdu_list:
    check = [hdu.header[k] in v for k, v in options.items()]
    if all(check):
        res.append(hdu)
  return res
