import re
from collections import defaultdict

import ccxt
import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    ExchangeSymbolsNotFound
from catalyst.exchange.exchange_utils import mixin_market_params

log = Logger('CCXT', level=LOG_LEVEL)


class CCXT(Exchange):
    def __init__(self, exchange_name, key, secret, base_currency,
                 portfolio=None):
        log.debug('available exchanges:\n{}'.format(ccxt.exchanges))
        self.api = ccxt.poloniex({
            'apiKey': key,
            'secret': secret,
        })
        markets = self.api.load_markets()
        log.debug('the markets:\n{}'.format(markets))

        self.name = exchange_name
        self.assets = {}
        self.load_assets()
        self.base_currency = base_currency
        self._portfolio = portfolio
        self.transactions = defaultdict(list)

        self.num_candles_limit = 2000
        self.max_requests_per_minute = 60
        self.request_cpt = dict()

        self.bundle = ExchangeBundle(self.name)

    def account(self):
        return None

    def time_skew(self):
        return None

    def get_symbol(self, asset):
        parts = asset.symbol.split('_')
        return '{}/{}'.format(parts[0].upper(), parts[1].upper())

    def get_timeframe(self, freq):
        freq_match = re.match(r'([0-9].*)?(m|M|d|D|h|H|T)', freq, re.M | re.I)
        if freq_match:
            candle_size = int(freq_match.group(1)) \
                if freq_match.group(1) else 1

            unit = freq_match.group(2)

        else:
            raise InvalidHistoryFrequencyError(frequency=freq)

        if unit.lower() == 'd':
            timeframe = '{}d'.format(candle_size)

        elif unit.lower() == 'm' or unit == 'T':
            timeframe = '{}m'.format(candle_size)

        elif unit.lower() == 'h' or unit == 'T':
            timeframe = '{}h'.format(candle_size)

        return timeframe

    def get_candles(self, freq, assets, bar_count=None, start_dt=None,
                    end_dt=None):
        symbols = self.get_symbols(assets)
        timeframe = self.get_timeframe(freq)
        delta = start_dt - pd.to_datetime('1970-1-1', utc=True)
        ms = int(delta.total_seconds()) * 1000

        ohlcvs = self.api.fetch_ohlcv(
            symbol=symbols[0],
            timeframe=timeframe,
            since=ms,
            limit=bar_count,
            params={}
        )

        candles = []
        for ohlcv in ohlcvs:
            candles.append(dict(
                last_traded=pd.to_datetime(ohlcv[0], unit='ms', utc=True),
                open=ohlcv[1],
                high=ohlcv[2],
                low=ohlcv[3],
                close=ohlcv[4],
                volume=ohlcv[5]
            ))
        return candles

    def load_assets(self, is_local=False):
        markets = self.api.fetch_markets()
        try:
            symbol_map = self.fetch_symbol_map(is_local)
        except ExchangeSymbolsNotFound:
            return None

        data_source = 'local' if is_local else 'catalyst'
        for market in markets:
            asset = symbol_map[market['id']] \
                if market['id'] in markets else None

            params = dict(exchange=self.name, data_source=data_source)
            mixin_market_params(params, market)

            if asset:
                params['symbol'] = asset['symbol']

                params['start_date'] = pd.to_datetime(
                    asset['start_date'], utc=True
                ) if 'start_date' in asset else None

                params['end_date'] = pd.to_datetime(
                    asset['end_date'], utc=True
                ) if 'end_date' in asset else None

                params['leverage'] = asset['leverage'] \
                    if 'leverage' in asset else 1.0

                params['asset_name'] = asset['asset_name'] \
                    if 'asset_name' in asset else None

                params['end_daily'] = pd.to_datetime(
                    asset['end_daily'], utc=True
                ) if 'end_daily' in asset and asset['end_daily'] != 'N/A' \
                    else None

                params['end_minute'] = pd.to_datetime(
                    asset['end_minute'], utc=True
                ) if 'end_minute' in asset and asset['end_minute'] != 'N/A' \
                    else None

            else:
                params['symbol'] = market['id']

            trading_pair = TradingPair(**params)
            if is_local:
                self.local_assets[market['id']] = trading_pair
            else:
                self.assets[market['id']] = trading_pair

    def get_balances(self):
        return None

    def create_order(self, asset, amount, is_buy, style):
        return None

    def get_open_orders(self, asset):
        return None

    def get_order(self, order_id):
        return None

    def cancel_order(self, order_param):
        return None

    def tickers(self, assets):
        return None

    def get_account(self):
        return None

    def get_orderbook(self, asset, order_type, limit):
        return None