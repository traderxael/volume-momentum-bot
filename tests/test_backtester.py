import unittest

import pandas as pd

from backtester import Backtester
from risk_manager import RiskManager


class FakeStrategy:
    """Estrategia con senales fijas: el backtester se prueba sin mercado."""

    def __init__(self, signals):
        self.signals = signals

    def generate_signals(self, df):
        out = df.copy()
        out['signal'] = self.signals[:len(out)]
        return out


def make_df(closes):
    return pd.DataFrame({
        'timestamp': pd.date_range('2026-01-01', periods=len(closes), freq='h'),
        'open': closes,
        'high': [c * 1.01 for c in closes],
        'low': [c * 0.99 for c in closes],
        'close': closes,
        'volume': [1000.0] * len(closes),
    })


class TestBacktester(unittest.TestCase):
    """El backtester tiene que contar la verdad: comisiones y tamano real."""

    def setUp(self):
        self.risk = RiskManager(
            risk_per_trade=0.01,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            commission_pct=0.001,
        )

    def _run(self, closes, signals):
        bt = Backtester(FakeStrategy(signals), self.risk, initial_balance=1000)
        report = bt.run(make_df(closes))
        return bt, report

    def test_el_pnl_del_backtester_descuenta_comisiones(self):
        # Entra en 100 (con slippage 100.1), sale en 105 (take profit).
        # Tamano: riesgo 1% de 1000 = 10 USDT / stop 2% de 100 = 5 unidades.
        # Bruto: (105 - 100.1) * 5 = 24.5
        # Comisiones: (100.1 + 105) * 5 * 0.001 = 1.0255
        bt, report = self._run([100, 105], [1, 0])
        self.assertEqual(len(bt.trades), 1)
        self.assertAlmostEqual(bt.trades[0]['pnl'], 24.5 - 1.0255, places=6)
        self.assertAlmostEqual(report['final_balance'], 1000 + 24.5 - 1.0255, places=6)

    def test_el_backtester_usa_el_tamano_de_la_entrada(self):
        # El P&L se calcula con el tamano que se Abrio, no con uno recalculado
        # sobre el balance inicial.
        bt, _ = self._run([100, 105], [1, 0])
        self.assertAlmostEqual(bt.trades[0]['size'], 5.0, places=6)

    def test_sin_comisiones_el_backtester_no_cambia(self):
        self.risk.commission_pct = 0.0
        bt, report = self._run([100, 105], [1, 0])
        self.assertAlmostEqual(bt.trades[0]['pnl'], 24.5, places=6)
        self.assertAlmostEqual(report['final_balance'], 1024.5, places=6)

    def test_el_informe_dice_cuanto_se_pago_en_comisiones(self):
        bt, report = self._run([100, 105], [1, 0])
        self.assertAlmostEqual(report['total_commission'], 1.0255, places=6)


if __name__ == '__main__':
    unittest.main()
