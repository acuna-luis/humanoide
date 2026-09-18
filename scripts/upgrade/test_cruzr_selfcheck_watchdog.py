from datetime import timedelta
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import cruzr_selfcheck_watchdog as watchdog

# Excerpt of cc_main.20260918_142735.835.log (ANSI codes removed).
STUCK_LOG = '''D 2026-09-18 14:27:38.471950 861 cc operator()() sm state changed: waitBootReady --(ActionSucc)-> TmpState -- brain_impl_sm.cpp:134
D 2026-09-18 14:27:38.472897 861 cc operator()() sm state changed: TmpState --(NextStep)-> WaitEStopRelease -- brain_impl_sm.cpp:134
D 2026-09-18 14:29:03.056166 861 cc operator()() sm state changed: WaitEStopRelease --(EstopStateChanged)-> EnterWorkMode -- brain_impl_sm.cpp:134
D 2026-09-18 14:29:03.272830 861 cc onStart() start action: 3:SelfCheck() -- event_action.cpp:15
D 2026-09-18 14:29:03.273245 861 cc operator()() sm state changed: EnterWorkMode --(ActionSucc)-> SelfChecking -- brain_impl_sm.cpp:134
D 2026-09-18 14:31:35.217769 861 cc onTick() == timestamp:1789713095, up_minutes:4 == -- app.cpp:169
'''
STATES = ['TmpState', 'WaitEStopRelease', 'EnterWorkMode', 'SelfChecking']
SNAPSHOT = [[['861', '12345'], '/etc/walker/log/system/cc_main.x.log'], STATES]


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.entry = watchdog.selfcheck_entry(STUCK_LOG)
        self.monitor = self.entry + timedelta(seconds=6)
        self.now = self.entry + timedelta(minutes=10)

    def test_incident_signature_is_detected(self):
        self.assertEqual(watchdog.assess(SNAPSHOT, STUCK_LOG, self.monitor, self.now),
                         (True, 'selfcheck_monitor_restarted_result_lost'))

    def test_normal_selfcheck_duration_is_not_stuck(self):
        stuck, _ = watchdog.assess(SNAPSHOT, STUCK_LOG, self.monitor,
                                   self.entry + timedelta(seconds=60))
        self.assertFalse(stuck)

    def test_result_or_startmotion_blocks_recovery(self):
        for extra in ('I 2026-09-18 14:29:15.0 861 cc operator()() selfcheck result: {"passed":true}\n',
                      'D 2026-09-18 14:29:15.0 861 cc onStart() start action: 6:StartMotion()\n'):
            stuck, reason = watchdog.assess(SNAPSHOT, STUCK_LOG+extra, self.monitor, self.now)
            self.assertFalse(stuck, reason)

    def test_monitor_must_restart_after_selfcheck_began(self):
        for started in (None, self.entry - timedelta(minutes=4)):
            stuck, reason = watchdog.assess(SNAPSHOT, STUCK_LOG, started, self.now)
            self.assertEqual((stuck, reason), (False, 'monitor_not_restarted_after_selfcheck'))

    def test_only_initial_boot_path_in_selfchecking(self):
        for states in (STATES[:-1]+['JoystickMode'],
                       ['TmpState', 'TeleopMode', 'TmpState', 'EnterWorkMode', 'SelfChecking']):
            stuck, _ = watchdog.assess([SNAPSHOT[0], states], STUCK_LOG, self.monitor, self.now)
            self.assertFalse(stuck)
        self.assertEqual(watchdog.assess(None, STUCK_LOG, self.monitor, self.now)[0], False)

    def test_entry_is_last_transition_into_selfchecking(self):
        later = STUCK_LOG + ('D 2026-09-18 14:40:00.000000 861 cc operator()() sm state changed: '
                             'SelfChecking --(ActionFail)-> Fault -- x\n')
        self.assertIsNone(watchdog.selfcheck_entry(later))
        self.assertEqual(self.entry.strftime('%H:%M:%S'), '14:29:03')


if __name__ == '__main__':
    unittest.main()
