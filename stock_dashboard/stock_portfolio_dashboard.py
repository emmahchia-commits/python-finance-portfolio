import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns


def fetch_stock_data(tickers, start_date, end_date): #fetching data
    stock_data = yf.download(tickers, start=start_date, end=end_date)
    if 'Adj Close' in stock_data.columns:
        prices = stock_data['Adj Close']
    else:
        prices = stock_data['Close']
    return prices

def calculate_portfolio_metrics(prices): #calculating relevant metrics
    returns = prices.pct_change()
    return returns

def plot_stock_trends(prices,title):
    normalized = prices / prices.iloc[0] * 100   # re-index to 100 at start
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=normalized)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Indexed Price (Start = 100)")
    plt.tight_layout()
    plt.show()

stock_data = fetch_stock_data(["AAPL", "NVDA"], start_date="2025-01-01", end_date="2025-10-08")

pf_metrics = calculate_portfolio_metrics(stock_data)

plot_stock_trends(stock_data,"Stock Price Trends for AAPL and NVDA")


