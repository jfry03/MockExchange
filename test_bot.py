from bots import Msg
from base import Exchange, Trade, Order, Product

class PlayerAlgorithm:
    def __init__(self, products):
        self.products = products
        """
        products is the list of products you'll be trading. View the product type in 
        base.py to see exactly what info this contains
        """
        self.name = "PlayerAlgorithm"
        self.mids = {product.ticker: [] for product in products}

    def send_messages(self, book):
        # All parties in the book are anonymised, except for your own bot. 
        self.record_prices(book)
        """
        So the book is of form {ticker: {Bid: [resting_orders], Ask: [resting_orders]}}. 
        The resting orders are most aggressive -> least aggresive
        The orders are of the Rest class (view base.py). 
        """

        """
        Put all of the messages you want to send in the list messages, and then return messages
        There are two types of messages (at the moment)
        These are orders, and cancels, which are both wrapped in the messages type
        For sending orders to the exchange view the order type in base.py

        The msg class is literally just
        class Msg:
            def __init__(self, msg_type, message):
                self.msg_type = msg_type
                self.message = message
                
        , where the message is literally the order object is msg_type == "ORDER"
        , or the order_id you'd previously sent if the msg_type == "REMOVE"   
        """
        messages = []
        return messages
    
    def record_prices(self, book):
        """Record the mid prices for each product in the book."""
        for ticker, data in book.items():
            if data['Bids'] and data['Asks']:
                mid_price = (data['Bids'][0].price + data['Asks'][0].price) / 2
                self.mids[ticker].append(mid_price)   
        return None
    
    def set_idx(self, idx):
        """ok so you get set a certain index, this is just the order id, and every order 
        must have a unique id to be able to cancel basically. Basically just increment this 
        by 1 every trade and send it with the order"""
        self.idx = idx
    
    def process_trades(self, trades):
        pass