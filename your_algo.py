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

    def send_messages(self, book):
        # All parties in the book are anonymised, except for your own bot. 

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
    
    def set_idx(self, idx):
        """ok so you get set a certain index, this is just the order id, and every order 
        must have a unique id to be able to cancel basically. Basically just increment this 
        by 1 every trade and send it with the order"""
        self.idx = idx
    
    def process_trades(self, trades):
        """You will get a list of trade objects that occurred. Use this to keep track of 
        trading activities. Bot names are hidden when they are not you, as well as the order ids
        The trades are of the Trades class (view base.py)"""
        pass