from fastapi import FastAPI, File, UploadFile, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx

from importer import run_import
from daytrade_importer import run_daytrade_import
from chart_router import router as chart_router

app = FastAPI()
app.include_router(chart_router)
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


SYMBOLS = {
    "nikkei": "%5EN225",
    "sp500":  "%5EGSPC",
}

@app.get("/market/{index}")
async def market_data(index: str, from_ts: int = Query(alias="from"), to_ts: int = Query(alias="to")):
    symbol = SYMBOLS.get(index)
    if not symbol:
        return JSONResponse({"error": "unknown index"}, status_code=400)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={from_ts // 1000}&period2={to_ts // 1000}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    data = resp.json()
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result or not result.get("timestamp"):
        return []
    timestamps = result["timestamp"]
    prices = result["indicators"]["adjclose"][0]["adjclose"]
    return [{"time": ts * 1000, "value": round(p, 2)} for ts, p in zip(timestamps, prices) if p is not None]


@app.post("/upload/daytrade", response_class=HTMLResponse)
async def upload_daytrade(request: Request, file: UploadFile = File(...)):
    result = None
    error = None
    try:
        content = await file.read()
        result = run_daytrade_import(file.filename, content)
    except Exception as e:
        error = str(e)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": result,
        "error": error,
    })


@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)):
    result = None
    error = None

    try:
        content = await file.read()
        result = run_import(file.filename, content)
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": result,
        "error": error,
    })
