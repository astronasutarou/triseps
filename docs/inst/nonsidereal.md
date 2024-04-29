# Non-sidereal tracking

The Seiemi telescope offers the non-sidereal tracking mode, which is generally used in observations of solar system bodies. You need to prepare tracking files to initiate the non-sidereal tracking.


## Tracking File

A dedicated script is available in the observer console. If you want to generate a tracking file for Ceres, type the following line in the observer console.

``` shell
$ fromHorizon.rb -a Ceres
```

Then, a tracking file is generated in `~/object/Track/`. The filename of the tracking file is given as follows:

> `${object_id}_${date:yyyymmdd}${time:hhmmss}_tk.dat`

Note that the script depends on the Horizons System operated by the NASA/JPL. You can not generate tracking files for object that are not registered in the Horizons System.


### Format

The first lines of the tracking file contains an object name and the time range. The format is as follows:

```
${object}, ${start_time} - ${end_time}
```

- `${object}` contains the name of the tracking target.
- `${start_time}` is the start time of the tracking file in the `yyyy-mm-dd HH:MM:SS` format.
- `${end_time}` is the end time of the tracking file in the `yyyy-mm-dd HH:MM:SS` format.

The following lines contain the ephemeris of the target. The format is described below. Note that each line _starts with a blank_ and _ends with a comma_.

```
 ${calendar_date},${julian_date},${sun},${moon},${ra},${dec},${azimuth},${elevation},
```

- `${calendar_date}` is the time in UTC in the `yyyy-mon-dd HH:MM:SS` format. The `mon` is the shortened month name like `Jan`, `Feb`, and `Mar`.
- `${julian_date}` is the Julian date in UTC.
- `${sun}` is the solar-presence condition code.
- `${moon}` is the lunar-presence condition code.
- `${ra}` is the astrometric right ascension of the target in the `HH MM SS.ff` format.
- `${dec}` is the astrometric declination of the target in the `sDD MM SS.f` format.
- `${azimuth}` is the apparent azimuth angle of the target in the decimal format.
- `${elevation}` is the apparent elevation angle of the target in the decimal format.

A sample of the tracking file is presented below. Note that the lines with the elevation below 20 degrees are omitted.

```
523608, 2023-02-01 07:00:00 - 2023-02-01 22:00:00
 2023-Feb-01 08:33:00,2459976.856250000,*,m,06 51 48.33,+06 40 31.3,95.888107,20.106322,
 2023-Feb-01 08:34:00,2459976.856944445,*,m,06 51 48.28,+06 40 32.0,96.038198,20.311870,
 2023-Feb-01 08:35:00,2459976.857638889,*,m,06 51 48.24,+06 40 32.7,96.188576,20.517361,
 2023-Feb-01 08:36:00,2459976.858333333,*,m,06 51 48.20,+06 40 33.4,96.339248,20.722793,
 2023-Feb-01 08:37:00,2459976.859027778,*,m,06 51 48.15,+06 40 34.0,96.490218,20.928166,
 2023-Feb-01 08:38:00,2459976.859722222,C,m,06 51 48.11,+06 40 34.7,96.641490,21.133477,
 2023-Feb-01 08:39:00,2459976.860416667,C,m,06 51 48.07,+06 40 35.4,96.793070,21.338725,
 2023-Feb-01 08:40:00,2459976.861111111,C,m,06 51 48.02,+06 40 36.1,96.944963,21.543909,
 2023-Feb-01 08:41:00,2459976.861805555,C,m,06 51 47.98,+06 40 36.7,97.097175,21.749027,
```


Please follow the Seimei Observer's wiki (SeimeiWiki) for more detailed information.[^wiki]

[^wiki]: Note that the SeimeiWiki is written in Japanese and password-protected. Only observers can access the wiki.
