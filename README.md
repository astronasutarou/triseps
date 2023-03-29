# triseps - SEPs for TriCCS

This repository provides a suite of programs for photometric measurements of data obtained with [TriCCS][triccs]. TriCCS is a tri-color simultaneous camera and spectrograph attached to [Seimei Telescope][seimei]. Three CMOS sensors are equipped with TriCCS. The cameras share the same field-of-view. Thanks to the CMOS sensors, TriCCS is able to continuously obtain multi-color images without dead time.

The following functions will be provided in this repository:

[ ] basic calibration
    [ ] dark subtraction
    [ ] flat fielding
- basic wcs calibration
- photometry of video data (three-dimensional FITS files)
    - aperture photometry
    - PSF photometry
- photometric calibration
- simple lightcurve analysis

[triccs]: http://www.o.kwasan.kyoto-u.ac.jp/inst/triccs/
[seimei]: http://seimei.nao.ac.jp/
