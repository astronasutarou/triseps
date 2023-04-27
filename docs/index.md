# triseps - SEPs for TriCCS
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Documentation Status](https://readthedocs.org/projects/triseps/badge/?version=latest)](https://triseps.readthedocs.io/en/latest/?badge=latest)

This repository provides a suite of programs for photometric measurements of data obtained with [TriCCS][triccs]. TriCCS is a tri-color simultaneous camera and spectrograph attached to [Seimei Telescope][seimei]. Three CMOS sensors are equipped with TriCCS. The cameras share the same field-of-view. Thanks to the CMOS sensors, TriCCS can continuously obtain multi-color images without dead time.


## Install
The package will be available in the PyPi repository. You can install the package by typing the following command.

``` console
$ python -m pip install \
    git+https://bitbucket.org/ryou_ohsawa/triseps/src/master/
```

Otherwise, you can clone the [repository][bitbucket] and install directly using the following command.

``` console
$ python setup.py install
```

## Contents

The following functions will be provided in this repository:

- basic calibration
    - dark subtraction
    - flat fielding
- basic astrometric calibration
- photometry of video data (three-dimensional FITS files)
    - aperture photometry
    - PSF photometry
- photometric calibration
- simple lightcurve analysis

[triccs]: http://www.o.kwasan.kyoto-u.ac.jp/inst/triccs/
[seimei]: http://seimei.nao.ac.jp/
[bitbucket]: https://bitbucket.org/ryou_ohsawa/triseps/src/master/
[pypi]: https://pypi.org/
