#!/usr/bin/env python
# -*- code: utf-8 -*-
from .warnings import DataWarning, warn


__all__ = [
    'quick_sanity_check',
]


def quick_sanity_check(database):
    check_dark_frame(database)
    check_flat_frame(database)
    check_object_frame(database)


def check_dark_frame(database):
    msg = 'data-type is "DARK", but obtained with a wrong shutter status.'
    dark = database[database['data_type'] == 'DARK']
    flag = dark['shutter'] != 'close'
    for d in dark[flag]:
        warn(d['frame_id'], msg, DataWarning)


def check_flat_frame(database):
    msg = 'data-type is "FLAT", but obtained with a wrong shutter status.'
    flat = database[database['data_type'] == 'FLAT']
    flag = flat['shutter'] != 'open'
    for d in flat[flag]:
        warn(d['frame_id'], msg, DataWarning)


def check_object_frame(database):
    msg = 'data-type is "OBJECT", but obtained with a wrong shutter status.'
    obj = database[database['data_type'] == 'OBJECT']
    flag = obj['shutter'] != 'open'
    for d in obj[flag]:
        warn(d['frame_id'], msg, DataWarning)
