# Preparation



## Build Database

First, build a database file using the following command. The first argument is the name of the database. The following arguments are observed FITS files, including science and calibration frames.

``` console
$ cd data-a
$ trimkdb database.fits TRCS*0.fits
```

The `trimkdb` (TriCCS make database) command collects useful information from FITS headers and compiles a database FITS file. The database is stored in the second HDU extension (`db`). Details of the database are written in [the database section](./database.md).


## Generate dark frames

Dark frames are automatically generated in the database file by the `trimkdb` command.


## Generate flat frames
