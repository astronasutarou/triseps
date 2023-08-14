#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.table import QTable


__header_keywords = {
  'frame_id': 'frameid',
  'exp_id': 'expid',
  'det_id': 'detid',
  'observer': 'observer',
  'proposal_id': 'prop-id',
  'observation_mode': 'obs-mod',
  'observation_date': 'date-obs',
  'object': 'object',
  'ra': 'ra',
  'dec': 'dec',
  'data_type': 'data-typ',
  'timestamp': 'gexp-str',
  'shutter': 'pos-shut',
  'filter': 'filtdisp',
  'naxis1': 'naxis1',
  'naxis2': 'naxis2',
  'naxis3': 'naxis3',
  'exptime': 'exptime',
  'exptime_single': 'exptime1',
  'elapsed_time': 'telapse',
  'frame_interval': 'tframe',
  'gain_config': 'gaincnfg',
  'gain': 'gain',
  'readnoise': 'rdnoise',
}


def effective_area(header):
  ''' Construct Photo-sensitive area indicator '''
  c1 = header['efp-min1'] - 1
  c2 = header['efp-min2'] - 1
  r1 = header['efp-rng1']
  r2 = header['efp-rng2']
  return f'{r1}x{r2}+{c1}+{c2}'


def dome_slit(header):
  ''' Construct Dome Slit status '''
  s1 = header['dom-sstr'].lower()
  s2 = header['dom-send'].lower()
  return s1 if s1 == s2 else 'error'


def build_record(header):
  ''' Extract key information from FITS header

  Arguments:
    header [Header]:
        A FITS header instance.

  Returns:
    A dictionary of the extracted items.
  '''
  rec = {}
  for key, kw in __header_keywords.items():
    rec.update({key: header[kw]})
  rec.update({'dome_slit': dome_slit(header)})
  rec.update({'effective_area': effective_area(header)})

  return rec


def compile_database(hdu_list):
  ''' Compile a database from multiple FITS HDUs '''
  db = []
  for hdu in hdu_list:
    db.append(build_record(hdu.header))
  database = QTable(db)

  return database
