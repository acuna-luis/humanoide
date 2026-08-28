#!/usr/bin/env python3
"""Unit tests for the pure E3.3 temporal contract."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / "vla_temporal_contract.py"
CONTRACT_PATH = HERE / "cruzr_s2_vla_temporal_contract_e3_3.json"
SPEC = importlib.util.spec_from_file_location("vla_temporal_contract", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TemporalContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = MODULE.load_contract(CONTRACT_PATH)
        self.times = MODULE.nominal_point_times(self.contract)

    def gate(self):
        return MODULE.OfflineTemporalGate(self.contract, started_at=100.0)

    def drain(self, gate, base):
        rows = []
        for offset in self.times:
            decision = gate.advance(base + offset)
            self.assertTrue(decision.accepted, decision.reasons)
            rows.extend(decision.emitted)
        return rows

    def test_exact_ten_point_schedule_and_no_replay(self):
        gate = self.gate()
        self.assertTrue(gate.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0).accepted)
        rows = self.drain(gate, 100.0)
        self.assertEqual([row["point_index"] for row in rows], list(range(10)))
        self.assertEqual(gate.advance(100.80).emitted, [])
        self.assertEqual(len(gate.emission_log), 10)

    def test_overlap_latches_fault_and_purges(self):
        gate = self.gate()
        gate.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        decision = gate.submit(chunk_id=2, point_times=self.times, flag_pred=0.0, now=100.01)
        self.assertFalse(decision.accepted)
        self.assertEqual(gate.state, "FAULTED")
        self.assertEqual(gate.pending, [])

    def test_late_dispatch_latches_fault(self):
        gate = self.gate()
        gate.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        decision = gate.advance(100.02)
        self.assertFalse(decision.accepted)
        self.assertEqual(gate.state, "FAULTED")

    def test_nonfinite_first_point_time_rejects_cleanly(self):
        gate = self.gate()
        times = list(self.times)
        times[0] = float("nan")
        decision = gate.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
        self.assertFalse(decision.accepted)
        self.assertEqual(gate.state, "ACTIVE")
        self.assertEqual(gate.pending, [])

    def test_interchunk_timeout_emits_nothing_old(self):
        gate = self.gate()
        gate.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        self.drain(gate, 100.0)
        self.assertEqual(gate.advance(101.20).emitted, [])
        decision = gate.advance(101.221)
        self.assertFalse(decision.accepted)
        self.assertEqual(gate.state, "TIMED_OUT")
        self.assertEqual(len(gate.emission_log), 10)

    def test_next_chunk_inside_gap(self):
        gate = self.gate()
        gate.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        self.drain(gate, 100.0)
        self.assertTrue(gate.submit(chunk_id=2, point_times=self.times, flag_pred=0.0, now=100.8).accepted)
        rows = self.drain(gate, 100.8)
        self.assertEqual(len(rows), 10)

    def test_cancel_before_during_and_between_purge(self):
        before = self.gate()
        before.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        self.assertTrue(before.cancel(100.0).accepted)
        self.assertEqual(before.pending, [])

        during = self.gate()
        during.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        during.advance(100.0)
        during.advance(100.08)
        self.assertTrue(during.cancel(100.081).accepted)
        self.assertEqual(len(during.emission_log), 2)
        self.assertEqual(during.pending, [])

        between = self.gate()
        between.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        self.drain(between, 100.0)
        self.assertTrue(between.cancel(100.8).accepted)
        self.assertEqual(between.pending, [])

    def test_stop_and_sensor_loss_purge(self):
        stopped = self.gate()
        stopped.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
        self.assertTrue(stopped.stop(100.0).accepted)
        self.assertTrue(stopped.stop(100.0).accepted)
        self.assertEqual(stopped.pending, [])

        for sensor in ("state", "image"):
            gate = self.gate()
            gate.submit(chunk_id=1, point_times=self.times, flag_pred=0.0, now=100.0)
            self.assertTrue(gate.sensor_fault(sensor, 100.0).accepted)
            self.assertEqual(gate.state, "FAULTED")
            self.assertEqual(gate.pending, [])

    def test_five_consecutive_candidate_and_reset(self):
        policy = MODULE.ConsecutiveEndPolicy(threshold=0.1, required=5)
        self.assertEqual([policy.observe(value) for value in (0.2, 0.2, 0.2, 0.2)], [False] * 4)
        self.assertFalse(policy.observe(0.1))
        self.assertEqual([policy.observe(0.2) for _ in range(4)], [False] * 4)
        self.assertTrue(policy.observe(0.2))

    def test_vendor_observed_policy_is_single_strict_threshold(self):
        policy = MODULE.VendorObservedEndPolicy(threshold=0.1)
        self.assertFalse(policy.observe(0.1))
        self.assertTrue(policy.observe(0.100001))

    def test_fifth_end_chunk_completes_after_its_last_point(self):
        gate = self.gate()
        base = 100.0
        for chunk_id in range(1, 6):
            self.assertTrue(gate.submit(chunk_id=chunk_id, point_times=self.times, flag_pred=0.2, now=base).accepted)
            self.drain(gate, base)
            if chunk_id < 5:
                self.assertEqual(gate.state, "ACTIVE")
            base += 0.8
        self.assertEqual(gate.state, "COMPLETED")
        self.assertEqual(len(gate.emission_log), 50)

    def test_session_timeout_and_cancel_after_timeout_are_idempotent(self):
        gate = self.gate()
        decision = gate.advance(108.0)
        self.assertFalse(decision.accepted)
        self.assertEqual(gate.state, "TIMED_OUT")
        self.assertTrue(gate.cancel(108.0).accepted)
        self.assertEqual(gate.state, "TIMED_OUT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
