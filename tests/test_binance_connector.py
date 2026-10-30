import unittest

from binance_connector import BinanceConnector


LOT_SIZE = {'filterType': 'LOT_SIZE', 'minQty': '0.00001', 'stepSize': '0.00001'}
MIN_NOTIONAL = {'filterType': 'MIN_NOTIONAL', 'minNotional': '5.0'}


class FakeClient:
    """Cliente de Binance minimo: solo los filtros y el precio actual."""

    def __init__(self, filters=None, price=100.0):
        self._filters = filters if filters is not None else [LOT_SIZE, MIN_NOTIONAL]
        self._price = price
        self.orders = []

    def get_symbol_info(self, symbol):
        return {'symbol': symbol, 'filters': self._filters}

    def get_symbol_ticker(self, symbol):
        return {'symbol': symbol, 'price': str(self._price)}

    def create_order(self, **kwargs):
        self.orders.append(kwargs)
        return {'orderId': 1, 'status': 'FILLED', **kwargs}


def make_connector(filters=None, price=100.0):
    """Conector sin red: se arma a mano para no tocar la API real."""
    c = BinanceConnector.__new__(BinanceConnector)
    c.api_key = None
    c.api_secret = None
    c.dry_run = False
    c.client = FakeClient(filters, price)
    c._filters = {}
    return c


class TestMinNotional(unittest.TestCase):
    """Una orden de 1 USDT la acepta el LOT_SIZE pero la rebota Binance."""

    def test_orden_por_debajo_del_min_notional_se_rechaza(self):
        c = make_connector()
        result = c.place_order('BTCUSDT', 'BUY', quantity=0.01, price=100)
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('MIN_NOTIONAL', result['message'])
        self.assertEqual(c.client.orders, [])

    def test_orden_por_sobre_del_min_notional_pasa(self):
        c = make_connector()
        result = c.place_order('BTCUSDT', 'BUY', quantity=0.10, price=100)
        self.assertNotEqual(result['status'], 'ERROR')
        self.assertEqual(len(c.client.orders), 1)

    def test_orden_a_mercado_valida_contra_el_precio_actual(self):
        # Sin precio: el notional se calcula con el ultimo precio conocido.
        c = make_connector(price=100.0)
        result = c.place_order('BTCUSDT', 'BUY', quantity=0.01)  # 1 USDT
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('MIN_NOTIONAL', result['message'])

        c2 = make_connector(price=100.0)
        result2 = c2.place_order('BTCUSDT', 'BUY', quantity=0.10)  # 10 USDT
        self.assertNotEqual(result2['status'], 'ERROR')

    def test_sin_filtros_no_se_inventa_un_minimo(self):
        c = make_connector(filters=[LOT_SIZE])
        result = c.place_order('BTCUSDT', 'BUY', quantity=0.01, price=100)
        self.assertNotEqual(result['status'], 'ERROR')

    def test_el_lot_size_sigue_aplicandose_primero(self):
        c = make_connector()
        # 0.000001 esta por debajo del minQty: el error es del LOT_SIZE.
        result = c.place_order('BTCUSDT', 'BUY', quantity=0.000001, price=100)
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('LOT_SIZE', result['message'])


if __name__ == '__main__':
    unittest.main()
