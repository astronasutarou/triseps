#!/usr/bin/env python
# -*- coding: utf-8 -*-
import astropy.io.fits as fits
import numpy as np

from .utils import chop_reference_pixels


__unique_keys = (
  'exptime_single',
  'gain',
  'effective_area',
)

__display_keys = (
  'data_type',
  'frame_id',
  'observer',
  'observation_date',
  'proposal_id',
  'object',
  'exptime_single',
  'gain',
  'shutter',
  'dome_slit',
  'effective_area',
)


def generate_key(setup):
  texp, gain, area = setup
  return f't{texp*1000:08.0f}_g{gain*100:04.0f}_{area}'


def generate_darkframe(key, dark):
  ihdu = fits.ImageHDU()
  data = []
  for d in dark:
    frame_id = d['frame_id']
    filename = f'{frame_id}.fits'
    ihdu.header.add_history(f'{filename}')
    with fits.open(filename) as hdul:
      assert hdul[0].header['naxis'] == 3
      median = np.median(hdul[0].data, axis=0)
      chopped = chop_reference_pixels(median, key)
      data.append(chopped)
  ihdu.data = np.mean(np.array(data), axis=0)
  return ihdu


def generate_darkframe(hdu_list, database):
  for key, subset in split_dataset(database):
    dark = subset[subset['data_type'] == 'DARK']
    if len(dark) == 0:
      eprint(f'Caution: no DARK frames for {key}.')
      continue
    print(f'Generate dark_{key} from {len(dark)} frames.')

    phdu = generate_darkframe(key, dark)

    filename = f'dark_{key}.fits'
    phdu.writeto(filename, overwrite=args.overwrite)
