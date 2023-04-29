# Preparation



## Build Database

First, build a database file using the following command. The first argument is the name of the database. The following arguments are observed FITS files, including science and calibration frames.

``` console
$ cd data-a
$ tripre database.fits TRCS*0.fits
```

The `tripre` (TriCCS make database) command collects useful information from FITS headers and compiles a database FITS file. The database is stored in the second HDU extension (`database`). Details of the database are written in [the database section](../reference/database.md).


## Generate dark frames

Dark frames are automatically generated in the database file by the `tripre` command.

- `det_id`
- `exptime_single`
- `gain`
- `effective_area`


## Generate flat frames

Flat frames are automatically generated in the database file by the `tripre` command.

- `det_id`
- `filter`
- `effective_area`
