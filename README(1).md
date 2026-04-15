# 📈 IntelliStock — AI Stock Predictor

A full-stack stock price prediction web app with signal indicators and a future return calculator.

---

## 🗂 Project Structure

```
intellistock/
├── index.html       ← Frontend (standalone, works without backend too)
├── app.py           ← Flask backend (API server)
├── requirements.txt ← Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### Option A — Frontend Only (No Python needed)
Just open `index.html` in any browser. Works completely standalone.

### Option B — Full Stack (Flask Backend)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python app.py

# 3. Open browser
http://localhost:5000
```

---

## 🌐 Deployment

### Netlify / GitHub Pages (Frontend Only)
1. Upload `index.html` to your repo
2. Enable GitHub Pages or drag-drop to Netlify
3. Done — no server needed!

### Render.com / Railway (Full Stack)
1. Push to GitHub
2. Create new Web Service → connect repo
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `python app.py`
5. Deploy!

---

## ✨ Features
- 🔍 **Stock Analysis** — Search any ticker (AAPL, TSLA, RELIANCE, TCS, etc.)
- 📊 **Live Chart** — Price history + prediction overlay (1W / 1M / 3M)
- ⚡ **Signal Indicator** — Visual gauge: Strong Buy → Strong Sell
- 📐 **Technical Indicators** — RSI, MACD, SMA 20, Bollinger Bands, Volume Trend
- 🎯 **Price Targets** — AI-predicted 1W, 1M, 3M targets with confidence score
- 💰 **Return Calculator** — Enter investment amount + period + scenario → get projected returns

---

## ⚠️ Disclaimer
> IntelliStock is for **educational purposes only**. Predictions are simulated and do not constitute financial advice. Always do your own research before investing.

---

Made with ❤️ for learning | Stack: HTML · CSS · JS · Chart.js · Python · Flask
