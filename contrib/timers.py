import datetime

__author__ = '4ikist'
__doc__ = """
This file contains functions for computing time of decorating functions
"""
import logging
import time
import functools

log = logging.getLogger('timers')


def stopwatch(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = datetime.datetime.now()
        result = fn(*args, **kwargs)
        stop = datetime.datetime.now()
        elapsed = stop - start
        log.info('%s worked time: %s' % (fn, elapsed.total_seconds()))
        return result

    return wrapper


