from .calibration import load, span


def splice(run):
    start, stop = span(run)
    by_instrument, readings = load(run)
    certs = [c for instrument in {r.instrument for r in readings} for c in by_instrument.get(instrument, ())]
    bounds = {start, stop}
    for item in [*readings, *certs]:
        bounds.update(n for n in (item.start, item.stop) if start < n < stop)
    boundaries = sorted(bounds)
    fragments = []
    for a, b in zip(boundaries, boundaries[1:]):
        active = [r for r in readings if r.start <= a < r.stop]
        valid, uncalibrated = [], []
        for reading in active:
            cert = next((c for c in by_instrument.get(reading.instrument, []) if c.start <= a < c.stop), None)
            if cert:
                valid.append((reading, cert))
            else:
                uncalibrated.append(reading.ref)
        fragment = {'start': a, 'stop': b, 'uncalibrated': uncalibrated}
        if not valid:
            fragment.update(status='uncalibrated' if active else 'gap')
        else:
            high = max(r.priority for r, _ in valid)
            top = [(r, c) for r, c in valid if r.priority == high]
            if len(top) > 1:
                fragment.update(status='conflict', contenders=[r.ref for r, _ in top])
            else:
                r, c = top[0]
                fragment.update(status='covered', reading=r.ref, certificate=c.ref, db=r.level + c.offset)
        fragments.append(fragment)
    return fragments
