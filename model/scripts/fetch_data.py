# model/scripts/fetch_data.py
import pandas as pd
import yfinance as yf
from pandas_datareader.stooq import StooqDailyReader


def _extract_close(df: pd.DataFrame, sym: str) -> pd.DataFrame | None:
    """从 yfinance.download 的返回里抽取某个 symbol 的 Close列，兼容列分级两种形态。"""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    # MultiIndex 列：可能是 [ticker, field] 或 [field, ticker]   
    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = df.columns.get_level_values(0)
        lvl1 = df.columns.get_level_values(1)

        if sym in lvl0:  # 形态1：顶层是 ticker
            sub = df[sym]
            if "Close" in sub.columns:
                return sub[["Close"]].rename(columns={"Close": "close"})
        if sym in lvl1:  # 形态2：顶层是字段，第二层是 ticker
            sub = df.xs(sym, axis=1, level=1)
            if "Close" in sub.columns:
                return sub[["Close"]].rename(columns={"Close": "close"})
        return None

    # 非分级列：单只股票
    cols = [c for c in df.columns if str(c).lower() == "close"]
    if cols:
        return df[[cols[0]]].rename(columns={cols[0]: "close"})
    return None


def _stooq_single(sym: str, start: str | None, end: str | None) -> pd.DataFrame | None:
    """从 Stooq 兜底抓单只日线；尝试常见代码变体。返回 MultiIndex [ts,ticker] 格式。"""
    for cand in [sym, sym.upper(), f"{sym}.US", f"{sym.upper()}.US"]:
        try:
            rdr = StooqDailyReader(
                symbols=cand,
                start=pd.to_datetime(start) if start else None,
                end=pd.to_datetime(end) if end else None,
            )
            h = rdr.read()
        except Exception:
            continue
        if h is None or h.empty:
            continue

        # 多股票时是列分级；单股票时是普通列，列名一般是小写
        if isinstance(h.columns, pd.MultiIndex):
            if cand in h.columns.get_level_values(0):
                sub = h.xs(cand, axis=1, level=0)
            else:
                continue
        else:
            sub = h

        # 找 close 列（小写）
        cols = [c for c in sub.columns if str(c).lower() == "close"]
        if not cols:
            continue

        sub = sub[[cols[0]]].copy()
        sub = sub.sort_index()
        sub.columns = ["close"]
        sub["ret"] = sub["close"].pct_change()
        sub["ticker"] = sym  # 用原始 symbol 作为标识
        sub.index.name = "ts"
        return sub.reset_index().set_index(["ts", "ticker"])
    return None


def fetch_prices(symbols: list[str], start: str | None, end: str | None) -> pd.DataFrame:
    """
    极简版：优先 yfinance; 失败则按 symbol 逐只用 Stooq 兜底。
    MultiIndex [ts, ticker]，列=['close','ret']。
    """
    frames: list[pd.DataFrame] = []

    # 1) yfinance 批量尝试（一次）
    try:
        bulk = yf.download(
            tickers=" ".join(symbols),
            start=start, end=end,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=False,
            repair=True,
            progress=False,
        )
        for sym in symbols:
            sub = _extract_close(bulk, sym)
            if sub is None or sub.empty:
                continue
            sub = sub.sort_index()
            sub["ret"] = sub["close"].pct_change()
            sub["ticker"] = sym
            sub.index.name = "ts"
            frames.append(sub.reset_index().set_index(["ts", "ticker"]))
    except Exception:
        pass  # 网络/服务异常，直接走兜底

    # 2) 对缺的 symbol 用 Stooq 兜底（逐只）
    have = set(pd.concat(frames).index.get_level_values("ticker").unique()) if frames else set()
    for sym in symbols:
        if sym in have:
            continue
        sub = _stooq_single(sym, start, end)
        if sub is not None and not sub.empty:
            frames.append(sub)

    if not frames:
        # 留给调用方决定是否跳过测试
        raise RuntimeError(f"No price data downloaded for {symbols}. Check network or date range.")

    out = pd.concat(frames).sort_index()
    out = out[out["close"] > 0]
    return out
