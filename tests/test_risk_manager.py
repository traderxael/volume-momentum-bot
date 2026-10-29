import math
import unittest

from risk_manager import RiskManager


class TestRiskManager(unittest.TestCase):
    def test_position_size_uses_risk_and_stop(self):
        rm = RiskManager(risk_per_trade=0.01, stop_loss_pct=0.02, take_profit_pct=0.04)
        self.assertAlmostEqual(rm.calculate_position_size(1000, 100), 5.0)

    def test_position_size_capped_to_spot_balance(self):
        rm = RiskManager(risk_per_trade=1.0, stop_loss_pct=0.01)
        self.assertAlmostEqual(rm.calculate_position_size(1000, 100), 10.0)

    def test_position_size_rejects_invalid_inputs(self):
        rm = RiskManager()
        for balance, price in [(0, 100), (-1, 100), (1000, 0), (1000, -5), (math.nan, 100), (1000, math.inf)]:
            self.assertEqual(rm.calculate_position_size(balance, price), 0.0, (balance, price))

    def test_sl_tp_long(self):
        rm = RiskManager(stop_loss_pct=0.02, take_profit_pct=0.04)
        sl, tp = rm.calculate_sl_tp(100, "long")
        self.assertAlmostEqual(sl, 98.0)
        self.assertAlmostEqual(tp, 104.0)
        self.assertAlmostEqual(rm.calculate_rr(100, sl, tp), 2.0)

    def test_entry_slippage_long_short(self):
        rm = RiskManager()
        self.assertAlmostEqual(rm.calculate_entry(100, "long"), 100.1)
        self.assertAlmostEqual(rm.calculate_entry(100, "short"), 99.9)

    def test_long_stop_and_target(self):
        rm = RiskManager(stop_loss_pct=0.02, take_profit_pct=0.04)
        self.assertTrue(rm.check_stop_loss(97, 100, "long"))
        self.assertFalse(rm.check_stop_loss(99, 100, "long"))
        self.assertTrue(rm.check_take_profit(105, 100, "long"))
        self.assertFalse(rm.check_take_profit(103, 100, "long"))

    def test_sl_tp_short(self):
        rm = RiskManager(stop_loss_pct=0.02, take_profit_pct=0.04)
        sl, tp = rm.calculate_sl_tp(100, "short")
        self.assertAlmostEqual(sl, 102.0)
        self.assertAlmostEqual(tp, 96.0)
        self.assertTrue(rm.check_stop_loss(103, 100, "short"))
        self.assertTrue(rm.check_take_profit(95, 100, "short"))


if __name__ == "__main__":
    unittest.main()
