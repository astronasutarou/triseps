#!/usr/bin/env python
# -*- code: utf-8 -*-
import sys


class DataWarning(RuntimeWarning):
    pass


def eprint(message):
    print(message, file=sys.stderr)


def warn(frame_id, message, category):
    message = f'{category.__name__}: {frame_id}: {message}'
    print(message, file=sys.stderr)
