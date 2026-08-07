"""Tests for the tick constant used by pulses_to_data / data_to_pulses (GH #839)."""
import unittest

from broadlink.remote import TICK, data_to_pulses, pulses_to_data

OLD_TICK = 32.84  # the constant this PR replaces


class TestTickConstant(unittest.TestCase):
    """TICK must match protocol.md's worked examples (its "us * 269 / 8192" formula)."""

    def test_tick_matches_protocol_md(self):
        # protocol.md's literal, verified-by-example formula.
        self.assertAlmostEqual(TICK, 8192 / 269, places=4)

    def test_protocol_md_worked_examples(self):
        # protocol.md's own worked examples, applying its own formula
        # (us * 269 / 8192) literally: 8920 us -> 0x124 (292 ticks),
        # 4450 us -> 0x92 (146 ticks). TICK = 8192 / 269 reproduces both
        # exactly; the alternative reading "2^-15 s" (1e6 / 2**15,
        # 30.5176 us) is 0.2% different and lands one tick short on the
        # second example under floor division. See PR discussion for why
        # 8192/269 is the better-evidenced choice pending hardware bench.
        for us, expected_ticks in ((8920, 292), (4450, 146)):
            got = int(us // TICK)
            self.assertLessEqual(abs(got - expected_ticks), 1)
            old_got = int(us // OLD_TICK)
            self.assertGreater(abs(old_got - expected_ticks), 5)

    def test_round_trip(self):
        # Learn-then-send is unaffected by which tick is used, as long as
        # both directions agree -- this must hold for TICK just as it held
        # for the old constant.
        pulses = [9000, 4500, 560, 1690, 560, 560]
        packet = pulses_to_data(pulses)
        decoded = data_to_pulses(packet)
        for original, result in zip(pulses, decoded):
            self.assertAlmostEqual(result, original, delta=TICK)

    def test_true_microsecond_nec_leader_is_now_correct(self):
        # A real NEC leader (9000/4500 us) built from TRUE microseconds
        # (e.g. Home Assistant's infrared platform, not a Broadlink round
        # trip) must decode back to ~9000/4500, not ~7% short.
        packet = pulses_to_data([9000, 4500])
        decoded = data_to_pulses(packet)
        self.assertAlmostEqual(decoded[0], 9000, delta=50)
        self.assertAlmostEqual(decoded[1], 4500, delta=50)

    def test_old_constant_was_seven_percent_short_on_real_hardware(self):
        # The silicon's timebase is fixed regardless of what the software
        # assumed, so what the old code actually put on the wire for a
        # true-microsecond input is tick_count * TICK, not
        # tick_count * OLD_TICK. This reproduces the ~7% figure from the
        # issue's hardware bench (8362us/8437us measured vs ~9000/9116us
        # true, same ballpark once packet framing rounding is folded in).
        buggy_packet = pulses_to_data([9000, 4500], tick=OLD_TICK)
        actually_transmitted = data_to_pulses(buggy_packet, tick=TICK)
        self.assertLess(actually_transmitted[0], 9000 - 500)
        self.assertLess(actually_transmitted[1], 4500 - 250)


if __name__ == "__main__":
    unittest.main()
