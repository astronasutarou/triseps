# Preparation



## Build Database

First, build a database file using the following command. The first argument is the name of the database. The following arguments are observed FITS files, including science and calibration frames.

``` console
$ cd yyyymmdd
$ tripre database.fits TRCS*.fits
```

The following lines are an example of messages shown in a terminal.

``` console
INFO: no dark frames for 0_00000996_076_2160x1280+60+0.
INFO: generate dark_0_00004992_076_2160x1280+60+0 from 1 frames.
INFO: generate dark_0_00009995_150_2160x1280+60+0 from 1 frames.
INFO: generate dark_0_00059991_300_2160x1280+60+0 from 1 frames.
INFO: no dark frames for 0_00119993_300_2160x1280+60+0.
INFO: generate flat_0_PS1-g2_2160x1280+60+0 from 11 frames.
compile_median_cube: DataWarning: TRCS00220480: skipped due to saturation.
compile_median_cube: DataWarning: TRCS00220540: skipped due to saturation.
compile_median_cube: DataWarning: TRCS00220550: skipped due to saturation.
compile_median_cube: DataWarning: TRCS00220560: skipped due to saturation.
compile_median_cube: DataWarning: TRCS00220570: skipped due to saturation.
```

The `tripre` (TriCCS preparation) command collects useful information from FITS headers and compiles a database FITS file. The database is stored in the second HDU extension (`database`). Details of the database are written in [the database section](../reference/database.md).


### Generate dark frames

Dark frames are automatically generated in the database file by the `tripre` command. The command assumes that the dark frames are uniquely identified by the following keywords:

- `det_id`
- `exptime_single`
- `gain`
- `effective_area`

Thus, the unique key for a dark frame is compiled as follows.

> `dark_${det_id}_${exptime_single in ms}_${gain}_${effective_area}`


### Generate flat frames

Flat frames are automatically generated in the database file by the `tripre` command. The command assumes that the flat frames are uniquely identified by the following keywords:

- `det_id`
- `filter`
- `effective_area`

Thus, the unique key for a dark frame is compiled as follows.

> `dark_${det_id}_${filter}_${effective_area}`

The Kyoto 3.8-m Seiemei Telescope has no dome flat sceen. Twilight sky is generally observed for obtaining flat frames. Some frames are easily saturated since the background level is rapidly changing. `trepre` calculates the 95-percentile count of a frame and omit the frame if the value exceeds the 90-percent of saturation limits. The saturation limits are `13000 ADU` for `gain=x1` and `16383` for the other cases.


## Quick view of the database

The `triview` command is used to show the information collected in the compiled database. Use the `frame` subcommand to list the `OBJECT` frames in the database. Add option `--category DARK` or `--category FLAT` to show the `DARK` or `FLAT` frames, respectively.

``` console
$ triview frame database.fits
  frame_id   observer         timestamp           object  filter     ra         dec      exptime   exptime_single shutter effective_area
------------ -------- -------------------------- -------- ------ ---------- ----------- ---------- -------------- ------- --------------
TRCS00219480 Beniyama 2023-01-31T11:12:29.595752  2023BP6 PS1-g2 02:24:55.9 -15:31:54.3   0.996464       0.996464    open 2160x1280+60+0
TRCS00219490 Beniyama 2023-01-31T11:12:52.250984  2023BP6 PS1-g2 02:24:55.1 -15:31:42.3  29.985432       9.995144    open 2160x1280+60+0
         ...      ...                        ...      ...    ...        ...         ...        ...            ...     ...            ...
TRCS00220450   public 2023-01-31T21:15:56.758135     None PS1-g2 13:38:54.4 +33:18:04.3   9.995144       9.995144    open 2160x1280+60+0
TRCS00220460   public 2023-01-31T21:16:31.134691     None PS1-g2 13:39:29.1 +33:18:03.9  199.90288       9.995144    open 2160x1280+60+0
Length = 96 rows
```

The table can be split by specifying columns via the `--key` option. Adding `--key object` or `-k object`, you can get the table of each object separately.

``` console
$ triview frame database.fits --key object
## 2004BE86
  frame_id   observer         timestamp           object  filter     ra         dec     exptime  exptime_single shutter effective_area
------------ -------- -------------------------- -------- ------ ---------- ----------- -------- -------------- ------- --------------
TRCS00219690 Beniyama 2023-01-31T12:58:51.309296 2004BE86 PS1-g2 09:09:56.0 +05:29:25.3 119.9824        59.9912    open 2160x1280+60+0
TRCS00219700 Beniyama 2023-01-31T13:03:05.396940 2004BE86 PS1-g2 09:09:56.0 +05:29:27.3  299.956        59.9912    open 2160x1280+60+0
TRCS00219710 Beniyama 2023-01-31T13:08:56.642331 2004BE86 PS1-g2 09:09:56.2 +05:29:30.2  299.956        59.9912    open 2160x1280+60+0

## 2008CS1
  frame_id   observer         timestamp           object filter     ra         dec      exptime  exptime_single shutter effective_area
------------ -------- -------------------------- ------- ------ ---------- ----------- --------- -------------- ------- --------------
TRCS00220070 Beniyama 2023-01-31T16:41:18.732098 2008CS1 PS1-g2 11:44:23.7 +09:44:00.0  24.96244       4.992488    open 2160x1280+60+0
TRCS00220080 Beniyama 2023-01-31T16:41:58.615901 2008CS1 PS1-g2 11:44:24.0 +09:44:05.7 299.54928       4.992488    open 2160x1280+60+0
TRCS00220090 Beniyama 2023-01-31T16:47:50.417444 2008CS1 PS1-g2 11:44:26.4 +09:44:54.9 299.54928       4.992488    open 2160x1280+60+0

......
```

Use the `calib` subcommand to list the auto-generated calibration frames.

``` console
$ triview calib database.fits
type n_frame                key
---- ------- ----------------------------------
DARK       1 DARK_0_00004992_076_2160X1280+60+0
DARK       1 DARK_0_00009995_150_2160X1280+60+0
DARK       1 DARK_0_00059991_300_2160X1280+60+0
FLAT       6       FLAT_0_PS1-G2_2160X1280+60+0
```
