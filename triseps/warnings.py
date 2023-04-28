#!/usr/bin/env python
# -*- code: utf-8 -*-
import sys, inspect


class DataWarning(RuntimeWarning):
  pass


def eprint(message):
  print(message, file=sys.stderr)


def warn(frame_id, message, category=DataWarning):
  func = inspect.stack()[1].function
  catname = category.__name__
  print(f'{func}: {catname}: {frame_id}: {message}', file=sys.stderr)
