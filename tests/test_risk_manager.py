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


class TestRiskLimits(unittest.TestCase):
    """Los limites que faltaban antes de operar en vivo (issue #1)."""

    def test_limite_de_perdida_diaria_bloquea_cuando_se_supera(self):
        rm = RiskManager(max_daily_loss_pct=0.05)
        rm.reset_daily(1000)
        self.assertFalse(rm.daily_loss_exceeded())
        rm.record_trade_result(-20)          # -2% del balance de referencia
        self.assertFalse(rm.daily_loss_exceeded())
        rm.record_trade_result(-40)          # -6% en total: ya se paso
        self.assertTrue(rm.daily_loss_exceeded())
        self.assertFalse(rm.can_open_trade())

    def test_una_ganancia_no_borra_la_perdida_del_dia(self):
        rm = RiskManager(max_daily_loss_pct=0.05)
        rm.reset_daily(1000)
        rm.record_trade_result(-60)
        rm.record_trade_result(+30)
        self.assertTrue(rm.daily_loss_exceeded())

    def test_el_limite_diario_se_reinicia_con_el_balance(self):
        rm = RiskManager(max_daily_loss_pct=0.05)
        rm.reset_daily(1000)
        rm.record_trade_result(-100)
        self.assertTrue(rm.daily_loss_exceeded())
        rm.reset_daily(1000)
        self.assertFalse(rm.daily_loss_exceeded())
        self.assertEqual(rm.daily_pnl, 0.0)

    def test_cooldown_entre_senales(self):
        rm = RiskManager(cooldown_seconds=300)
        self.assertFalse(rm.cooldown_active(None, 1000.0))
        # El cooldown bloquea desde el mismo instante de la salida.
        self.assertTrue(rm.cooldown_active(1000.0, 1000.0))
        self.assertTrue(rm.cooldown_active(1000.0, 1100.0))
        self.assertFalse(rm.cooldown_active(1000.0, 1300.0))

    def test_maximo_de_posiciones_simultaneas(self):
        rm = RiskManager(max_open_positions=2)
        self.assertTrue(rm.can_open_position(0))
        self.assertTrue(rm.can_open_position(1))
        self.assertFalse(rm.can_open_position(2))

    def test_el_pnl_descuenta_comisiones_de_entrada_y_salida(self):
        rm = RiskManager(commission_pct=0.001)
        # long: 100 -> 110 con 1 unidad. Bruto 10.
        # Comisiones: 0.1 de entrada (100) + 0.11 de salida (110) = 0.21
        self.assertAlmostEqual(rm.calculate_pnl(100, 110, 'long', 1.0), 9.79)
        # short: 100 -> 90 con 1 unidad. Bruto 10.
        # Comisiones: 0.1 de entrada (100) + 0.09 de salida (90) = 0.19
        self.assertAlmostEqual(rm.calculate_pnl(100, 90, 'short', 1.0), 9.81)

    def test_sin_comisiones_el_pnl_es_el_bruto(self):
        rm = RiskManager(commission_pct=0.0)
        self.assertAlmostEqual(rm.calculate_pnl(100, 110, 'long', 1.0), 10.0)


if __name__ == "__main__":
    unittest.main()
