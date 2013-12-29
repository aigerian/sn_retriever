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
        start = time.time()
        result = fn(*args, **kwargs)
        stop = time.time()
        elapsed = stop - start
        log.info('%s worked time: %s' % (fn.__name__, elapsed))
        return result

    return wrapper


