"""
Yahoo Finance から分足 OHLCV を取得して Grafana 用に返す。
- 1m: 直近 7 日以内
- 5m: 直近 60 日以内
タイムスタンプはダッシュボードの固定時間軸（今日 9:00-16:00 JST）に
合わせて日付シフト済み（epoch ms）で返す。
"""
from fastapi import APIRouter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import httpx

router = APIRouter()

JST = ZoneInfo("Asia/Tokyo")
UTC = ZoneInfo("UTC")

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


@router.get("/api/ohlcv")
async def get_ohlcv(code: str, date: str):
    """
    code: 証券コード（例: 8136）
    date: YYYY-MM-DD
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return []

    today_jst = datetime.now(JST).date()
    days_ago = (today_jst - target_date).days

    if days_ago <= 7:
        interval = "1m"
    elif days_ago <= 60:
        interval = "5m"
    else:
        return []

    ticker = f"{code}.T"
    period1 = int(datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=JST).timestamp())
    period2 = int(datetime(target_date.year, target_date.month, target_date.day, 23, 59, tzinfo=JST).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={period1}&period2={period2}&interval={interval}"
    )

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=_HEADERS, timeout=10)
        except Exception:
            return []

    if resp.status_code != 200:
        return []

    data = resp.json()
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result or not result.get("timestamp"):
        return []

    timestamps = result["timestamp"]
    quotes = result["indicators"]["quote"][0]
    shift = timedelta(days=days_ago)
    rows = []

    for i, ts in enumerate(timestamps):
        o = quotes["open"][i]
        h = quotes["high"][i]
        l = quotes["low"][i]
        c = quotes["close"][i]
        if any(x is None for x in [o, h, l, c]):
            continue
        dt_shifted = datetime.fromtimestamp(ts, JST) + shift
        time_str = dt_shifted.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append({
            "time": time_str,
            "open": round(o, 1),
            "high": round(h, 1),
            "low": round(l, 1),
            "close": round(c, 1),
        })

    return rows
