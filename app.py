"""
IntelliStock - Flask Backend
Provides stock analysis API endpoints with simulated ML predictions.
Run: pip install flask flask-cors && python app.py
"""

from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
import yfinance as yf
import math, random, datetime, time, functools, json, os

app = Flask(__name__)
app.secret_key = 'intellistock_secret_key_99' # In production, use an environment variable
CORS(app)

USERS_FILE = 'users.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# ── Auth Decorator ──────────────────────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
    "AMZN":     {"name": "Amazon.com Inc.",      "price": 185.07, "change": -2.15,  "pct": -1.15, "high52": 229.00, "low52": 151.61, "vol": "33.6M", "cap": "1.92T", "trend": "neutral"},
    "META":     {"name": "Meta Platforms",       "price": 502.30, "change": 8.45,   "pct": 1.71,  "high52": 589.60, "low52": 352.47, "vol": "18.9M", "cap": "1.28T", "trend": "bullish"},
    # 10+ Indian Companies
    "RELIANCE": {"name": "Reliance Industries",  "price": 2944.70,"change": 32.30,  "pct": 1.11,  "high52": 3100.00,"low52":2210.00, "vol": "8.9M",  "cap": "19.9LCr","trend": "bullish"},
    "TCS":      {"name": "Tata Consultancy",     "price": 3862.45,"change": 45.80,  "pct": 1.20,  "high52": 4254.00,"low52":3156.05, "vol": "2.3M",  "cap": "13.9LCr","trend": "bullish"},
    "HDFCBANK": {"name": "HDFC Bank Ltd.",       "price": 1530.45, "change": 12.30,  "pct": 0.81,  "high52": 1757.50, "low52": 1363.55, "vol": "18.2M", "cap": "11.6LCr","trend": "bullish"},
    "INFY":     {"name": "Infosys Ltd.",         "price": 1420.10, "change": -15.40, "pct": -1.07, "high52": 1733.00, "low52": 1185.00, "vol": "6.1M",  "cap": "5.9LCr", "trend": "neutral"},
    "ICICIBANK":{"name": "ICICI Bank Ltd.",      "price": 1085.20, "change": 8.15,   "pct": 0.76,  "high52": 1113.40, "low52": 820.00,  "vol": "12.5M", "cap": "7.6LCr", "trend": "bullish"},
    "HINDUNILVR":{"name": "Hindustan Unilever",  "price": 2245.60, "change": -22.40, "pct": -0.99, "high52": 2769.65, "low52": 2172.05, "vol": "1.8M",  "cap": "5.3LCr", "trend": "bearish"},
    "ITC":      {"name": "ITC Ltd.",             "price": 428.15,  "change": 2.45,   "pct": 0.58,  "high52": 499.70,  "low52": 370.00,  "vol": "14.2M", "cap": "5.3LCr", "trend": "bullish"},
    "SBIN":     {"name": "State Bank of India",  "price": 765.40,  "change": 5.20,   "pct": 0.68,  "high52": 794.60,  "low52": 501.55,  "vol": "22.8M", "cap": "6.8LCr", "trend": "bullish"},
    "BHARTIARTL":{"name": "Bharti Airtel Ltd.",  "price": 1215.30, "change": 14.50,  "pct": 1.21,  "high52": 1245.00, "low52": 735.00,  "vol": "5.4M",  "cap": "6.9LCr", "trend": "bullish"},
    "KOTAKBANK":{"name": "Kotak Mahindra Bank", "price": 1785.10, "change": -10.30, "pct": -0.57, "high52": 2063.00, "low52": 1645.00, "vol": "3.2M",  "cap": "3.5LCr", "trend": "neutral"},
    "LT":       {"name": "Larsen & Toubro",      "price": 3650.00, "change": 42.60,  "pct": 1.18,  "high52": 3738.90, "low52": 2150.00, "vol": "2.1M",  "cap": "5.1LCr", "trend": "bullish"},
    "AXISBANK": {"name": "Axis Bank Ltd.",       "price": 1050.45, "change": 4.20,   "pct": 0.40,  "high52": 1151.85, "low52": 815.00,  "vol": "8.9M",  "cap": "3.2LCr", "trend": "neutral"},
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


def build_indicators(prices: list, trend: str, ticker: str = "") -> list:
    last = prices[-1]
    rsi = compute_rsi(prices)
    macd = compute_macd(prices)
    sma20 = compute_sma(prices, 20)
    bb_upper, bb_lower = compute_bollinger(prices)
    
    currency = "₹" if ticker.endswith(".NS") or ticker.endswith(".BSE") or ticker in STOCK_DB and ticker not in ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META"] else "$"

    rsi_signal = "sell" if rsi > 70 else "buy" if rsi < 30 else "neutral-buy" if rsi > 55 else "neutral-sell" if rsi < 45 else "neutral"
    macd_signal = "buy" if macd > 0 else "sell"
    sma_signal = "buy" if last > sma20 else "sell"
    bb_signal = "sell" if last > bb_upper else "buy" if last < bb_lower else "neutral"
    vol_signal = "buy" if trend == "bullish" else "sell" if trend == "bearish" else "neutral"

    return [
        {"name": "RSI (14)",      "value": str(rsi),                    "signal": rsi_signal,  "display": str(rsi)},
        {"name": "MACD",          "value": str(macd),                   "signal": macd_signal, "display": ("+" if macd >= 0 else "") + str(macd)},
        {"name": "SMA 20",        "value": str(sma20),                  "signal": sma_signal,  "display": currency + "{:,.2f}".format(sma20)},
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

# ── View Routes ────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        if username in users and users[username]['password'] == password:
            session['user'] = username
            if 'watchlist' not in users[username]:
                users[username]['watchlist'] = []
                save_users(users)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid Operator ID or Access Code")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if not username or not password:
            return render_template('signup.html', error="Fields cannot be empty")
        if password != confirm:
            return render_template('signup.html', error="Passwords do not match")
            
        users = load_users()
        if username in users:
            return render_template('signup.html', error="Operator ID already registered")
            
        users[username] = {"password": password, "watchlist": []}
        save_users(users)
        session['user'] = username
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=session['user'])

@app.route('/analyze')
@login_required
def analyzer():
    return render_template('index.html', user=session['user'])

@app.route('/watchlist')
@login_required
def watchlist():
    return render_template('watchlist.html', user=session['user'])


@app.route('/api/analyze/<ticker>')
@login_required
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
            price = round(random.uniform(50, 3500), 2)
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
                "cap": f"{random.uniform(20, 500):.0f}Cr",
                "trend": random.choice(["bullish", "neutral", "bearish"]),
            }

        days = 90
        prices = generate_price_history(stock["price"] * 0.92, days)
        prices[-1] = stock["price"]
        labels = generate_labels(days)

    # Common analysis logic
    indicators = build_indicators(prices, stock["trend"], t_symbol)
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

@app.route('/api/get_watchlist', methods=['GET'])
@login_required
def get_watchlist_api():
    users = load_users()
    user_data = users.get(session['user'], {})
    w_list = user_data.get('watchlist', [])
    
    # Enrich watchlist with basic current data
    enriched = []
    for ticker in w_list:
        real = get_real_stock_data(ticker)
        if real:
            enriched.append(real['stock'])
        elif ticker.upper() in STOCK_DB:
            enriched.append({**STOCK_DB[ticker.upper()], "ticker": ticker.upper()})
        else:
            enriched.append({"ticker": ticker, "name": ticker, "price": 0, "change": 0, "pct": 0})
    return jsonify(enriched)

@app.route('/api/watchlist/toggle/<ticker>', methods=['POST'])
@login_required
def toggle_watchlist_item(ticker: str):
    ticker = ticker.upper()
    users = load_users()
    if session['user'] not in users:
        return jsonify({"error": "User not found"}), 404
    
    w_list = users[session['user']].get('watchlist', [])
    if ticker in w_list:
        w_list.remove(ticker)
        action = "removed"
    else:
        w_list.append(ticker)
        action = "added"
    
    users[session['user']]['watchlist'] = w_list
    save_users(users)
    return jsonify({"status": "success", "action": action, "ticker": ticker, "watchlist": w_list})

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
    return jsonify({"status": "ok", "service": "IntelliStock API", "version": "1.1.0"})


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("IntelliStock API running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
