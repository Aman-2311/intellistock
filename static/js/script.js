// ── State ──────────────────────────────────────────────
let currentStockData = null; 
let priceChart = null;
let currentPeriod = '1W';
let watchList = JSON.parse(localStorage.getItem('watchlist') || '[]');

// ── API Integration ───────────────────────────────────
async function analyzeStock() {
  const tickerInput = document.getElementById('tickerInput');
  const ticker = tickerInput.value.trim().toUpperCase();
  if (!ticker) { showToast('Please enter a stock symbol'); return; }

  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('mainContent').style.display = 'grid';
  document.getElementById('chartLoader').classList.add('active');

  try {
    const response = await fetch(`/api/analyze/${ticker}`);
    if (!response.ok) throw new Error('Failed to fetch analysis');
    
    const data = await response.json();
    currentStockData = data;
    updateUI(data);
    updateWatchBtn();
  } catch (error) {
    console.error(error);
    showToast('Error: ' + error.message);
  } finally {
    document.getElementById('chartLoader').classList.remove('active');
  }
}

function updateUI(data) {
  const { stock, prices, labels, indicators, signal, prediction } = data;
  const currency = stock.ticker.endsWith('.NS') || stock.ticker.endsWith('.BSE') ? '₹' : '$';

  // Update Stock Info
  document.getElementById('stockName').textContent = stock.name;
  document.getElementById('stockTicker').textContent = stock.ticker;
  document.getElementById('stockPrice').textContent = currency + stock.price.toLocaleString();
  
  const chEl = document.getElementById('priceChange');
  chEl.textContent = (stock.change >= 0 ? '+' : '') + stock.change + ' (' + (stock.pct >= 0 ? '+' : '') + stock.pct + '%)';
  chEl.className = 'price-change ' + (stock.change >= 0 ? 'up' : 'down');

  document.getElementById('high52').textContent = currency + stock.high52.toLocaleString();
  document.getElementById('low52').textContent = currency + stock.low52.toLocaleString();
  document.getElementById('volume').textContent = stock.vol;
  document.getElementById('mktCap').textContent = stock.cap;

  // Signal Indicator
  const needlePos = (signal.score / 100 * 100) + '%';
  document.getElementById('signalNeedle').style.left = needlePos;
  
  const badge = document.getElementById('signalBadge');
  badge.textContent = signal.label;
  const labelColor = getLabelColor(signal.label);
  badge.style.background = labelColor + '22';
  badge.style.color = labelColor;
  badge.style.border = `1px solid ${labelColor}44`;
  document.getElementById('signalScore').textContent = `Score: ${signal.score} / 100`;

  // Indicators List
  const indList = document.getElementById('indicatorList');
  indList.innerHTML = '';
  indicators.forEach(ind => {
    const cls = ind.signal.includes('buy') ? 'buy' : ind.signal.includes('sell') ? 'sell' : 'neutral';
    const sigText = ind.signal.replace('neutral-','').toUpperCase();
    const sigColors = { buy: 'var(--buy)', neutral: 'var(--neutral)', sell: 'var(--sell)' };
    const sigBg = cls === 'buy' ? 'rgba(57,255,20,0.1)' : cls === 'sell' ? 'rgba(255,45,85,0.1)' : 'rgba(255,215,0,0.1)';
    
    indList.innerHTML += `
      <div class="indicator-row">
        <span class="ind-name">${ind.name}</span>
        <span class="ind-value">${ind.display}</span>
        <span class="ind-signal" style="background:${sigBg}; color:${sigColors[cls]}">${sigText}</span>
      </div>`;
  });

  // Price Targets
  function setPred(idP, idPct, target, base) {
    document.getElementById(idP).textContent = currency + target.toLocaleString(undefined, { maximumFractionDigits: 2 });
    const p = ((target - base) / base * 100);
    const isUp = p >= 0;
    const el = document.getElementById(idPct);
    el.textContent = (isUp ? '+' : '') + p.toFixed(2) + '%';
    el.style.color = isUp ? 'var(--strong-buy)' : 'var(--strong-sell)';
  }
  
  setPred('p1w', 'pct1w', prediction.r1w, stock.price);
  setPred('p1m', 'pct1m', prediction.r1m, stock.price);
  setPred('p3m', 'pct3m', prediction.r3m, stock.price);

  document.getElementById('confBar').style.width = prediction.confidence + '%';
  document.getElementById('confPct').textContent = prediction.confidence + '%';

  // Chart
  renderChart(prices, labels, prediction, currency);
  
  // Update source label
  const srcEl = document.getElementById('sourceLabel');
  if (data.source === 'simulated') {
    srcEl.textContent = 'SIMULATED FEED';
    srcEl.style.background = 'rgba(255,149,0,0.1)';
    srcEl.style.color = 'var(--sell)';
  } else {
    srcEl.textContent = 'REAL FEED';
    srcEl.style.background = 'rgba(0,229,255,0.1)';
    srcEl.style.color = 'var(--accent)';
  }

  // Hide previous result
  document.getElementById('calcResult').classList.remove('visible');
  showToast('Analysis complete for ' + stock.ticker);
}

// ── Watch List Logic ──
function toggleWatch() {
  if (!currentStockData) return;
  const ticker = currentStockData.stock.ticker;
  const index = watchList.indexOf(ticker);
  
  if (index === -1) {
    watchList.push(ticker);
    showToast(`${ticker} added to Watch List`);
  } else {
    watchList.splice(index, 1);
    showToast(`${ticker} removed from Watch List`);
  }
  
  localStorage.setItem('watchlist', JSON.stringify(watchList));
  updateWatchBtn();
}

function updateWatchBtn() {
  const btn = document.getElementById('saveBtn');
  if (!currentStockData || !btn) return;
  const isWatched = watchList.includes(currentStockData.stock.ticker);
  
  if (isWatched) {
    btn.textContent = '✓ Watched';
    btn.classList.add('active');
  } else {
    btn.textContent = '+ Watch';
    btn.classList.remove('active');
  }
}

function getLabelColor(label) {
  const colors = { 
    'STRONG BUY': 'var(--strong-buy)', 
    'BUY': 'var(--buy)', 
    'NEUTRAL': 'var(--neutral)', 
    'SELL': 'var(--sell)', 
    'STRONG SELL': 'var(--strong-sell)' 
  };
  return colors[label] || 'var(--neutral)';
}

async function calculateReturn() {
  if (!currentStockData) { showToast('Please analyze a stock first'); return; }
  
  const amount = parseFloat(document.getElementById('calcAmount').value);
  if (!amount || amount <= 0) { showToast('Enter a valid investment amount'); return; }

  const period = document.getElementById('calcPeriod').value;
  const scenario = document.getElementById('calcScenario').value;

  try {
    const response = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount,
        period,
        scenario,
        trend: currentStockData.stock.trend,
        currentPrice: currentStockData.stock.price
      })
    });
    
    if (!response.ok) throw new Error('Calculation failed');
    
    const res = await response.json();
    const isPos = res.profit >= 0;
    const fmt = n => n.toLocaleString(undefined, { maximumFractionDigits: 2 });
    const currency = currentStockData.stock.ticker.endsWith('.NS') || currentStockData.stock.ticker.endsWith('.BSE') ? '₹' : '$';

    document.getElementById('futureVal').textContent = currency + fmt(res.futureValue);
    document.getElementById('profitVal').textContent = (isPos ? '+' : '-') + currency + fmt(Math.abs(res.profit));
    document.getElementById('profitVal').className = 'result-val ' + (isPos ? 'up' : 'down');
    document.getElementById('returnPct').textContent = (isPos ? '+' : '') + res.returnPct + '%';
    document.getElementById('returnPct').className = 'result-val ' + (isPos ? 'up' : 'down');
    document.getElementById('sharesEst').textContent = res.shares;

    document.getElementById('calcResult').classList.add('visible');
  } catch (error) {
    showToast('Error: ' + error.message);
  }
}

// ── Chart ──────────────────────────────────────────────
function renderChart(prices, labels, prediction, currency) {
  const ctx = document.getElementById('priceChart').getContext('2d');
  if (priceChart) priceChart.destroy();

  const lastPrice = prices[prices.length - 1];
  const predLabels = ['Now', '1W', '1M'];

  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [...labels, ...predLabels.slice(1)],
      datasets: [
        {
          label: 'Price',
          data: [...prices, null, null],
          borderColor: '#00e5ff',
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          backgroundColor: (ctx) => {
            const chart = ctx.chart;
            const {ctx: canvasCtx, chartArea} = chart;
            if (!chartArea) return null;
            const g = canvasCtx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
            g.addColorStop(0, 'rgba(0,229,255,0.18)');
            g.addColorStop(1, 'rgba(0,229,255,0)');
            return g;
          },
          tension: 0.4,
        },
        {
          label: 'Prediction',
          data: [...Array(prices.length - 1).fill(null), lastPrice, prediction.r1w, prediction.r1m],
          borderColor: '#39ff14',
          borderWidth: 2,
          borderDash: [5,4],
          pointRadius: [0,4,4,4],
          pointBackgroundColor: '#39ff14',
          fill: false,
          tension: 0.3,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f1e2d',
          borderColor: '#1a3047',
          borderWidth: 1,
          titleColor: '#5a8fa8',
          bodyColor: '#e0f4ff',
          titleFont: { family: 'Space Mono', size: 10 },
          bodyFont: { family: 'Space Mono', size: 12 },
        }
      },
      scales: {
        x: { grid: { color: 'rgba(26,48,71,0.5)' }, ticks: { color: '#5a8fa8', font: { family:'Space Mono', size:9 }, maxTicksLimit: 8 } },
        y: { grid: { color: 'rgba(26,48,71,0.5)' }, ticks: { color: '#5a8fa8', font: { family:'Space Mono', size:9 }, callback: v => currency+v.toLocaleString() } }
      }
    }
  });
}

function quickPick(ticker) {
  document.getElementById('tickerInput').value = ticker;
  analyzeStock();
}

function switchChart(period, el) {
  document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  currentPeriod = period;
  if (!currentStockData) return;

  showToast('Switched to ' + period + ' view');
  const currency = currentStockData.stock.ticker.endsWith('.NS') || currentStockData.stock.ticker.endsWith('.BSE') ? '₹' : '$';
  renderChart(currentStockData.prices, currentStockData.labels, currentStockData.prediction, currency);
}

// ── Toast ──────────────────────────────────────────────
function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// Enter key
const tickerInput = document.getElementById('tickerInput');
if (tickerInput) {
  tickerInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') analyzeStock();
  });
}
