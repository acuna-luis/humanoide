"""Exercise both standalone remote monitors without ROS or robot commands."""
import unittest
from runtime import entry410_single_stage_remote as entry
from runtime import metamove_head_probe as head


class StopCommunicationTests(unittest.TestCase):
    def test_state_loss_and_pressed_stop_are_distinct(self):
        for monitor in (entry, head):
            with self.subTest(monitor=monitor.__name__):
                monitor.check_stop_sample(100., 0, 104.5)
                monitor.check_stop_sample(100., 0, 106.)
                for received, value, now in (
                    (100., 1, 100.), (100., 2, 100.),
                    (100., 0, 106.001), (100., 0, 99.),
                    (float('nan'), 0, 100.), (100., 0, float('inf')),
                ):
                    with self.assertRaises(RuntimeError):
                        monitor.check_stop_sample(received, value, now)

    def test_missing_update_rejected_before_dispatch(self):
        for cadence in (entry.stop_cadence_ready, head.check_stop_cadence):
            self.assertFalse(cadence([100.]))
            self.assertTrue(cadence([100., 104.5, 109.]))
            for samples in ([100., 106.001], [100., 99.], [100., float('nan')]):
                with self.assertRaises(RuntimeError):
                    cadence(samples)


if __name__ == '__main__':
    unittest.main()
