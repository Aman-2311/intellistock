# IntelliStock 📈

IntelliStock is a premium, professional-grade stock analysis and forecasting platform. It combines real-time financial data with AI-driven sentiment analysis to provide actionable insights for traders and investors.

## ✨ Key Features

- **Real-Time Data Feed**: Live prices, changes, and market stats powered by `yfinance`.
- **AI-Backed Predictions**: Market forecasts (1W, 1M, 3M) derived from professional analyst consensus and historical performance.
- **Strategic Projection Terminal**: Calculate potential ROI and lot sizes based on different market scenarios (Bull, Bear, Base).
- **Personalized Watch List**: Save and track your favorite assets with local persistence.
- **Multi-Page Platform**: Includes a premium Login portal, a central Dashboard, and a specialized Analysis tool.
- **Global Asset Support**: Automatically handles currency detection (₹ for NSE/BSE, $ for US markets).
- **Stunning UI**: A high-end, cyberpunk-fintech design system built with custom Vanilla CSS.

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Locally**:
   ```bash
   python app.py
   ```

3. **Access Terminal**:
   Open `http://localhost:5000` and enter any credentials to access the command center.

## 📦 Deployment

The project is pre-configured for containerized deployment (e.g., Railway, Heroku) with:
- `Procfile`: Gunicorn production server.
- `Dockerfile`: Multi-stage build for rapid deployment.
- `.dockerignore`: Environment optimization.

---
*Disclaimer: System predictions are for informational purposes only and do not constitute financial advice.*
