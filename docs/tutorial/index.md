# Overview of TriCCS data reduction

In this tutorial, we assume that obtained data are stored as follows. The FITS files obtained by ARM-A, -B, and -C are respectively stored in `data-a`, `data-b`, and `data-c`. Each directory contains scientific and calibration frames.


``` python
yyyymmdd
├─data-a  # ARM-A
│   ├─ TRCSnnnnnnn0.fits
│   ├─ TRCSnnnnnnn0.fits
│   └─ ...
├─data-b  # ARM-B
│   ├─ TRCSnnnnnnn1.fits
│   ├─ TRCSnnnnnnn1.fits
│   └─ ...
└─data-c  # ARM-C
     ├─ TRCSnnnnnnn2.fits
     ├─ TRCSnnnnnnn2.fits
     └─ ...
```

1. [Preparation](./preparation.md)
1. [Basic calibration](./reduction.md)
1. Astrometric calibration
1. Photometry
1. Photometric calibration
