from game import Game, ConversionRequest, ConversionRequest
from base import Product
from bots import MarketMaker, RandomTrader, Reverter, Taker
from your_algo import PlayerAlgorithm  # 

import pandas as pd
import matplotlib.pyplot as plt


uec = Product("UEC", mpv=0.1)

products = [uec]
tickers_to_products = {p.ticker: p for p in products}

market_maker_params = {"products": products, "name": "market_maker", "mids": {"UEC": 1000}, "mpv_frequencies": {"UEC": 10}, "level_size": {"UEC": 20}, "initial_width": {"UEC": 20}, "level_count": 20}
r1_params = {"products": products, "name": "customer_flow1", "max_sizes": {"UEC": 50}, "sizing_factor": 1000, "freq": 0.2}
r2_params = {"products": products, "name": "customer_flow2", "max_sizes": {"UEC": 20}, "sizing_factor": 2000, "freq": 0.3}
reverter_params = {"products": products, "name": "rev", "sizing_factor": {"UEC": 5000}, "freq": {"UEC": 0.4}, "sentiment_influence": {"UEC": 0.015}, "max_sizes": {"UEC": 80}}
taker_params = {"products": products, "name": "whale", "sizing_factor": {"UEC": 100000}, "freq": {"UEC": 0.001}, "sentiment_influence": {"UEC": -0.3}, "max_levels": {"UEC": 18}}

mm_bot = MarketMaker(**market_maker_params)
r1_bot = RandomTrader(**r1_params)
r2_bot = RandomTrader(**r2_params)
reverter_bot = Reverter(**reverter_params)
taker_bot = Taker(**taker_params)

player_bot = PlayerAlgorithm()

"""
This trading game is turn based -> there is no latency effect 
i just iterate through all the different bots 
"""



g = Game(products, [player_bot, r1_bot, r2_bot, reverter_bot, taker_bot, mm_bot], exempt_bots=["market_maker", "whale", "customer_flow1", "customer_flow2", "rev"], player_bots=[player_bot.name])

"""Don't change the initialisation. Your bot needs to be a player bot; basically it
doesnt get certain information that i transfer around between the other bots to achieve effects"""

g.initialise_game()
g.play_game(20000) # 20000 just refers to the number of loops

player_positions = g.positions[player_bot.name]
cash = player_positions["Cash"]

for ticker in player_positions:
    product = tickers_to_products[ticker]
    if ticker != "Cash":
        """going to equalise as per the mm market impact. This seems pretty necesssary 
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



