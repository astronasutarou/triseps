#!/usr/bin/env python
# -*- coding: utf-8 -*-
import astropy.io.fits as fits
import numpy as np

from .warnings import eprint
from .utils import chop_reference_pixels, split_dataset, pickup_data


__unique_keys = (
  'filter',
  'effective_area',
)


def compile_flatframe(key, hdu_list):
  phdu = fits.ImageHDU(name=f'flat_{key}')
  data = []

  for hdu in hdu_list:
    frame_id = hdu.header['frameid']
    phdu.header.add_history(f'{frame_id}')
    assert hdu.header['naxis'] == 3
    median = np.median(hdu.data, axis=0)
    chopped = chop_reference_pixels(median, key)
    data.append(chopped)
  data = np.sum(np.array(data), axis=0)
  phdu.data = np.array(data) / np.median(data)
  return phdu


def generate_flatframe(hdu_list, database):
  flat_list = []

  for calib_id, subset in split_dataset(database, __unique_keys):
    db_flat = subset[subset['data_type'] == 'FLAT']
    hdu_flat = pickup_data(hdu_list, frameid=db_flat['frame_id'])

    if len(db_flat) == 0:
      eprint(f'Caution: no flat frames for {calib_id}.')
      continue

    print(f'Generate flat_{calib_id} from {len(db_flat)} frames.')
    flat_list.append(compile_flatframe(calib_id, hdu_flat))

  return flat_list
