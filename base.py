from typing import List
from time import time

from rich.console import Console
from rich.table import Table


class Order:
    """
    Order object representing an incoming market order.
    """
    MAPPING = {"Buy": 1, "Sell": -1}

    def __init__(self, ticker: str, price: float, size: int, order_id: int, agg_dir: str, bot_name: str):
        self.ticker = ticker
        self.price = price
        self.size = size
        self.order_id = order_id
        self.agg_dir = agg_dir
        self.bot_name = bot_name
        self.aggness = self.price * Order.MAPPING[self.agg_dir]

    def __str__(self):
        return f'{self.bot_name} wants to {self.agg_dir} at {self.price}'


class Trade:
    """
    Trade object for record-keeping executed trades.
    """
    def __init__(self, price: float, size: int, ticker: str,
                 agg_order_id: int, rest_order_id: int,
                 agg_dir: str, agg_bot: str, rest_bot: str):
        self.ticker = ticker
        self.price = price
        self.size = size
        self.agg_order_id = agg_order_id
        self.agg_dir = agg_dir
        self.rest_order_id = rest_order_id
        self.trade_time = time()
        self.agg_bot = agg_bot
        self.rest_bot = rest_bot

    def __str__(self):
        return f'{self.ticker} traded at {self.price}'


class Product:
    """
    Product metadata container (tick size, limits, etc.)
    """
    def __init__(self, ticker: str, mpv: float = 1, lot_size: int = 1,
                 pos_limit=None, min_price=0, max_price=None, conversions=None):
        self.ticker = ticker
        self.pos_limit = pos_limit
        self.min_price = min_price
        self.max_price = max_price
        self.mpv = mpv
        self.lot_size = lot_size
        self.conversions = conversions or {}

    def __str__(self):
        return self.ticker
    
    def set_lore(self, lore):
        self.lore = lore
        

class Rest:
    """
    Resting order in the order book.
    """
    def __init__(self, size: int, price: float, order_id: int,
                 ticker: str, aggness: float, bot_name: str):
        self.size = size
        self.price = price
        self.order_id = order_id
        self.ticker = ticker
        self.aggness = aggness
        self.bot_name = bot_name

    def __str__(self):
        return f"Price: {self.price}, Size: {self.size}"


class Exchange:
    """
    Exchange object. An exchange can hold a variety of products
    """
    def __init__(self, products: List[Product]):
        self.products = products
        self.ticker_to_product = {p.ticker: p for p in self.products}
        self.book = {p.ticker: {"Bids": [], "Asks": []} for p in self.products}
        self.trade_log = []
        self.mapping = {"Buy": 1, "Sell": -1}
        self.name_mapping = {"Buy": "Bids", "Sell": "Asks"}
        self.order_ids = {}  # order_id → [ticker, side]
        self.action_log = []
    
    def process_order(self, loop_num, order: Order) -> List[Trade]:

        if order.order_id in self.order_ids.keys():
            raise ValueError("Already Seen OrderId. Please ensure that a new OrderId has been generated")
        with open("orders.txt", "a") as f:
            f.write(str(order) + ' ' + str(loop_num) + ' ' + "\n")
        trades = []
        book = self.book[order.ticker]
        side_to_match = "Asks" if order.agg_dir == "Buy" else "Bids" # what side of the book to look at to try and match
        opposing_book = book[side_to_match]
        while order.size > 0 and opposing_book:
            rest = opposing_book[0]
            price_match = (rest.price <= order.price+0.000001) if order.agg_dir == "Buy" else (rest.price >= order.price-0.000001)
            if not price_match:
                break

            trade_size = min(order.size, rest.size)
            trade = self.record_trade(rest.price, trade_size, order, rest)
            trades.append(trade)

            order.size -= trade_size
            rest.size -= trade_size

            if rest.size == 0:
                opposing_book.pop(0)

        if order.size > 0:
            self.add_order(order)

        return trades

    def record_trade(self, price: float, size: int, order: Order, rest: Rest) -> Trade:
        trade = Trade(
            price=price,
            size=size,
            ticker=order.ticker,
            agg_order_id=order.order_id,
            rest_order_id=rest.order_id,
            agg_dir=order.agg_dir,
            agg_bot=order.bot_name,
            rest_bot=rest.bot_name
        )
        self.trade_log.append(trade)
        return trade

    def remove_order(self, order_id: int) -> bool:
        """
        Need the order_id to cancel an order. Have stored the path in self.order_ids
        """
        info = self.order_ids.get(order_id)
        if not info:
            return False
        ticker, side = info
        book = self.book[ticker][side]
        for idx, rest in enumerate(book):
            if rest.order_id == order_id:
                book.pop(idx)
                return "Order Cancelled"
        return "Cancellation Failed"

    def add_order(self, order: Order):
        
        self.order_ids[order.order_id] = [order.ticker, self.name_mapping[order.agg_dir]] #mapping to help with removal
        rest = Rest(order.size, order.price, order.order_id, order.ticker,
                    order.price * self.mapping[order.agg_dir], order.bot_name)

        book = self.book[order.ticker]["Bids"] if order.agg_dir == "Buy" else self.book[order.ticker]["Asks"]

        for idx, item in enumerate(book):
            if order.aggness > item.aggness:
                book.insert(idx, rest)
                return
            elif order.aggness == item.aggness:
                insert_idx = idx
                while insert_idx + 1 < len(book) and book[insert_idx + 1].aggness == order.aggness:
                    insert_idx += 1
                book.insert(insert_idx + 1, rest)
                return

        book.append(rest)

    def display_book(self):
        console = Console()
        for ticker, sides in self.book.items():
            table = Table(title=f"Order Book for {ticker}", show_lines=True)

            # Columns: Bot | Size | Price || Price | Size | Bot
            table.add_column("Bot (Bid)", justify="left", style="green")
            table.add_column("Size", justify="right", style="green")
            table.add_column("Price", justify="right", style="green")

            table.add_column("Price", justify="left", style="red")
            table.add_column("Size", justify="left", style="red")
            table.add_column("Bot (Ask)", justify="left", style="red")

            bids = sides.get("Bids", [])
            asks = sides.get("Asks", [])
            max_len = max(len(bids), len(asks))
            bids += [None] * (max_len - len(bids))
            asks += [None] * (max_len - len(asks))

            for bid, ask in zip(bids, asks):
                bid_bot = bid.bot_name if bid else ""
                bid_size = str(bid.size) if bid else ""
                bid_price = f"{bid.price:.2f}" if bid else ""

                ask_price = f"{ask.price:.2f}" if ask else ""
                ask_size = str(ask.size) if ask else ""
                ask_bot = ask.bot_name if ask else ""

                table.add_row(bid_bot, bid_size, bid_price, ask_price, ask_size, ask_bot)

            console.print(table)




if __name__ == "__main__":


    p1 = Product("UEC")
    exchange = Exchange([p1])

    new_order = Order("UEC", 150, 5, 1, "Sell", "j")
    exchange.add_order(new_order)


    exchange.display_book()
    print(exchange.trade_log)


    print("I Made A Change")
