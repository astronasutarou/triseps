#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np


def saturation_counts(gain_config, margin=0.9):
  if gain_config == 'x1':
    return 13000 * margin
  else:
    return 16383 * margin


def is_saturated(hdu, percentile=95):
  gain_config = hdu.header['gaincnfg']
  limit = saturation_counts(gain_config)
  return bool(np.percentile(hdu.data, percentile) > limit)
