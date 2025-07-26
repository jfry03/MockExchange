from game import Game, ConversionRequest, ConversionRequest
from base import Product
from bots import MarketMaker, RandomTrader, Reverter, Taker
from your_algo import PlayerAlgorithm  # 
import pandas as pd
import matplotlib.pyplot as plt
import json



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


market_maker_params = bot_params["market_maker_params"]


player_positions = g.positions[player_bot.name]
cash = player_positions["Cash"]

for ticker in player_positions:
    print(ticker)
    if ticker == "Cash":
        continue
    product = tickers_to_products[ticker]
    """going to equaliseas per the mm market impact. This seems pretty necesssary 
    as I've got no position limits so otherwise you could do some weird stuff and 
    trade like 100% of the volume i think idk but this is preventative and reasonable"""
    if player_positions[ticker] > 0:
        best_ask = g.exchange.display_book()[ticker]["Asks"][0]
        first_trade_price = best_ask.price
        # so level_size every mpv_frequencies * product.mpv
        level_spacing = product.mpv * market_maker_params["mpv_frequencies"][ticker]
        worst_trade_price = first_trade_price - level_spacing/market_maker_params["level_size"][ticker]
        cash += player_positions[ticker] * (first_trade_price + worst_trade_price) / 2
    elif player_positions[ticker] < 0:
        best_bid = g.exchange.display_book()[ticker]["Bids"][0]
        first_trade_price = best_bid.price
        level_spacing = product.mpv * market_maker_params["mpv_frequencies"][ticker]
        worst_trade_price = first_trade_price + level_spacing/market_maker_params["level_size"][ticker]
        cash -= player_positions[ticker] * (first_trade_price + worst_trade_price) / 2

print(f"Final Cash: {cash}")                                                                              

df = pd.DataFrame(g.record)
df.to_csv("game_record.csv", index=False) 


g.exchange.display_book()


    
plt.plot(df["UEC"], linewidth=0.2, label="Mid Price")
plt.show()



