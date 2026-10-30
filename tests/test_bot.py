import os
import unittest

from bot import TradingBot


class FakeBinance:
    """Binance de mentira: solo balance y colocacion de ordenes."""

    def __init__(self, balance=1000.0):
        self.balance = balance
        self.orders = []

    def get_balance(self):
        return {'USDT': self.balance}

    def place_order(self, symbol, side, quantity, price=None):
        self.orders.append({'symbol': symbol, 'side': side, 'quantity': quantity})
        return {'orderId': len(self.orders), 'status': 'DRY_RUN'}


class TestBotRiskGuards(unittest.TestCase):
    """El bot tiene que obeying los limites antes de mandar una orden."""

    def setUp(self):
        self.bot = TradingBot({'DRY_RUN': True, 'SYMBOL': 'BTCUSDT'})
        self.bot.binance = FakeBinance(balance=1000.0)
        self.bot.risk.reset_daily(1000.0)

    def test_no_abre_operacion_si_se_supero_el_limite_diario(self):
        self.bot.risk.record_trade_result(-100)   # -10% con limite del 5%
        position = self.bot.execute_trade(1, 100)
        self.assertIsNone(position)
        self.assertEqual(self.bot.binance.orders, [])

    def test_no_abre_operacion_durante_el_cooldown(self):
        self.bot.cooldown_seconds = 300
        self.bot._clock = lambda: 1000.0
        self.bot.last_exit_time = 900.0
        position = self.bot.execute_trade(1, 100)
        self.assertIsNone(position)
        self.assertEqual(self.bot.binance.orders, [])

    def test_pasado_el_cooldown_si_puede_operar(self):
        self.bot.cooldown_seconds = 300
        self.bot._clock = lambda: 1500.0
        self.bot.last_exit_time = 1000.0
        position = self.bot.execute_trade(1, 100)
        self.assertIsNotNone(position)
        self.assertEqual(len(self.bot.binance.orders), 1)

    def test_no_supera_el_maximo_de_posiciones_simultaneas(self):
        self.bot.max_open_positions = 1
        self.bot._clock = lambda: 1000.0
        first = self.bot.execute_trade(1, 100)
        self.assertIsNotNone(first)
        # Una segunda senal con el limite en 1 no puede abrir otra posicion.
        self.bot.last_exit_time = None
        second = self.bot.execute_trade(1, 100)
        self.assertIsNone(second)
        self.assertEqual(len(self.bot.open_positions), 1)

    def test_cerrar_una_posicion_registra_el_pnl_del_dia(self):
        self.bot._clock = lambda: 1000.0
        self.bot.execute_trade(1, 100)
        # Entrada a 100, salida a 98: 5 unidades a -2 = -10 USDT brutos.
        # Comisiones (0.1% de las dos piernas): 0.99 USDT. Neto: -10.99.
        self.bot._close_position(98)
        self.assertAlmostEqual(self.bot.risk.daily_pnl, -10.99, places=6)
        self.assertEqual(self.bot.last_exit_time, 1000.0)


class TestConfigFromEnv(unittest.TestCase):
    """La configuracion sale del .env: si no, los limites no se pueden cambiar."""

    def _bot_con_env(self, **env):
        keys = list(env.keys())
        for k in keys:
            os.environ[k] = env[k]
        try:
            return TradingBot()
        finally:
            for k in keys:
                os.environ.pop(k, None)

    def test_los_valores_del_env_se_cargan_con_su_tipo(self):
        bot = self._bot_con_env(
            MAX_DAILY_LOSS_PCT='0.02',
            COOLDOWN_SECONDS='60',
            MAX_OPEN_POSITIONS='2',
            COMMISSION_PCT='0.0005',
            DRY_RUN='false',
            SYMBOL='ETHUSDT',
        )
        self.assertAlmostEqual(bot.risk.max_daily_loss_pct, 0.02)
        self.assertEqual(bot.cooldown_seconds, 60)
        self.assertEqual(bot.max_open_positions, 2)
        self.assertAlmostEqual(bot.risk.commission_pct, 0.0005)
        self.assertFalse(bot.dry_run)
        self.assertEqual(bot.symbol, 'ETHUSDT')

    def test_un_valor_invalido_no_revienta_el_bot(self):
        bot = self._bot_con_env(COOLDOWN_SECONDS='no-es-un-numero')
        self.assertEqual(bot.cooldown_seconds, 300)   # el valor por defecto


if __name__ == '__main__':
    unittest.main()
