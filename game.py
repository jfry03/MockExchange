# pyright: ignore[reportMissingImports]
import matplotlib.pyplot as plt
import math
import numpy as np
import pandas as pd

from base import Exchange, Trade, Order, Product, Rest
from bots import RandomTrader, MarketMaker, Taker, Reverter

import random
from time import time


class ConversionRequest:
    def __init__(self, start_ticker, end_ticker, quantity):
        self.start_ticker = start_ticker
        self.end_ticker = end_ticker
        self.quantity = quantity


class Convert:
    def __init__(self):
        pass


class Game:
    def __init__(self, products, bots, exempt_bots=[], player_bots = [], pos_limit_type="SOFT", sentiments=None):
        self.pos_limit_type = pos_limit_type
        self.exchange = Exchange(products)
        self.bots = {bot.name: bot for bot in bots}
        self.positions = {bot.name: {product.ticker: 0 for product in products} for bot in bots}
        self.products = products
        self.ticker_to_product = {p.ticker: p for p in self.products}
        self.exempt_bots = exempt_bots
        self.player_bots = player_bots
        self.whale_trades = []
        for bot in self.positions:
            self.positions[bot]['Cash'] = 0
        
        self.trades = []

        self.mapping = {"Buy": 1, "Sell": -1}

        if sentiments is None:
            self.sentiments = {product.ticker: 0 for product in products}
        else:
            self.sentiments = sentiments
        
        self.track_realisation = []

        self.realisation = {product.ticker: 0 for product in products}

        self.trade_log = []

        # ========== Mids and Sentiments Tracking =========
        self.record = {}
        for product in products:
            self.record[product.ticker] = []
        for bot in self.bots:
            for product in products:

                self.record[f"{bot}_{product.ticker}"] = []
            self.record[f"{bot}_Cash"] = []
        self.record["Loop"] = []

        for product in products:
            self.record[f"Realisation_{product.ticker}"] = []
            self.record[f"Sentiment_{product.ticker}"] = []
    
    def anonymise_trades(self, trades, bot_name):
        anonymised_trades = []
        for trade in trades:
            if trade.agg_bot == bot_name:
                anonymised_trade = Trade(
                    ticker=trade.ticker,
                    price=trade.price,
                    size=trade.size,
                    agg_order_id=trade.agg_order_id,
                    agg_dir=trade.agg_dir,
                    rest_order_id="Anonymised",  
                    agg_bot=bot_name,  
                    rest_bot="Anonymised"  
                )
            elif trade.rest_bot == bot_name:
                anonymised_trade = Trade(
                    ticker=trade.ticker,
                    price=trade.price,
                    size=trade.size,
                    agg_order_id="Anonymised",
                    agg_dir=trade.agg_dir,
                    rest_order_id=trade.rest_order_id,
                    agg_bot="Anonymised",  # Anonymise the other bot
                    rest_bot=bot_name  # Keep the bot name
                )
            else:
                anonymised_trade = Trade(
                    ticker=trade.ticker,
                    price=trade.price,
                    size=trade.size,
                    agg_order_id="Anonymised",
                    agg_dir=trade.agg_dir,
                    rest_order_id="Anonymised",
                    agg_bot="Anonymised",  # Anonymise both bots
                    rest_bot="Anonymised"
                )
            anonymised_trades.append(anonymised_trade)
        return anonymised_trades
  
    def initialise_game(self):
        start_idx = 0
        for bot in self.bots.values():
            bot.set_idx(start_idx)
            start_idx += 10e6
        
    def play_game(self, iterations):
        self.initialise_game()
        for idx in range(iterations):
            self.game_loop(idx)

    def record_state(self, loop_num):
        for product in self.products:
            # Append the mid price for the product
            if self.exchange.book[product.ticker]["Bids"] and self.exchange.book[product.ticker]["Asks"]:
                mid_price = (self.exchange.book[product.ticker]["Bids"][0].price + self.exchange.book[product.ticker]["Asks"][0].price) / 2

                self.record[product.ticker].append(mid_price)
            else:
                self.record[product.ticker].append(None)
            self.record[f"Realisation_{product.ticker}"].append(self.realisation[product.ticker])
            self.record[f"Sentiment_{product.ticker}"].append(self.sentiments[product.ticker])
        
        for bot_name, bot in self.bots.items():
            for product in self.products:
                self.record[f"{bot_name}_{product.ticker}"].append(self.positions[bot_name][product.ticker])
            self.record[f"{bot_name}_Cash"].append(self.positions[bot_name]['Cash'])
        
        self.record["Loop"].append(loop_num)      


    def game_loop(self, loop_num):
        
        for bot_name, bot in self.bots.items():
            # ===== Get Messages from Bot =====
            if bot_name in self.player_bots:
                messages = bot.send_messages(self.exchange.book)
            else:
                messages, self.sentiments, self.realisation = bot.send_messages(self.exchange.book, self.sentiments, self.realisation, loop_num)

            for msg in messages:
                trades = []
                if msg.msg_type == "ORDER":
                    order = msg.message
                    if self.validate_order(order):
                        # ===== Get Trades so that the bots can then process them =====
                        trades += self.exchange.process_order(loop_num, order)

                        for other_bot in self.bots.values():
                            if other_bot.name in self.player_bots:
                                # Anonymise trades for player bots
                                anonymised_trades = self.anonymise_trades(trades, other_bot.name)
                                other_bot.process_trades(anonymised_trades)
                            else:
                                self.realisation = other_bot.process_trades(trades, self.realisation)

                        self.track_positions(trades)

                if msg.msg_type == "CONVERSION":
                    convert = msg.message
                    if self.validate_conversion(convert):
                        converts = self.perform_conversion(convert)
                        if hasattr(bot, "process_conversions"):
                            bot.process_conversions(converts)

                if msg.msg_type == "REMOVE":
                    order_id = msg.message
                    self.exchange.remove_order(order_id)

        self.record_state(loop_num)


    def validate_conversion(self, convert):
        return True  # stub for now

    def validate_order(self, order):
        product = self.ticker_to_product[order.ticker]
        ratio = order.price / product.mpv
        if not math.isclose(ratio, round(ratio), abs_tol=1e-6):
            raise ValueError(f"Order {order.order_id} violates MPV for {order.ticker} ({order.price} not a multiple of {product.mpv})")
        if product.max_price is not None and order.price > product.max_price:
            raise ValueError(f"Order {order.order_id} price exceeds max for {order.ticker}")
        if product.min_price is not None and order.price < product.min_price:
            raise ValueError(f"Order {order.order_id} price below min for {order.ticker}")

        if self.pos_limit_type == "SOFT":
            if not self.soft_limit(order):
                raise ValueError(f"Order {order.order_id} exceeds soft limit")
        elif self.pos_limit_type == "HARD":
            if not self.hard_limit(order):
                raise ValueError(f"Order {order.order_id} exceeds hard limit")

        return True

    def soft_limit(self, order):
        return True
        """
        product = self.ticker_to_product[order.ticker]
        pos_lim = product.pos_limit
        if pos_lim is None or order.bot_name in self.exempt_bots:
            return True
        real_size = self.mapping[order.agg_dir] * order.size
        current_pos = self.positions[order.bot_name][order.ticker]
        new_pos = current_pos + real_size
        return -pos_lim <= new_pos <= pos_lim

        """

    def hard_limit(self, order):
        return False  # implement as neededs
    
    def record_trades(self, trades, iteration):
        for trade in trades:
            self.trade_log.append((iteration, trade))
        


    def track_positions(self, trades):
        for trade in trades:
            ticker = trade.ticker
            agg_bot = trade.agg_bot
            rest_bot = trade.rest_bot
            agg_dir = trade.agg_dir
            size = trade.size
            price = trade.price

            self.positions[agg_bot][ticker] += size * self.mapping[agg_dir]
            self.positions[rest_bot][ticker] -= size * self.mapping[agg_dir]

            self.positions[agg_bot]['Cash'] -= size * self.mapping[agg_dir] * price
            self.positions[rest_bot]['Cash'] += size * self.mapping[agg_dir] * price

    def validate_positions(self):
        pass  # placeholder



