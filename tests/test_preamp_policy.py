import unittest

from swproj2eq.core.dsp import compute_preamp_db


class DummyChannel:
    def __init__(self, gains):
        self.correction_dB = gains


class PreampPolicyTests(unittest.TestCase):
    def test_global_max_positive_gain_plus_headroom(self):
        channels = [DummyChannel([-1.0, 2.3, 0.0]), DummyChannel([1.5, 3.0, -4.0])]
        self.assertAlmostEqual(compute_preamp_db(channels), -4.0)

    def test_no_positive_gain_returns_zero(self):
        channels = [DummyChannel([-3.0, -1.0]), DummyChannel([-0.5, 0.0])]
        self.assertEqual(compute_preamp_db(channels), 0.0)


if __name__ == "__main__":
    unittest.main()
