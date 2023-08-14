#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np

from .warnings import eprint
from .utils import pick, pickup_data
from .utils import compile_median_cube, split_dataset, generate_calib_id


__unique_keys = (
  'det_id',
  'exptime_single',
  'gain',
  'effective_area',
)


def estimate_darkframe(database, frame_id):
  row = pick(database, frame_id=frame_id)
  calib_id = generate_calib_id(row[__unique_keys])
  return f'dark_{calib_id}'


def compile_darkframe(key, hdu_list):
  dark_hdu = compile_median_cube(hdu_list, name=f'dark_{key}')

  dark_hdu.header['CATEGORY'] = 'CALIBRATION'
  dark_hdu.header['OBJECT'] = 'DARK'
  dark_hdu.header['NFRAME'] = dark_hdu.data.shape[0]

  dark_hdu.data = np.mean(dark_hdu.data, axis=0)
  return dark_hdu


def generate_darkframe(hdu_list, database):
  dark_list = []

  for calib_id, subset in split_dataset(database, __unique_keys):
    db_dark = subset[subset['data_type'] == 'DARK']
    hdu_dark = pickup_data(hdu_list, frameid=db_dark['frame_id'])

    if len(db_dark) == 0:
      eprint(f'INFO: no dark frames for {calib_id}.')
      continue

    eprint(f'INFO: generate dark_{calib_id} from {len(db_dark)} frames.')
    dark_list.append(compile_darkframe(calib_id, hdu_dark))

  return dark_list
