"""Market-data retrieval through yfinance for a personal prototype."""
from datetime import datetime
import config
import utils

try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception:
    YF_AVAILABLE = False


def _history(symbol, period="2mo"):
    if not YF_AVAILABLE:
        return None
    try:
        data = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
        if data is None or data.empty or "Close" not in data:
            return None
        data = data.dropna(subset=["Close"])
        return None if data.empty else data
    except Exception as exc:
        utils.log(f"[MARKET] {symbol} failed: {exc}")
        return None


def _metrics(data):
    result = {
        "latest": None, "prev": None, "session_date": None, "retrieved_at": utils.now_local().isoformat(),
        "ret_1d": None, "ret_5d": None, "ret_mtd": None, "above_ma20": None,
    }
    if data is None:
        return result
    closes = data["Close"]
    result["latest"] = float(closes.iloc[-1])
    result["session_date"] = closes.index[-1].date()
    if len(closes) >= 2:
        result["prev"] = float(closes.iloc[-2])
        result["ret_1d"] = utils.safe_return(result["latest"], result["prev"])
    if len(closes) >= 6:
        result["ret_5d"] = utils.safe_return(result["latest"], float(closes.iloc[-6]))
    if len(closes) >= 20:
        result["above_ma20"] = result["latest"] >= float(closes.iloc[-20:].mean())
    try:
        index = closes.index[-1]
        month = closes[(closes.index.month == index.month) & (closes.index.year == index.year)]
        result["ret_mtd"] = utils.safe_return(result["latest"], float(month.iloc[0]))
    except Exception:
        pass
    return result


def _group(mapping, period, kind):
    output = {}
    utils.log(f"[MARKET] Fetching {kind}...")
    for name, metadata in mapping.items():
        symbol = metadata if isinstance(metadata, str) else metadata["symbol"]
        item = _metrics(_history(symbol, period))
        item["symbol"] = symbol
        if isinstance(metadata, dict):
            item.update({key: metadata[key] for key in ("base", "quote", "decimals")})
        output[name] = item
    return output


def get_equities():
    return _group(config.EQUITY_TICKERS, "2mo", "equity indices")


def get_fx():
    return _group(config.FX_PAIRS, "1mo", "FX pairs")


def get_rates():
    # Yahoo currently returns these directly in percentage points: 4.70 means 4.70%.
    return _group(config.RATE_TICKERS, "1mo", "Treasury rates")


def get_all_market_data():
    equities, fx, rates = get_equities(), get_fx(), get_rates()
    dates = [item["session_date"] for group in (equities, fx, rates) for item in group.values() if item.get("session_date")]
    return {
        "equities": equities, "fx": fx, "rates": rates,
        "session_date": max(dates) if dates else None,
        "retrieved_at": utils.now_local().isoformat(),
        "data_ok": any(item.get("latest") is not None for group in (equities, fx, rates) for item in group.values()),
    }
