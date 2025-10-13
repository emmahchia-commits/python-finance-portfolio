import pandas as pd
import yfinance as yf
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

tickers = [ # Used ChatGPT to create a list of 10 tickers
    "AAPL",  # Apple - Technology / Consumer
    "MSFT",  # Microsoft - Technology / Cloud
    "AMZN",  # Amazon - Consumer / Cloud
    "GOOGL", # Alphabet - Internet / Ads
    "TSLA",  # Tesla - EV / Auto
    "NVDA",  # Nvidia - Semiconductors / AI
    "JPM",   # JPMorgan Chase - Banking / Financials
    "JNJ",   # Johnson & Johnson - Healthcare
    "XOM",   # Exxon Mobil - Energy / Oil & Gas
    "BAC"    # Bank of America - Financials / Retail banking
]
weights = [0.2,0.05,0.05,0.1,0.05,0.3,0.1,0.05,0.05,0.05]
start_date, end_date = "2023-01-01", "2025-10-08"
benchmark = "^GSPC"

def fetch_prices(tickers, start_date, end_date):
    comps = yf.download(tickers, start_date, end_date)
    prices = comps["Close"]
    return prices

def fetch_benchmark(benchmark, star_date, end_date):
    benchmark = yf.download(benchmark, start_date, end_date)
    benchmark_prices = benchmark["Close"]
    return benchmark_prices

def daily_returns(prices):
    daily_returns = prices.pct_change().dropna()
    return daily_returns

def portfolio_returns(daily_returns, weight):
    returns = daily_returns * weight
    portfolio_returns = returns.sum(axis =1)
    return portfolio_returns

def annualised_return(r, time):
    annualised_return = (1+r).prod()**(252/len(r)) - 1
    return annualised_return

def annualised_vol(portfolio_returns):
    annualised_vol = portfolio_returns.std()*252**(1/2)
    return annualised_vol

def sharpe_ratio(r,rf,vol):
    sharpe_ratio = (r-rf)/vol # With rf 10Y treasury bill
    return sharpe_ratio

def equity(r):
    equity = (1+r).cumprod()
    equity = equity/equity.iloc[0]
    return equity

def equity_curve(equity):
    plt.figure(figsize=(10, 6))
    equity.plot()
    plt.title("Cumulative Return: Portfolio vs $1 Start")
    plt.ylabel("Growth of $1")
    plt.xlabel("Date")
    plt.tight_layout()
    plt.savefig("cum_returns.png")
    plt.show()
    
def drawdown(equity):
    peak = equity.cummax()
    drawdown = equity/peak-1
    max_dd = drawdown.min()
    return drawdown, max_dd

def drawdown_curve(drawdown):
    plt.figure(figsize=(10, 3.6))
    drawdown.plot()
    plt.title("Portfolio Drawdown")
    plt.ylabel("Drawdown")
    plt.xlabel("Date")
    plt.tight_layout()
    plt.savefig("drawdown.png")
    plt.show()



prices_df = fetch_prices(tickers, start_date, end_date)
benchmark_prices_df = fetch_benchmark(benchmark, start_date, end_date)
daily_rets = daily_returns(prices_df)    
daily_benchmark_rets = daily_returns(benchmark_prices_df)   
port_rets = portfolio_returns(daily_rets, weights)    

ann_ret = annualised_return(port_rets, 252)           
ann_vol = annualised_vol(port_rets)
sr = sharpe_ratio(ann_ret, 0.04059, ann_vol)

be_eq = equity(daily_benchmark_rets)
eq = equity(port_rets)    
total_eq = pd.concat([eq, be_eq], axis =1).rename(columns = {0:"Portfolio","^GSPC":"S&P 500"})                       
dd_series, max_dd = drawdown(eq)                     

equity_curve(total_eq)
drawdown_curve(dd_series)

