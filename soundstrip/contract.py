"""Small validation primitives shared by operations within a service."""
import math


def obj(value):
    if type(value) is not dict:
        raise ValueError('expected an object')
    return value


def array(value, limit=512):
    if type(value) is not list or len(value) > limit:
        raise ValueError(f'expected an array of at most {limit} entries')
    return value


def key(value):
    if type(value) is not str or not value or len(value) > 96 or not value.strip():
        raise ValueError('expected a nonblank string up to 96 characters')
    return value


def integer(value, low=0, high=10**12):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'expected integer in [{low}, {high}]')
    return value


def decimal(value, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise ValueError(f'expected finite number in [{low}, {high}]')
    return float(value)


def rows(body, field, limit=512):
    seen = set()
    for value in array(body[field], limit):
        row = obj(value)
        identity = key(row['id'])
        if identity in seen:
            raise ValueError(f'duplicate {field} id: {identity}')
        seen.add(identity)
        yield identity, row
