"""Calibration and observation records in a shared synthetic millisecond clock."""
from dataclasses import dataclass

from .contract import decimal, integer, key, rows


def span(row):
    a, b = [integer(row[k], 0, 10**9) for k in ('start', 'stop')]
    if a >= b:
        raise ValueError('empty or reversed time span')
    return a, b


@dataclass(frozen=True)
class Certificate:
    ref: str
    instrument: str
    start: int
    stop: int
    offset: float


@dataclass(frozen=True)
class Reading:
    ref: str
    start: int
    stop: int
    instrument: str
    level: float
    priority: int


def load(data):
    by_instrument = {}
    for ref, row in rows(data, 'certificates', 128):
        by_instrument.setdefault(key(row['instrument']), []).append(
            Certificate(ref, key(row['instrument']), *span(row),
                        decimal(row['offset_db'], -40, 40)))
    for certs in by_instrument.values():
        certs.sort(key=lambda c: c.start)
        for a, b in zip(certs, certs[1:]):
            if a.stop > b.start:
                raise ValueError(f'certificate intervals overlap: {a.ref}, {b.ref}')
    readings = [Reading(ref, *span(row), key(row['instrument']), decimal(row['db'], -30, 180),
                        integer(row['priority'], 0, 100)) for ref, row in rows(data, 'readings', 256)]
    return by_instrument, sorted(readings, key=lambda row: row.ref)
