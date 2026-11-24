"""Fixed-length window support review and peak-window selection.

All spans are left-closed and right-open.  A window is backed by exactly one
instrument and one certificate that contains the whole window; consecutive
certificates of the same instrument may not be combined.  Inside the window the
ordinary splice priority rules apply: overlapping readings select the highest
priority and an unresolved same-instrument tie makes that instrument unable to
back the window.  Among the instruments that fully back the window the weakest
selected reading priority decides; a tie at the top makes the window disputed
and it is left out of the comparison.

The peak search does not walk a millisecond at a time.  Between adjacent
reading/certificate boundaries the selected readings, the certificate
containment and therefore the window energy are fixed or linear in the window
start, so a maximum over a region is reached at a region edge.  Candidate starts
are built from those boundaries (and their millisecond neighbours), which also
covers starts that are not raw-reading starts such as ``reading.stop -
window_ms``.  The number of candidates is linear in the number of records, not
in the length of the time axis.
"""
import math

from .calibration import load, span
from .contract import integer
from .exposure import energy, level

LEVEL_TIE = 1e-9


def certificate_detail(cert):
    return {'id': cert.ref, 'instrument': cert.instrument, 'start': cert.start,
            'stop': cert.stop, 'offset_db': cert.offset}


def reading_detail(reading):
    return {'id': reading.ref, 'instrument': reading.instrument,
            'start': reading.start, 'stop': reading.stop,
            'db': reading.level, 'priority': reading.priority}


class Survey:
    """Readings, certificates and per-instrument priority selection."""

    def __init__(self, run):
        self.start, self.stop = span(run)
        self.by_instrument, self.readings = load(run)
        self.by_reading = {}
        for reading in self.readings:
            self.by_reading.setdefault(reading.instrument, []).append(reading)
        self.instruments = sorted(self.by_reading)

    def certificate_state(self, instrument, a, b):
        """Describe how this instrument's certificates cover [a, b).

        ``single`` is the only acceptable state: one certificate contains the
        whole window.  ``split`` means touching certificates jointly cover it,
        which is forbidden.  ``gap`` means the certificates do not cover it at
        all.  A certificate's right endpoint is not part of its coverage, so
        ``b == certificate.stop`` is still fully contained.
        """
        certs = self.by_instrument.get(instrument, ())
        for cert in certs:
            if cert.start <= a and b <= cert.stop:
                return 'single', cert
        covered = a
        for cert in certs:  # load() keeps certificates sorted by start
            if cert.stop <= covered:
                continue
            if cert.start > covered:
                break
            covered = cert.stop
        return ('split' if covered >= b else 'gap'), None

    def assess(self, instrument, a, b):
        """Judge one instrument's support for the window [a, b)."""
        state, cert = self.certificate_state(instrument, a, b)
        certs = self.by_instrument.get(instrument, ())
        readings = [r for r in self.by_reading.get(instrument, ())
                    if r.start < b and r.stop > a]
        points = {a, b}
        for reading in readings:
            if a < reading.start < b:
                points.add(reading.start)
            if a < reading.stop < b:
                points.add(reading.stop)
        ordered = sorted(points)
        segments, gaps, conflicts, uncalibrated, selected = [], [], [], [], []
        weakest = None
        for low, high in zip(ordered, ordered[1:]):
            active = [r for r in readings if r.start <= low < r.stop]
            if not active:
                gaps.append({'start': low, 'stop': high})
                continue
            valid, missing = [], []
            for reading in active:
                cert_here = next((c for c in certs if c.start <= low < c.stop), None)
                (valid if cert_here else missing).append((reading, cert_here))
            if not valid:
                # A calibrated lower-priority source always outranks an
                # uncalibrated one, so only a fragment with no calibrated
                # reading at all is an uncalibrated hole.
                uncalibrated.append({'start': low, 'stop': high,
                                     'readings': sorted(r.ref for r, _ in missing)})
                continue
            priority = max(r.priority for r, _ in valid)
            top = [(r, c) for r, c in valid if r.priority == priority]
            if len(top) > 1:
                conflicts.append({'start': low, 'stop': high,
                                  'contenders': sorted(r.ref for r, _ in top)})
                continue
            reading, fragment_cert = top[0]
            weakest = reading.priority if weakest is None else min(weakest, reading.priority)
            if reading.ref not in selected:
                selected.append(reading.ref)
            segments.append({'start': low, 'stop': high,
                             'reading': reading.ref,
                             'reading_start': reading.start,
                             'reading_stop': reading.stop,
                             'level_db': reading.level,
                             'priority': reading.priority,
                             'certificate': fragment_cert.ref if fragment_cert else None,
                             'offset_db': fragment_cert.offset if fragment_cert else None,
                             'db': reading.level + fragment_cert.offset if fragment_cert else None})
        complete = not gaps and not uncalibrated and not conflicts
        return {
            'instrument': instrument,
            'certificate': cert.ref if cert else None,
            'certificate_state': state,
            'certificate_detail': certificate_detail(cert) if cert else None,
            'certificates': [certificate_detail(c) for c in certs
                             if c.start < b and c.stop > a],
            'observation_complete': not gaps,
            'calibration_complete': not uncalibrated,
            'readings_complete': not gaps and not uncalibrated,
            'unique_readings': complete,
            'weakest_priority': weakest if complete else None,
            'segments': segments,
            'selected_readings': selected,
            'gaps': gaps,
            'uncalibrated': uncalibrated,
            'conflicts': conflicts,
            'supports': complete and state == 'single',
        }


def evaluate(survey, a, length):
    """Review the fixed-length window starting at ``a``."""
    b = a + length
    assessments = [survey.assess(name, a, b) for name in survey.instruments]
    supporters = [item for item in assessments if item['supports']]
    result = {'window': {'start': a, 'stop': b, 'window_ms': length},
              'window_start': a, 'window_stop': b,
              'instruments': assessments}
    if supporters:
        best = max(item['weakest_priority'] for item in supporters)
        winners = [item for item in supporters if item['weakest_priority'] == best]
        if len(winners) > 1:
            result.update(status='disputed', reason='priority_dispute', priority=best,
                          tied_instruments=[item['instrument'] for item in winners])
        else:
            chosen = winners[0]
            total = math.fsum(energy(seg['db'], seg['stop'] - seg['start'])
                              for seg in chosen['segments'])
            details = []
            for ref in chosen['selected_readings']:
                reading = next(r for r in survey.readings if r.ref == ref)
                details.append(reading_detail(reading))
            result.update(status='usable', reason='supported',
                          instrument=chosen['instrument'],
                          certificate=chosen['certificate'],
                          certificate_detail=chosen['certificate_detail'],
                          weakest_priority=best,
                          equivalent_db=level(total, length),
                          segments=chosen['segments'],
                          readings=chosen['selected_readings'],
                          reading_details=details)
        return result
    disputed = any(item['observation_complete'] and item['conflicts']
                   and item['certificate_state'] == 'single' for item in assessments)
    certificate = any(item['observation_complete'] and item['certificate_state'] != 'single'
                      for item in assessments)
    if disputed:
        result.update(status='unsupported', reason='priority_dispute',
                      category='dispute')
    elif certificate:
        result.update(status='unsupported', reason='certificate_insufficient',
                      category='coverage')
    else:
        result.update(status='unsupported', reason='insufficient_observation',
                      category='coverage')
    return result


def candidate_starts(survey, length):
    """Derived candidate starts; never a millisecond-by-millisecond sweep."""
    low, high = survey.start, survey.stop - length
    if high < low:
        return []
    base = {low, high}
    for certs in survey.by_instrument.values():
        for cert in certs:
            base.add(cert.start)
            base.add(cert.stop - length)
    for reading in survey.readings:
        base.add(reading.start)
        base.add(reading.stop)
        base.add(reading.start - length)
        base.add(reading.stop - length)
    starts = set()
    for point in base:
        for candidate in (point - 1, point, point + 1):
            if low <= candidate <= high:
                starts.add(candidate)
    return sorted(starts)


def _compact(result):
    return {'window': result['window'], 'reason': result['reason'],
            'instruments': [{'instrument': item['instrument'],
                             'certificate_state': item['certificate_state'],
                             'readings_complete': item['readings_complete'],
                             'unique_readings': item['unique_readings'],
                             'weakest_priority': item['weakest_priority']}
                            for item in result['instruments']]}


def peak(survey, length):
    """Select the highest-equivalent usable window, earliest on ties."""
    starts = candidate_starts(survey, length)
    best, causes, examples = None, {}, {}
    for a in starts:
        result = evaluate(survey, a, length)
        if result['status'] == 'usable':
            if best is None or result['equivalent_db'] > best['equivalent_db'] + LEVEL_TIE:
                best = result
        else:
            reason = result['reason']
            causes[reason] = causes.get(reason, 0) + 1
            examples.setdefault(reason, _compact(result))
    if best is not None:
        return {'status': 'usable', 'reason': 'supported', 'evaluated': len(starts),
                'window': best['window'], 'window_start': best['window_start'],
                'window_stop': best['window_stop'],
                'equivalent_db': best['equivalent_db'],
                'instrument': best['instrument'], 'certificate': best['certificate'],
                'certificate_detail': best['certificate_detail'],
                'weakest_priority': best['weakest_priority'],
                'segments': best['segments'], 'readings': best['readings'],
                'reading_details': best['reading_details']}
    if causes.get('priority_dispute'):
        status, reason, category = 'disputed', 'priority_dispute', 'dispute'
    elif causes.get('certificate_insufficient'):
        status, reason, category = 'unsupported', 'certificate_insufficient', 'coverage'
    else:
        status, reason, category = 'unsupported', 'insufficient_observation', 'coverage'
    return {'status': status, 'reason': reason, 'category': category,
            'evaluated': len(starts), 'window': None, 'window_start': None,
            'window_stop': None, 'equivalent_db': None,
            'causes': causes, 'examples': examples}


def _fixed_length(data):
    survey = Survey(data)
    length = integer(data['window_ms'], 1, 10**9)
    if length > survey.stop - survey.start:
        raise ValueError('window is longer than the survey interval')
    return survey, length


def review(data):
    """Review a caller-specified window; ``window_start`` is required here."""
    survey, length = _fixed_length(data)
    start = integer(data['window_start'], 0, 10**9)
    if start < survey.start or start + length > survey.stop:
        raise ValueError('window is not inside the survey interval')
    return evaluate(survey, start, length)


def peak_window(data):
    """Select the peak fixed-length window of the survey."""
    survey, length = _fixed_length(data)
    return peak(survey, length)
