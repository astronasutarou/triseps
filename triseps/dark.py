#!/usr/bin/env python
# -*- coding: utf-8 -*-
import astropy.io.fits as fits
import numpy as np

from .warnings import eprint
from .utils import chop_reference_pixels, split_dataset, pickup_data


__unique_keys = (
  'exptime_single',
  'gain',
  'effective_area',
)


def compile_darkframe(key, hdu_list):
  dark_hdu = fits.ImageHDU(name=f'dark_{key}')
  data = []

  for hdu in hdu_list:
    frame_id = hdu.header['frameid']
    dark_hdu.header.add_history(f'{frame_id}')
    assert hdu.header['naxis'] == 3
    median = np.median(hdu.data, axis=0)
    chopped = chop_reference_pixels(median, key)
    data.append(chopped)

  dark_hdu.data = np.mean(np.array(data), axis=0)
  return dark_hdu


def generate_darkframe(hdu_list, database):
  dark_list = []

  for calib_id, subset in split_dataset(database, __unique_keys):
    db_dark = subset[subset['data_type'] == 'DARK']
    hdu_dark = pickup_data(hdu_list, frameid=db_dark['frame_id'])

    if len(db_dark) == 0:
      eprint(f'Caution: no DARK frames for {calib_id}.')
      continue

    eprint(f'Generate dark_{calib_id} from {len(db_dark)} frames.')
    dark_list.append(compile_darkframe(calib_id, hdu_dark))

  return dark_list
