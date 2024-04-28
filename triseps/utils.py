#!/usr/bin/env python
# -*- coding: utf-8 -*-
from contextlib import contextmanager
from astropy.table import unique
from datetime import UTC, datetime
import astropy.io.fits as fits
import numpy as np
import re

from .warnings import warn
from .database import effective_area
from .sanity_check import is_saturated


@contextmanager
def timestamp(hdu):
  t_start = datetime.now(UTC)
  hdu.header.add_history(
    f'// processing start at {t_start.isoformat()}')
  try:
    yield hdu
  finally:
    t_end = datetime.now(UTC)
    t_elapse = t_end - t_start
    hdu.header.add_history(
      f'// processing completed at {t_end.isoformat()}')
    hdu.header.add_history(
      f'// elapsed time: {t_elapse.total_seconds()}s')


def pick(database, **options):
  k, v = options.popitem()
  return database[database[k] == v][0]


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
  reg = re.compile(r'(.*_)?(\d+)x(\d+)\+(\d+)\+(\d+)')
  match = reg.match(key).groups()
  ax1, ax2, cx1, cx2 = [int(n) for n in match[1:]]
  if data.ndim == 2:
    data = data[cx2:cx2+ax2, cx1:cx1+ax1]
  elif data.ndim == 3:
    data = data[:, cx2:cx2+ax2, cx1:cx1+ax1]
  else:
    raise RuntimeError('wrong size of the image array: {data.shape}')
  return np.array(data)


def compile_median_cube(hdu_list, name):
    cube = fits.ImageHDU(name=name)
    data = []

    cube.header.add_history('Source Frames:')
    for hdu in hdu_list:
      frame_id = hdu.header['frameid']
      region = effective_area(hdu.header)
      if is_saturated(hdu) is True:
        warn(frame_id, 'skipped due to saturation.')
        continue
      assert hdu.header['naxis'] == 3

      median = np.median(hdu.data, axis=0)
      chopped = chop_reference_pixels(median, region)
      data.append(chopped)
      cube.header.add_history(f'  - {frame_id}')

    cube.data = data
    return cube


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
