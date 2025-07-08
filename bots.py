from base import Exchange, Trade, Order, Product
import random
import numpy as np


class Msg:
    def __init__(self, msg_type, message):
        self.msg_type = msg_type
        self.message = message




class MarketMaker:
    def __init__(self, products, name, mids, mpv_frequencies, level_size, initial_width = 0, realisation_effect = None, level_count = 5):
        self.mpv_frequencies = mpv_frequencies
        self.mids = mids
        self.level_size = level_size
        self.initial_width_mpv = initial_width
        self.level_count = level_count

        self.positions = {p.ticker: 0 for p in products}
        self.positions['Cash'] = 0

        self.products = products
        self.ticker_to_product = {p.ticker: p for p in products}
        self.tickers = {p.ticker for p in self.products}


    
        self.trades = {}
        self.name = name

        self.open_orders = {ticker: {} for ticker in self.tickers}
        self.mapping = {"Buy": 1, "Sell": -1}
        self.reset_status()
        self.sent_orders = {t: [] for t in self.tickers}

        if realisation_effect is None:
            self.realisation_effect = {p.ticker: 0.005 for p in products}
        else:
            self.realisation_effect = realisation_effect
    def reset_status(self):
        self.status = {ticker: True for ticker in self.tickers}
        self.status["Cash"] = True
    
    def set_idx(self, idx):
        self.idx = idx
        
    def send_messages(self, book_state, sentiments, realisation, loop_num):
        

        outputs = []
        for ticker in self.tickers:

            if self.status[ticker]:

                desired_mid = self.mids[ticker] - self.positions[ticker]/self.level_size[ticker] * (self.mpv_frequencies[ticker] * self.ticker_to_product[ticker].mpv)
                desired_mid = self.round_to_mpv(desired_mid, self.ticker_to_product[ticker].mpv)

                for id in self.sent_orders[ticker]:
                    removal = Msg("REMOVE", id)
                    outputs.append(removal)

                self.sent_orders[ticker] = []
                
                for i in range(0,self.level_count):
                    bid_price = desired_mid - i * self.mpv_frequencies[ticker] * self.ticker_to_product[ticker].mpv - self.initial_width_mpv[ticker] * self.ticker_to_product[ticker].mpv
                    if bid_price > 0:
                        bid_price = self.round_to_mpv(bid_price, self.ticker_to_product[ticker].mpv)
                        bid = Order(ticker, bid_price, self.level_size[ticker], self.idx, "Buy", self.name)

                        outputs += [Msg("ORDER", bid)]
                        self.sent_orders[ticker].append(self.idx)
                        self.idx += 1
                    

                    sell_price = max(10, desired_mid + i*self.mpv_frequencies[ticker] * self.ticker_to_product[ticker].mpv + self.initial_width_mpv[ticker] * self.ticker_to_product[ticker].mpv)
                    sell_price = self.round_to_mpv(sell_price, self.ticker_to_product[ticker].mpv)
                    ask = Order(ticker, sell_price, self.level_size[ticker], self.idx, "Sell", self.name)

                    outputs += [Msg("ORDER", ask)]
                    self.sent_orders[ticker].append(self.idx)

                    self.idx += 1


        return outputs, sentiments, realisation
                
    @staticmethod
    def round_to_mpv(num, interval):
        result = round(num / interval) * interval
        return round(result, 4)


    def process_trades(self, trades, realisation):
        for trade in trades:
            if trade.agg_bot == self.name:
                mm_dir = self.mapping[trade.agg_dir]
            elif trade.rest_bot == self.name:
                mm_dir = -self.mapping[trade.agg_dir]
            else:
                return realisation
            self.positions[trade.ticker] += trade.size * mm_dir
            if mm_dir == 1: # MM has bought
                if realisation[trade.ticker] <= -0.01:
                    realisation[trade.ticker] += trade.size * self.realisation_effect[trade.ticker]
            elif mm_dir == -1: # MM has sold
                if realisation[trade.ticker] >= 0.01:
                    realisation[trade.ticker] -= trade.size * self.realisation_effect[trade.ticker]

            if -0.05 < realisation[trade.ticker] < 0.001:
                realisation[trade.ticker] = 0.0
    
        return realisation







class RandomTrader:
    """
    This bot just trades a certain amount of each product at random intervals, without caring about the book state.
    """
    def __init__(self, products, name, max_sizes, bias = None, sentiment_limits = None, sentiment_effect = None, sentiment_influence = None, sizing_factor=1.0, freq=1.0, remove=True):
        self.products = products
        self.tickers_to_products_ = {p.ticker: p for p in products}
        self.sizing_factor = sizing_factor
        self.freq = freq
        self.name = name
        self.remove = remove
        self.positions = {p.ticker: 0 for p in products}
        self.mapping = {"Buy": 1, "Sell": -1}
        self.sent_orders = []
        self.max_sizes = max_sizes



        if bias is None:
            self.bias = {p.ticker: 0.5 for p in products}
        else:
            self.bias = bias
        if sentiment_limits is None:
            self.sentiment_limits = {p.ticker: 0.0 for p in products}
        else:
            self.sentiment_limits = sentiment_limits

        if sentiment_effect is None:
            self.sentiment_effect = {p.ticker: 0.0 for p in products}
        else:
            self.sentiment_effect = sentiment_effect

        if sentiment_influence is None:
            self.sentiment_influence = {p.ticker: 0.0 for p in products}
        else:
            self.sentiment_influence = sentiment_influence
    
    @staticmethod
    def sentiment_mapping(self, x):
        if x > 0.02 or x < -0.02:
           return x
        return 0.0
        
    def set_idx(self, idx):
        self.idx = idx

    def send_messages(self, book_state, sentiments, realisation, loop_num):
        messages = []



        if self.remove:
            for id in self.sent_orders:
                removal = Msg("REMOVE", id)
                messages.append(removal)
        self.sent_orders = []

        for ticker in book_state:
            
            if realisation[ticker] > 0.01 and book_state[ticker]["Asks"]:
                correction_order = Order(ticker, book_state[ticker]["Asks"][0].price, int(np.random.normal(book_state[ticker]["Asks"][0].size, 2)), self.idx, "Buy", self.name)
                messages.append(Msg("ORDER", correction_order))
                self.sent_orders.append(self.idx)
                self.idx += 1
                continue
            elif realisation[ticker] < -0.01 and book_state[ticker]["Bids"]:

                correction_order = Order(ticker, book_state[ticker]["Bids"][0].price, int(np.random.normal(book_state[ticker]["Bids"][0].size, 2)), self.idx, "Sell", self.name)
                messages.append(Msg("ORDER", correction_order))
                self.sent_orders.append(self.idx)
                self.idx += 1
                continue
            
            if random.random() > self.freq:
                continue  # skip this tick. This just determines how frequently the bot trades
            if abs(sentiments[ticker]) < self.sentiment_limits[ticker]:
                print(loop_num)
                continue
            product = self.tickers_to_products_[ticker]
            if book_state[ticker]["Bids"] and book_state[ticker]["Asks"]:
                spread = book_state[ticker]["Asks"][0].price - book_state[ticker]["Bids"][0].price
                if spread <= 0:
                    continue

                spread_mpvs = spread / product.mpv

                trade_dir = random.choices(["Buy", "Sell"], weights=[self.bias[ticker] + sentiments[ticker] * self.sentiment_effect[ticker], 1 - self.bias[ticker] - sentiments[ticker] * self.sentiment_effect[ticker]])[0]
                trade_size = self.determine_sizing(spread_mpvs, ticker)
                    
                if trade_dir == "Sell":
                    price = self.round_to_mpv(book_state[ticker]["Bids"][0].price * 0.9, product.mpv)
                    order = Order(ticker, price, trade_size, self.idx, "Sell", self.name)
                    sentiments[ticker] += self.sentiment_influence[ticker]


                elif trade_dir == "Buy":
                    price = self.round_to_mpv(book_state[ticker]["Asks"][0].price * 1.1, product.mpv)
                    order = Order(ticker, price, trade_size, self.idx, "Buy", self.name)
                    sentiments[ticker] -= self.sentiment_influence[ticker]

                messages.append(Msg("ORDER", order))
                self.sent_orders.append(self.idx)
                self.idx += 1

            elif book_state[ticker]["Asks"]:
                spread = book_state[ticker]["Asks"][0].price
                trade_size = self.determine_sizing(spread / product.mpv, ticker)
                messages.append(Msg("ORDER", Order(ticker, spread, trade_size, self.idx, "Buy", self.name)))
                self.idx += 1
                self.sent_orders.append(self.idx)
            sentiments[ticker] = self.round_sentiment(sentiments[ticker])
        return messages, sentiments, realisation
    
    @staticmethod
    def round_to_mpv(num, interval):
        result = round(num / interval) * interval
        return round(result, 4)
    
    
    @staticmethod
    def round_sentiment(x):
        if x > 0.5:
            return 0.5
        if x < -0.5:
            return 0.5
        return x
    
    def determine_sizing(self, spread_mpv, ticker):
        mean_size = min(self.sizing_factor / max(spread_mpv, 1e-6), self.max_sizes[ticker])
        sampled_size = np.random.exponential(mean_size)
        return max(1, int(sampled_size))  # Ensure at least size 1

    def process_trades(self, trades, realisation):
        for trade in trades:
            if trade.agg_bot == self.name:
                self.positions[trade.ticker] += trade.size * self.mapping[trade.agg_dir]
            elif trade.rest_bot == self.name:
                self.positions[trade.ticker] -= trade.size * self.mapping[trade.agg_dir]
        return realisation
    
    def process_conversions(self, conversion):
        pass

class Reverter:
    def __init__(self, products, name, max_sizes = None, bias=None, sizing_factor=1.0, sentiment_influence=0.0, freq=0.01):
        self.products = products
        self.name = name
        self.tickers_to_products_ = {p.ticker: p for p in products}
        self.positions = {p.ticker: 0 for p in products}
        self.mapping = {"Buy": 1, "Sell": -1}
        self.sent_orders = []
        self.max_sizes = max_sizes if max_sizes is not None else {p.ticker: 50 for p in products}
        # Per-ticker parameters
        tickers = [p.ticker for p in products]
        self.bias = bias if bias is not None else {t: 0.5 for t in tickers}
        self.sizing_factor = sizing_factor if sizing_factor is not None else {t: 1.0 for t in tickers}
        self.sentiment_influence = sentiment_influence if sentiment_influence is not None else {t: 0.0 for t in tickers}
        self.freq = freq if freq is not None else {t: 0.01 for t in tickers}

    def set_idx(self, idx):
        self.idx = idx
    
    def send_messages(self, book_state, sentiments, realisation, loop_num):
        messages = []
        for ticker in book_state:
            if sentiments[ticker] < 0.05 and sentiments[ticker] > -0.05:
                continue
            if random.random() > self.freq[ticker]:
                continue
            trade_dir = random.choices(
                ["Buy", "Sell"],
                weights=[self.bias[ticker] + 2*sentiments[ticker], 1 - self.bias[ticker] - 2*sentiments[ticker]]
            )[0]
            product = self.tickers_to_products_[ticker]
            if book_state[ticker]["Bids"] == [] or book_state[ticker]["Asks"] == []:
                continue
            spread_mpv = (book_state[ticker]["Asks"][0].price - book_state[ticker]["Bids"][0].price) / product.mpv
            trade_size = self.determine_sizing(spread_mpv, ticker)
            if trade_dir == "Buy":
                price = self.round_to_mpv(book_state[ticker]["Asks"][0].price * 1.1, product.mpv)
                order = Order(ticker, price, trade_size, self.idx, "Buy", self.name)
                sentiments[ticker] -= self.sentiment_influence[ticker]
            else:  # Sell
                price = self.round_to_mpv(book_state[ticker]["Bids"][0].price * 0.9, product.mpv)
                order = Order(ticker, price, trade_size, self.idx, "Sell", self.name)
                sentiments[ticker] += self.sentiment_influence[ticker]
            messages.append(Msg("ORDER", order))
            self.sent_orders.append(self.idx)
            self.idx += 1
        sentiments[ticker] = self.round_sentiment(sentiments[ticker])
        return messages, sentiments, realisation

    def determine_sizing(self, spread_mpv, ticker):
        mean_size = min(self.sizing_factor[ticker] / max(spread_mpv, 1e-6), self.max_sizes[ticker])
        sampled_size = np.random.exponential(mean_size)
        return max(1, int(sampled_size))  # Ensure at least size 1
    @staticmethod
    def round_to_mpv(num, interval):
        result = round(num / interval) * interval
        return round(result, 4)
    @staticmethod
    def round_sentiment(x):
        if x > 0.5:
            return 0.5
        if x < -0.5:
            return 0.5
        return x

    def process_trades(self, trades, realisation):
        for trade in trades:
            if trade.agg_bot == self.name:
                self.positions[trade.ticker] += trade.size * self.mapping[trade.agg_dir]
            elif trade.rest_bot == self.name:
                self.positions[trade.ticker] -= trade.size * self.mapping[trade.agg_dir]
        return realisation

class Taker:
    """
    Taker bot with per-ticker parameters, similar to RandomTrader.
    """
    def __init__(
        self,
        products,
        name,
        bias=None,
        sizing_factor=None,
        sentiment_influence=None,
        freq=None,
        max_levels=None,
    ):
        self.products = products
        self.name = name
        self.tickers_to_products_ = {p.ticker: p for p in products}
        self.positions = {p.ticker: 0 for p in products}
        self.mapping = {"Buy": 1, "Sell": -1}
        self.sent_orders = []

        # Per-ticker parameters
        tickers = [p.ticker for p in products]
        self.bias = bias if bias is not None else {t: 0.5 for t in tickers}
        self.sizing_factor = sizing_factor if sizing_factor is not None else {t: 1.0 for t in tickers}
        self.sentiment_influence = sentiment_influence if sentiment_influence is not None else {t: 0.0 for t in tickers}
        self.freq = freq if freq is not None else {t: 0.01 for t in tickers}
        self.max_levels = max_levels if max_levels is not None else {t: 3 for t in tickers}

        self.realisation_effect = 1
    def set_idx(self, idx):
        self.idx = idx

    def send_messages(self, book_state, sentiments, realisation, loop_num):
        messages = []
        for id in self.sent_orders:
            removal = Msg("REMOVE", id)
            messages.append(removal)
        self.sent_orders = []
        for ticker in book_state:
            if random.random() > self.freq[ticker]:
                continue
            if realisation[ticker] != 0:
                continue
            if sentiments[ticker] > 0.05 or sentiments[ticker] < -0.05:
                continue

            product = self.tickers_to_products_[ticker]
            trade_dir = random.choices(
                ["Buy", "Sell"],
                weights=[self.bias[ticker], 1 - self.bias[ticker]]
            )[0]
            max_levels = self.max_levels[ticker]
            total_size = 0
            price = None
            book_density = 0
            if trade_dir == "Buy":
                asks = book_state[ticker]["Asks"][:max_levels]
                for ask in asks:
                    book_density += ask.size
                    price = ask.price  # last price in loop is deepest
                if book_density > 0:
                    price_spread = abs(price - book_state[ticker]["Bids"][0].price)/product.mpv + 10
                    size = book_density * self.sizing_factor[ticker] * 1/price_spread
                    size = int(np.random.normal(size, 1))
                    order = Order(ticker, price, size, self.idx, "Buy", self.name)
                    messages.append(Msg("ORDER", order))
                    self.sent_orders.append(self.idx)
                    self.idx += 1
                    sentiments[ticker] -= self.sentiment_influence[ticker]
                    realisation[ticker] += self.realisation_effect
            else:  # Sell
                bids = book_state[ticker]["Bids"][:max_levels]
                for bid in bids:
                    book_density += bid.size
                    price = bid.price
                if book_density  > 0:
                    price_spread = abs(price - book_state[ticker]["Asks"][0].price)/product.mpv + 10
                    size = book_density * self.sizing_factor[ticker] * 1/price_spread
                    size = int(np.random.normal(size, 1))
                    order = Order(ticker, price, size, self.idx, "Sell", self.name)
                    messages.append(Msg("ORDER", order))
                    self.sent_orders.append(self.idx)
                    self.idx += 1
                    sentiments[ticker] += self.sentiment_influence[ticker]
                    realisation[ticker] -= self.realisation_effect
            self.sent_orders.append(self.idx)
        return messages, sentiments, realisation

    def process_trades(self, trades, realisation):
        for trade in trades:
            if trade.agg_bot == self.name:
                self.positions[trade.ticker] += trade.size * self.mapping[trade.agg_dir]
            elif trade.rest_bot == self.name:
                self.positions[trade.ticker] -= trade.size * self.mapping[trade.agg_dir]
        return realisation
    
    def process_conversions(self, conversion):
        pass