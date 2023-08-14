# Preparation



## Build Database

First, build a database file using the following command. The first argument is the name of the database. The following arguments are observed FITS files, including science and calibration frames.

``` console
$ cd data-a
$ tripre database.fits TRCS*0.fits
```

The `tripre` (TriCCS preparation) command collects useful information from FITS headers and compiles a database FITS file. The database is stored in the second HDU extension (`database`). Details of the database are written in [the database section](../reference/database.md).


## Generate dark frames

Dark frames are automatically generated in the database file by the `tripre` command. The command assumes that the dark frames are uniquely identified by the following keywords:

- `det_id`
- `exptime_single`
- `gain`
- `effective_area`

Thus, the unique key for a dark frame is compiled as follows.

> `dark_${det_id}_${exptime_single in ms}_${gain}_${effective_area}`


## Generate flat frames

Flat frames are automatically generated in the database file by the `tripre` command. The command assumes that the flat frames are uniquely identified by the following keywords:

- `det_id`
- `filter`
- `effective_area`

Thus, the unique key for a dark frame is compiled as follows.

> `dark_${det_id}_${filter}_${effective_area}`

The Kyoto 3.8-m Seiemei Telescope has no dome flat sceen. Twilight sky is generally observed for obtaining flat frames. Some frames are easily saturated since the background level is rapidly changing. `trepre` calculates the 95-percentile count of a frame and omit the frame if the value exceeds the 90-percent of saturation limits. The saturation limits are `13000 ADU` for `gain=x1` and `16383` for the other cases.
