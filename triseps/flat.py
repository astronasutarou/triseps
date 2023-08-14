#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np

from .warnings import eprint
from .utils import pick, pickup_data
from .utils import compile_median_cube, split_dataset, generate_calib_id


__unique_keys = (
  'det_id',
  'filter',
  'effective_area',
)


def estimate_flatframe(database, frame_id):
  row = pick(database, frame_id=frame_id)
  calib_id = generate_calib_id(row[__unique_keys])
  return f'flat_{calib_id}'


def compile_flatframe(key, hdu_list):
  flat_hdu = compile_median_cube(hdu_list, name=f'flat_{key}')

  flat_hdu.header['CATEGORY'] = 'CALIBRATION'
  flat_hdu.header['OBJECT'] = 'FLAT'
  flat_hdu.header['NFRAME'] = flat_hdu.data.shape[0]

  data = np.sum(flat_hdu.data, axis=0)
  flat_hdu.data = data / np.median(data)
  return flat_hdu


def generate_flatframe(hdu_list, database):
  flat_list = []

  for calib_id, subset in split_dataset(database, __unique_keys):
    db_flat = subset[subset['data_type'] == 'FLAT']
    hdu_flat = pickup_data(hdu_list, frameid=db_flat['frame_id'])

    if len(db_flat) == 0:
      eprint(f'INFO: no flat frames for {calib_id}.')
      continue

    eprint(f'INFO: generate flat_{calib_id} from {len(db_flat)} frames.')
    flat_list.append(compile_flatframe(calib_id, hdu_flat))

  return flat_list
