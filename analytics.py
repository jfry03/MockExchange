import pandas as pd  
import numpy as np  
import matplotlib.pyplot as plt
from typing import List, Dict

class Analytics:
    def __init__(self, game, bot_params):
        self.game = game
        self.bot_params = bot_params
        self.results = pd.DataFrame()
        self.products = game.products
        self.tickers_to_products = {p.ticker: p for p in self.products}
        self.game_record = game.record

    def evaluate_pnl(self, bot_name):
        """Calculate PnL for a specific bot."""

        market_maker_params = self.bot_params["market_maker_params"]

        player_positions = self.game.positions[bot_name]
        cash = player_positions["Cash"]

        for ticker in player_positions:
            print(ticker)
            if ticker == "Cash":
                continue
            product = self.tickers_to_products[ticker]
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
        
        return cash
    
    def plot_results(self, stocks: List):
        """Plot the mid prices for the given stocks over time, each with its own y-axis for proper scaling."""
        df = pd.DataFrame(self.game_record)
        print(df.head(5))
        plt.figure(figsize=(12, 6))
        ax = plt.gca()
        axes = [ax]
        colors = plt.cm.tab10.colors  # Up to 10 distinct colors

        for i, stock in enumerate(stocks):
            col = f"{stock}"
            if col in df.columns:
                if i == 0:
                    axes[0].plot(df[col], label=f"{stock} mid", color=colors[i % len(colors)])
                    axes[0].set_ylabel(f"{stock} Mid Price")
                else:
                    ax_new = axes[0].twinx()
                    ax_new.plot(df[col], label=f"{stock} mid", color=colors[i % len(colors)])
                    ax_new.set_ylabel(f"{stock} Mid Price")
                    # Offset the right spine for visibility if more than 2 axes
                    ax_new.spines["right"].set_position(("outward", 60 * (i - 1)))
                    axes.append(ax_new)
            else:
                print(f"Warning: {col} not found in game record columns.")

        axes[0].set_xlabel("Time")
        plt.title("Mid Prices Over Time (Each Stock Scaled)")
        # Combine legends from all axes
        lines, labels = [], []
        for ax in axes:
            line, label = ax.get_legend_handles_labels()
            lines += line
            labels += label
        axes[0].legend(lines, labels, loc='upper left')
        plt.tight_layout()
        plt.show()

    def upload_csv(self, filename="game_record.csv"):
        """Upload the game record to a CSV file."""
        df = pd.DataFrame(self.game_record)
        df.to_csv(filename, index=False)
        print(f"Game record saved to {filename}")

