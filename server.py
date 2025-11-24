from typing import Any, Dict, Optional
import os

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Tokens de API
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN", "")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# Criar servidor MCP
mcp = FastMCP(
    "united-exchange-investments",
    stateless_http=True,
    json_response=True,
)

async def _get(url: str, params: Dict[str, Any]):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()

# ----------- BRASIL (B3) --------------

@mcp.tool()
async def b3_quote(ticker: str):
    url = f"https://brapi.dev/api/quote/{ticker}"
    params = {"range": "1d", "interval": "1d", "token": BRAPI_TOKEN}
    data = await _get(url, params)

    result = data["results"][0]
    return {
        "ticker": result["symbol"],
        "price": result["regularMarketPrice"],
        "change_percent": result["regularMarketChangePercent"],
        "currency": result["currency"],
        "exchange": result["exchangeName"],
    }

# ----------- EUA (Stocks / ETFs) ------------

@mcp.tool()
async def us_equity(symbol: str):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "apikey": ALPHAVANTAGE_API_KEY
    }
    data = await _get(url, params)
    ts = data["Time Series (Daily)"]
    last_date = sorted(ts.keys())[-1]
    d = ts[last_date]
    return {
        "symbol": symbol,
        "date": last_date,
        "close": d["4. close"],
        "high": d["2. high"],
        "low": d["3. low"],
        "volume": d["6. volume"],
    }

# ----------- TREASURIES (FRED API) ------------

@mcp.tool()
async def treasury_yield(tenor: int):
    series = {2:"DGS2", 5:"DGS5", 10:"DGS10", 30:"DGS30"}[tenor]
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series,
        "api_key": FRED_API_KEY,
        "file_type": "json"
    }
    data = await _get(url, params)
    return data["observations"][-1]

# ----------- FX USD/BRL ------------

@mcp.tool()
async def usdbrl():
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": "USD",
        "to_currency": "BRL",
        "apikey": ALPHAVANTAGE_API_KEY
    }
    data = await _get(url, params)
    info = data["Realtime Currency Exchange Rate"]
    return {
        "rate": info["5. Exchange Rate"],
        "time": info["6. Last Refreshed"]
    }

# Rodar MCP
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
