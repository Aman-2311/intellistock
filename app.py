"""
IntelliStock - Flask Backend
Provides stock analysis API endpoints with simulated ML predictions.
Run: pip install flask flask-cors && python app.py
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import yfinance as yf
import math, random, datetime, time

app = Flask(__name__)
CORS(app)

# ── Cache Layer ───────────────────────────────────────────────────────────────
STOCK_CACHE = {} # ticker -> {data, timestamp}
CACHE_EXPIRY = 300 # 5 minutes

# ── Mock Stock Data (Fallback) ────────────────────────────────────────────────
STOCK_DB = {
    "AAPL":     {"name": "Apple Inc.",          "price": 189.84, "change": 2.31,   "pct": 1.23,  "high52": 199.62, "low52": 164.08, "vol": "58.2M", "cap": "2.94T", "trend": "bullish"},
    "TSLA":     {"name": "Tesla Inc.",           "price": 248.50, "change": -5.20,  "pct": -2.05, "high52": 488.54, "low52": 138.80, "vol": "92.1M", "cap": "795B",  "trend": "neutral"},
    "NVDA":     {"name": "NVIDIA Corp.",         "price": 875.39, "change": 18.62,  "pct": 2.17,  "high52": 974.00, "low52": 462.42, "vol": "41.8M", "cap": "2.15T", "trend": "bullish"},
    "MSFT":     {"name": "Microsoft Corp.",      "price": 415.22, "change": 3.85,   "pct": 0.94,  "high52": 468.35, "low52": 362.90, "vol": "22.4M", "cap": "3.08T", "trend": "bullish"},
    "GOOGL":    {"name": "Alphabet Inc.",        "price": 172.63, "change": 1.42,   "pct": 0.83,  "high52": 193.31, "low52": 130.67, "vol": "24.6M", "cap": "2.15T", "trend": "bullish"},
    "RELIANCE": {"name": "Reliance Industries",  "price": 1294.70,"change": -12.30, "pct": -0.94, "high52": 1608.95,"low52":1175.00, "vol": "8.9M",  "cap": "17.5LCr","trend": "neutral"},
    "TCS":      {"name": "Tata Consultancy",     "price": 3562.45,"change": 45.80,  "pct": 1.30,  "high52": 4592.25,"low52":3056.05, "vol": "2.3M",  "cap": "12.9LCr","trend": "bullish"},
    "AMZN":     {"name": "Amazon.com Inc.",      "price": 185.07, "change": -2.15,  "pct": -1.15, "high52": 229.00, "low52": 151.61, "vol": "33.6M", "cap": "1.92T", "trend": "neutral"},
    "META":     {"name": "Meta Platforms",       "price": 502.30, "change": 8.45,   "pct": 1.71,  "high52": 589.60, "low52": 352.47, "vol": "18.9M", "cap": "1.28T", "trend": "bullish"},
}

# ── Real Data Integration ─────────────────────────────────────────────────────

def format_number(num):
    if num is None: return "N/A"
    if num >= 1e12: return f"{num/1e12:.2f}T"
    if num >= 1e9: return f"{num/1e9:.2f}B"
    if num >= 1e6: return f"{num/1e6:.2f}M"
    return f"{num:,.0f}"

def get_real_stock_data(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        
        # Historical data for labels/prices
        hist = t.history(period="3mo")
        if hist.empty: raise ValueError("No history found")
        
        prices = [round(float(p), 2) for p in hist['Close'].tolist()]
        labels = [d.strftime("%b %d") for d in hist.index]
        
        price = info.get('currentPrice') or info.get('regularMarketPrice') or prices[-1]
        prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose') or prices[-2]
        change = round(price - prev_close, 2)
        pct = round((change / prev_close) * 100, 2) if prev_close else 0
        
        trend = "bullish" if pct > 0.5 else "bearish" if pct < -0.5 else "neutral"
        
        return {
            "stock": {
                "name": info.get('shortName') or info.get('longName') or ticker_symbol,
                "ticker": ticker_symbol,
                "price": price,
                "change": change,
                "pct": pct,
                "high52": info.get('fiftyTwoWeekHigh') or "N/A",
                "low52": info.get('fiftyTwoWeekLow') or "N/A",
                "vol": format_number(info.get('volume')),
                "cap": format_number(info.get('marketCap')),
                "trend": trend,
                "analystTargets": {
                    "mean": info.get('targetMeanPrice'),
                    "high": info.get('targetHighPrice'),
                    "count": info.get('numberOfAnalystOpinions')
                },
                "recommendation": info.get('recommendationKey')
            },
            "prices": prices,
            "labels": labels
        }
    except Exception as e:
        print(f"Error fetching real data for {ticker_symbol}: {e}")
        return None

# ── Utilities ──────────────────────────────────────────────────────────────────
def generate_price_history(base_price: float, days: int) -> list:
    prices = [base_price]
    for _ in range(1, days):
        drift = (random.random() - 0.48) * 0.025
        prices.append(round(prices[-1] * (1 + drift), 2))
    return prices


def generate_labels(days: int) -> list:
    labels = []
    today = datetime.date.today()
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        labels.append(d.strftime("%b %d"))
    return labels


def compute_rsi(prices: list, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(-period, 0):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    rs = gains / (losses if losses > 0 else 1e-9)
    return round(100 - 100 / (1 + rs), 2)


def compute_sma(prices: list, period: int) -> float:
    window = prices[-period:] if len(prices) >= period else prices
    return round(sum(window) / len(window), 2)


def compute_macd(prices: list) -> float:
    ema12 = compute_sma(prices, 12)
    ema26 = compute_sma(prices, 26)
    return round(ema12 - ema26, 2)


def compute_bollinger(prices: list, period: int = 20):
    window = prices[-period:] if len(prices) >= period else prices
    mean = sum(window) / len(window)
    std = math.sqrt(sum((p - mean) ** 2 for p in window) / len(window))
    return round(mean + 2 * std, 2), round(mean - 2 * std, 2)


def build_indicators(prices: list, trend: str) -> list:
    last = prices[-1]
    rsi = compute_rsi(prices)
    macd = compute_macd(prices)
    sma20 = compute_sma(prices, 20)
    bb_upper, bb_lower = compute_bollinger(prices)

    rsi_signal = "sell" if rsi > 70 else "buy" if rsi < 30 else "neutral-buy" if rsi > 55 else "neutral-sell" if rsi < 45 else "neutral"
    macd_signal = "buy" if macd > 0 else "sell"
    sma_signal = "buy" if last > sma20 else "sell"
    bb_signal = "sell" if last > bb_upper else "buy" if last < bb_lower else "neutral"
    vol_signal = "buy" if trend == "bullish" else "sell" if trend == "bearish" else "neutral"

    return [
        {"name": "RSI (14)",      "value": str(rsi),                    "signal": rsi_signal,  "display": str(rsi)},
        {"name": "MACD",          "value": str(macd),                   "signal": macd_signal, "display": ("+" if macd >= 0 else "") + str(macd)},
        {"name": "SMA 20",        "value": str(sma20),                  "signal": sma_signal,  "display": "$" + "{:,.2f}".format(sma20)},
        {"name": "Bollinger B.",  "value": f"{bb_lower}–{bb_upper}",   "signal": bb_signal,   "display": f"{bb_lower}–{bb_upper}"},
        {"name": "Volume Trend",  "value": trend,                       "signal": vol_signal,  "display": trend.upper()},
    ]


def signal_score(indicators: list) -> int:
    weights = {"buy": 80, "neutral-buy": 60, "neutral": 50, "neutral-sell": 40, "sell": 20}
    return round(sum(weights.get(i["signal"], 50) for i in indicators) / len(indicators))


def score_to_label(score: int) -> str:
    if score >= 75: return "STRONG BUY"
    if score >= 60: return "BUY"
    if score >= 45: return "NEUTRAL"
    if score >= 30: return "SELL"
    return "STRONG SELL"


def predict_prices(base: float, trend: str, targets: dict = None) -> dict:
    # Use real analyst targets if available
    if targets and targets.get('mean'):
        mean = targets['mean']
        # Smooth the movement for different periods
        r1w = round(base + (mean - base) * 0.25, 2)
        r1m = round(base + (mean - base) * 0.70, 2)
        r3m = round(mean, 2)
        
        # Confidence based on number of analysts or set a high floor for professional data
        count = targets.get('count', 0)
        confidence = min(95, 65 + (count // 10)) if count else random.randint(70, 85)
    else:
        # Fallback to simulation
        bias = 1.025 if trend == "bullish" else 0.975 if trend == "bearish" else 1.0
        r1w = round(base * (bias + (random.random() - 0.3) * 0.02), 2)
        r1m = round(base * (bias ** 4 + (random.random() - 0.3) * 0.05), 2)
        r3m = round(base * (bias ** 12 + (random.random() - 0.3) * 0.10), 2)
        confidence = random.randint(55, 85)
        
    return {"r1w": r1w, "r1m": r1m, "r3m": r3m, "confidence": confidence}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze/<ticker>')
def analyze(ticker: str):
    t_symbol = ticker.upper()
    
    # 1. Check Cache
    if t_symbol in STOCK_CACHE:
        cached = STOCK_CACHE[t_symbol]
        if time.time() - cached['timestamp'] < CACHE_EXPIRY:
            return jsonify(cached['data'])

    # 2. Try Real Data
    real_data = get_real_stock_data(t_symbol)
    
    if real_data:
        stock = real_data["stock"]
        prices = real_data["prices"]
        labels = real_data["labels"]
    else:
        # 3. Fallback to Simulation
        t = t_symbol.replace(".NS", "").replace(".BSE", "")
        if t in STOCK_DB:
            stock = {**STOCK_DB[t], "ticker": t}
        else:
            price = round(random.uniform(50, 350), 2)
            change = round((random.random() - 0.48) * price * 0.04, 2)
            stock = {
                "name": t + " Corp.",
                "ticker": t,
                "price": price,
                "change": change,
                "pct": round(change / price * 100, 2),
                "high52": round(price * 1.35, 2),
                "low52": round(price * 0.72, 2),
                "vol": f"{random.uniform(5, 80):.1f}M",
                "cap": f"{random.uniform(20, 500):.0f}B",
                "trend": random.choice(["bullish", "neutral", "bearish"]),
            }

        days = 90
        prices = generate_price_history(stock["price"] * 0.92, days)
        prices[-1] = stock["price"]
        labels = generate_labels(days)

    # Common analysis logic
    indicators = build_indicators(prices, stock["trend"])
    score = signal_score(indicators)
    
    # Refine score with analyst recommendation if available
    rec = stock.get('recommendation')
    if rec:
        rec_boost = {"strong_buy": 15, "buy": 10, "hold": 0, "underperform": -10, "sell": -20}.get(rec, 0)
        score = max(5, min(95, score + rec_boost))

    label = score_to_label(score)
    prediction = predict_prices(stock["price"], stock["trend"], stock.get('analystTargets'))

    result = {
        "stock": stock,
        "prices": prices[-30:],
        "labels": labels[-30:],
        "indicators": indicators,
        "signal": {"score": score, "label": label},
        "prediction": prediction,
        "source": "api" if real_data else "simulated"
    }
    
    # Update Cache
    STOCK_CACHE[t_symbol] = {'data': result, 'timestamp': time.time()}
    
    return jsonify(result)



@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        amount = float(data.get("amount", 0))
        period = data.get("period", "1m")
        scenario = data.get("scenario", "base")
        trend = data.get("trend", "neutral")
        current_price = float(data.get("currentPrice", 100))

        if amount <= 0:
            return jsonify({"error": "Amount must be greater than zero"}), 400
            
        if current_price <= 0:
            return jsonify({"error": "Invalid current price"}), 400

        # Calculation logic
        trend_rate = 0.22 if trend == "bullish" else -0.08 if trend == "bearish" else 0.10
        period_mul = {"1w": 1/52, "1m": 1/12, "3m": 3/12, "6m": 6/12, "1y": 1.0}.get(period, 1/12)

        growth = trend_rate * period_mul
        if scenario == "bull":
            growth += 0.30 * period_mul
        elif scenario == "bear":
            growth -= 0.20 * period_mul

        future_value = round(amount * (1 + growth), 2)
        profit = round(future_value - amount, 2)
        return_pct = round(growth * 100, 2)
        shares = int(amount // current_price)

        return jsonify({
            "futureValue": future_value,
            "profit": profit,
            "returnPct": return_pct,
            "shares": shares,
        })
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input format: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500



@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "service": "IntelliStock API", "version": "1.0.0"})


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("IntelliStock API running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
