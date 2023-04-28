#!/usr/bin/env python
# -*- code: utf-8 -*-
import astropy.io.fits as fits


def compile_as_fitsfile(database, dark_list, flat_list):
  hdul = fits.HDUList([
    fits.PrimaryHDU(),
    fits.BinTableHDU(data=database, name='database')
  ])

  for d in dark_list: hdul.append(d)
  for f in flat_list: hdul.append(f)

  return hdul
