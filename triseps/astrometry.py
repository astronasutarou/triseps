#!/usr/bin/env python
# -*- coding: utf-8 -*-
from astropy.wcs import WCS as wcsobj
from subprocess import CalledProcessError
from subprocess import check_output, check_call
import numpy as np
import astropy.io.fits as fits
import os, shutil, tempfile, warnings

from .warnings import eprint

__DEBUG__ = False

try:
  __solve_field = check_output(['which', 'solve-field']).strip()
except CalledProcessError as e:
  __solve_field = ''
  eprint(f'Cannot find "solve-field": {str(e)}')

__keywords_naxis3 = (
  'NAXIS3', 'CTYPE3', 'CRPIX3', 'CRVAL3', 'CUNIT3',
  'CD1_3', 'CD2_3', 'CD3_3', 'CD3_2', 'CD3_1',
)


class wcs_directory(object):
  ''' create/delete temporary directory for astrometry. '''
  def __enter__(self):
    self.cwd = os.getcwd()
    self.dirname = tempfile.mkdtemp(prefix='wcs.', dir=self.cwd)
    if __DEBUG__: eprint(f'{self.dirname} created')
    os.chdir(self.dirname)
    if __DEBUG__: eprint(f'change directory to {self.dirname}')

  def __exit__(self, type, value, traceback):
    os.chdir(self.cwd)
    if __DEBUG__: eprint(f'change directory to {self.cwd}')
    if not __DEBUG__:
      shutil.rmtree(self.dirname)
    else:
      eprint(f'{self.dirname} left intact')


def get_astrometry_scale(header):
  ''' calculate index scales for astrometry.net

  Parameters:
    header (Header): fits header object

  Return:
    floor: lower bound of image scale in arcmin
    floor: upper bound of image scale in arcmin
  '''
  nx1 = header.get('NAXIS1')
  nx2 = header.get('NAXIS2')
  pxs = np.abs(header.get('CD1_1') * 60.0)
  s, d = np.min([nx1, nx2]), nx1+nx2
  return s * pxs, d * pxs


def drop_naxis3_keywords(header):
  ''' remove NAXIS3 keywords from a fits header

  This function drops NAXIS3 keywords from a header object.
  This operation is destructive. Note that a header object is altered inplace.

  Paramters:
    header (Header): a fits header object

  Return:
    Header: a FITS header object without NAXIS3 keywords
  '''
  header.set('NAXIS', 2)
  for key in __keywords_naxis3: header.remove(key, ignore_missing=True)
  return header


def wcs_without_naxis3(header):
  ''' drop naxis3 keywords from header

  Paramters:
    header (Header): fits header object

  Return:
    WCSObj: a wcs object without NAXIS3 keywords
  '''
  with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    hdr = header.copy()
    drop_naxis3_keywords(hdr)
    return wcsobj(header=hdr)


def wcspaste(src, dst):
  ''' copy wcs information

  Paramters:
    src (Header): a header object with source wcs information
    dst (Header): a header object of destination

  Return:
    Header: an updated Header object
  '''
  keywords = [
    'CTYPE1', 'CTYPE2', 'CRVAL1', 'CRVAL2', 'CRPIX1', 'CRPIX2',
    'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2', 'LONPOLE', 'LATPOLE', ]
  sipA_keywords = [
    'A_ORDER', 'A_0_0', 'A_0_1', 'A_0_2', 'A_1_0', 'A_1_1', 'A_2_0',
    'AP_ORDER', 'AP_0_0', 'AP_0_1', 'AP_0_2', 'AP_1_0', 'AP_1_1', 'AP_2_0', ]
  sipB_keywords = [
    'B_ORDER', 'B_0_0', 'B_0_1', 'B_0_2', 'B_1_0', 'B_1_1', 'B_2_0',
    'BP_ORDER', 'BP_0_0', 'BP_0_1', 'BP_0_2', 'BP_1_0', 'BP_1_1', 'BP_2_0', ]
  for key in keywords: dst.header[key] = src.header[key]
  if 'SIP' in src.header['CTYPE1']:
    for key in sipA_keywords: dst.header[key] = src.header.get(key, 0.0)
  if 'SIP' in src.header['CTYPE2']:
    for key in sipB_keywords: dst.header[key] = src.header.get(key, 0.0)

  return dst


def solve_field(src, verbose=False):
  ''' calibrate astrometry infomation

  Parameters:
    src     (ImageHDU): original ImageHDU object

  Return:
    ImageHDU: a FITS ImageHDU with the updated WCS information
  '''
  frame_id = src.header.get('FRAMEID')
  filename = '{}.fits'.format(frame_id)
  wcsfile  = '{}.wcs'.format(frame_id)
  axyfile  = '{}.axy'.format(frame_id)

  with wcs_directory():
    naxis2, naxis1 = src.header.get('NAXIS2'), src.header.get('NAXIS1')
    wcs_src = wcs_without_naxis3(header=src.header)
    ra, dec = wcs_src.all_pix2world(((naxis1/2.0, naxis2/2.0),), 1)[0]

    if src.data.ndim == 3:
      # use the first frame in case of non-sidereal tracking
      img = src.data[0]
    else:
      img = src.data
    wcs = fits.PrimaryHDU(data=img)
    wcs.writeto('{}.fits'.format(frame_id))
    scale_low, scale_high = get_astrometry_scale(src.header)
    cmd = [__solve_field, '--no-plots',
           '--no-tweak', '--parity', 'pos',
           '--depth', '20,40,80,160,320,640', '--objs', '400',
           '--ra', str(ra), '--dec', str(dec), '--radius', '1.0',
           '--scale-low', str(scale_low), '--scale-high', str(scale_high),
           '--scale-units', 'arcminwidth', '--axy', axyfile,
           '--new-fits', 'none', '--wcs', wcsfile, filename]

    if verbose is False:
      with open(os.devnull, 'w') as devnull:
        check_call(cmd, stdout=devnull, stderr=devnull)
    else:
      check_call(cmd)

    cmd = [__solve_field, '--no-plots',
           '--continue', '--parity', 'pos',
           '--ra', str(ra), '--dec', str(dec), '--radius', '1.0',
           '--pixel-error', '0.2', '--verify', wcsfile,
           '--new-fits', 'none', '--wcs', wcsfile, axyfile]

    if verbose is False:
      with open(os.devnull, 'w') as devnull:
        check_call(cmd, stdout=devnull, stderr=devnull)
    else:
      check_call(cmd)

    wcs = fits.open(wcsfile)[0]

    src.header['WCSVALID'] = True
    src.header['WCSORIG']  = 'Gaia EDR3'

    wcspaste(wcs, src)
    for h in wcs.header['HISTORY']:
      src.header.add_history(f'[wcs] {h}')

    src.header.add_comment(
      '---------- ASTROMETRY SECTION', before='HISTORY')
    for c in wcs.header['COMMENT']:
      src.header.add_comment(c)

    return src
