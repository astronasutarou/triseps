#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import unique
import re


def chop_reference_pixels(data, key):
  reg = re.compile(r'.*_?(\d+)x(\d+)\+(\d+)\+(\d+)')
  res = reg.match(key)
  if res is not None:
    ax1, ax2, cx1, cx2 = [int(n) for n in res.groups()]
    data = data[cx2:cx2+ax2, cx1:cx1+ax1]
  return data


def split_dataset(database, keys):
  ''' Split the database into subset by unique keys. '''
  unique_setups = unique(database, keys)[keys]
  for setup in unique_setups:
    key = generate_key(setup)
    yield key, database[database[keys] == setup]
