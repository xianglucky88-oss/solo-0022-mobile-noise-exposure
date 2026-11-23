import math

from .contract import obj
from .splice import splice


def level(energy, length):
    return 10 * math.log10(energy / length) if length else None


def energy(db, length):
    return 10 ** (db / 10) * length


def exposure(data):
    fragments = splice(data)
    covered = [f for f in fragments if f['status'] == 'covered']
    length = sum(f['stop'] - f['start'] for f in covered)
    total = math.fsum(energy(f['db'], f['stop'] - f['start']) for f in covered)
    return {'equivalent_db': level(total, length), 'covered_ms': length, 'window_ms': data['stop'] - data['start']}


def coverage(data):
    return {'fragments': splice(data)}


def compare(data):
    a, b = splice(obj(data['left'])), splice(obj(data['right']))
    i = j = length = 0
    left, right, support = [], [], []
    while i < len(a) and j < len(b):
        x, y = a[i], b[j]
        low, high = max(x['start'], y['start']), min(x['stop'], y['stop'])
        if low < high and x['status'] == y['status'] == 'covered':
            length += high - low
            left.append(energy(x['db'], high - low))
            right.append(energy(y['db'], high - low))
            support.append({'start': low, 'stop': high, 'left': x['reading'], 'right': y['reading'],
                            'left_certificate': x['certificate'], 'right_certificate': y['certificate']})
        if x['stop'] <= y['stop']:
            i += 1
        if y['stop'] <= x['stop']:
            j += 1
    return {'common_ms': length, 'difference_db': 10 * math.log10(math.fsum(right) / math.fsum(left)) if length else None,
            'support': support}
