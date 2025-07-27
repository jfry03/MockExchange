from game import Game, ConversionRequest, ConversionRequest
from base import Product
from bots import MarketMaker, RandomTrader, Reverter, Taker
from your_algo import PlayerAlgorithm  # 
import pandas as pd
import matplotlib.pyplot as plt
import json
from analytics import Analytics




uec = Product("UEC", mpv=0.1)

products = [uec]
tickers_to_products = {p.ticker: p for p in products}

with open("bot_parameters.json") as f:
    bot_params = json.load(f)


bot_type_to_class = {
    "market_maker": MarketMaker,
    "random_trader": RandomTrader,
    "reverter": Reverter,
    "taker": Taker
}

market_bots = {}
for bot_name, params in bot_params.items():
    params = params.copy()  # avoid mutating the original dict
    params["products"] = products  # replace string with Product object
    params.pop("bot_type", None)   # remove bot_type if present
    bot_class = bot_type_to_class[bot_params[bot_name]["bot_type"]]
    market_bots[bot_name] = bot_class(**params)

print(market_bots)

player_bot = PlayerAlgorithm(products)

bots = [player_bot] + list(market_bots.values())




"""
This trading game is turn based -> there is no latency effect 
i just iterate through all the different bots 
"""


g = Game(products, bots, player_bots=[player_bot.name])

"""Don't change the initialisation. Your bot needs to be a player bot; basically it
doesnt get certain information that i transfer around between the other bots to achieve effects"""

g.initialise_game()
g.play_game(20000) # 20000 just refers to the number of loops


analysis = Analytics(g, bot_params)

analysis.upload_csv("game_record.csv")
analysis.plot_results(["UEC"])





