#!/usr/bin/env python
# -*- code: utf-8 -*-
from astropy.table import QTable
import astropy.io.fits as fits

from .database import header_keywords


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
    for key, kw in header_keywords.items():
        rec.update({key: header[kw]})
    rec.update({'dome_slit': dome_slit(header)})
    rec.update({'effective_area': effective_area(header)})

    return rec


def compile_database(hdu_list):
    db = []
    for hdu in hdu_list:
        db.append(build_record(hdu.header))
    database = QTable(db)

    return database


def write_as_fitsfile(filename, database, overwrite=False):
    hdul = fits.HDUList([
        fits.PrimaryHDU(),
        fits.BinTableHDU(data=database, name='database')
    ])
    hdul.writeto(filename, overwrite=overwrite)
