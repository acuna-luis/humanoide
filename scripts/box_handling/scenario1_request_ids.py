"""Bounded replay protection for sequential, potentially long-lived sessions."""
import re


class RequestIds:
    """Keep only a high-water mark for the IDs emitted by ProcessSession.

    Decimal IDs must start at 1 and increase exactly by one. Legacy named IDs
    retain their bounded set and request limit. A session cannot switch modes,
    so changing ID syntax cannot evade replay checks or clear their history.
    """
    __slots__ = ('legacy_limit', 'mode', 'last_sequence', 'legacy_ids')

    def __init__(self, legacy_limit):
        self.legacy_limit = legacy_limit
        self.mode = None
        self.last_sequence = 0
        self.legacy_ids = set()

    @staticmethod
    def sequence(request_id):
        # Length is capped even when used without a worker's field validator.
        if isinstance(request_id, str) and re.fullmatch(r'[1-9][0-9]{0,127}', request_id):
            return int(request_id)
        return None

    def validate(self, request_id):
        sequence = self.sequence(request_id)
        mode = 'sequential' if sequence is not None else 'legacy'
        if self.mode is not None and mode != self.mode:
            raise ValueError('Cannot mix sequential and legacy request_id modes')
        if sequence is not None:
            if sequence <= self.last_sequence:
                raise ValueError('Repeated request_id; no retry permitted')
            if sequence != self.last_sequence + 1:
                raise ValueError('Out-of-order request_id; expected the next sequence')
        else:
            if request_id in self.legacy_ids:
                raise ValueError('Repeated request_id; no retry permitted')
            if len(self.legacy_ids) >= self.legacy_limit:
                raise ValueError('Session request limit reached for legacy request_id mode')

    def add(self, request_id):
        self.validate(request_id)
        sequence = self.sequence(request_id)
        if sequence is None:
            self.mode = 'legacy'
            self.legacy_ids.add(request_id)
        else:
            self.mode = 'sequential'
            self.last_sequence = sequence
