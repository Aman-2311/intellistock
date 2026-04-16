// ── State ──────────────────────────────────────────────
let currentStockData = null; 
let priceChart = null;
let currentPeriod = '1W';
let watchList = []; 

// ── Initialization ──
document.addEventListener('DOMContentLoaded', () => {
  init();
});

async function init() {
  await loadWatchlist();
  if (document.getElementById('watchlistContainer')) {
    renderWatchlistPage();
  }
}

async function loadWatchlist() {
  try {
    const res = await fetch('/api/get_watchlist');
    if (res.ok) {
      const data = await res.json();
      watchList = data.map(s => s.ticker);
      updateWatchBtn();
    }
  } catch (err) {
    console.error('Failed to load watchlist:', err);
  }
}

// ── API Integration ───────────────────────────────────
async function analyzeStock() {
  const tickerInput = document.getElementById('tickerInput');
  const ticker = tickerInput.value.trim().toUpperCase();
  if (!ticker) { showToast('Please enter a stock symbol'); return; }

  const emptyState = document.getElementById('emptyState');
  const mainContent = document.getElementById('mainContent');
  if(emptyState) emptyState.style.display = 'none';
  if(mainContent) mainContent.style.display = 'grid';
  
  const loader = document.getElementById('chartLoader');
  if(loader) loader.classList.add('active');

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
    if(loader) loader.classList.remove('active');
  }
}

function updateUI(data) {
  const { stock, prices, labels, indicators, signal, prediction } = data;
  const currency = stock.ticker.endsWith('.NS') || stock.ticker.endsWith('.BSE') ? '₹' : '$';

  // Update Stock Info
  const nameEl = document.getElementById('stockName');
  const tickerEl = document.getElementById('stockTicker');
  const priceEl = document.getElementById('stockPrice');
  
  if(nameEl) nameEl.textContent = stock.name;
  if(tickerEl) tickerEl.textContent = stock.ticker;
  if(priceEl) priceEl.textContent = currency + stock.price.toLocaleString();
  
  const chEl = document.getElementById('priceChange');
  if(chEl) {
    chEl.textContent = (stock.change >= 0 ? '+' : '') + stock.change + ' (' + (stock.pct >= 0 ? '+' : '') + stock.pct + '%)';
    chEl.className = 'price-change ' + (stock.change >= 0 ? 'up' : 'down');
  }

  const h52 = document.getElementById('high52');
  const l52 = document.getElementById('low52');
  const vol = document.getElementById('volume');
  const cap = document.getElementById('mktCap');
  
  if(h52) h52.textContent = currency + stock.high52.toLocaleString();
  if(l52) l52.textContent = currency + stock.low52.toLocaleString();
  if(vol) vol.textContent = stock.vol;
  if(cap) cap.textContent = stock.cap;

  // Signal Indicator
  const gear = document.getElementById('signalNeedle');
  if(gear) gear.style.left = (signal.score / 100 * 100) + '%';
  
  const badge = document.getElementById('signalBadge');
  if(badge) {
    badge.textContent = signal.label;
    const labelColor = getLabelColor(signal.label);
    badge.style.background = labelColor + '22';
    badge.style.color = labelColor;
    badge.style.border = `1px solid ${labelColor}44`;
  }
  
  const scoreEl = document.getElementById('signalScore');
  if(scoreEl) scoreEl.textContent = `Score: ${signal.score} / 100`;

  // Indicators List
  const indList = document.getElementById('indicatorList');
  if(indList) {
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
  }

  // Price Targets
  function setPred(idP, idPct, target, base) {
    const pEl = document.getElementById(idP);
    const pctEl = document.getElementById(idPct);
    if(!pEl || !pctEl) return;
    
    pEl.textContent = currency + target.toLocaleString(undefined, { maximumFractionDigits: 2 });
    const p = ((target - base) / base * 100);
    const isUp = p >= 0;
    pctEl.textContent = (isUp ? '+' : '') + p.toFixed(2) + '%';
    pctEl.style.color = isUp ? 'var(--strong-buy)' : 'var(--strong-sell)';
  }
  
  setPred('p1w', 'pct1w', prediction.r1w, stock.price);
  setPred('p1m', 'pct1m', prediction.r1m, stock.price);
  setPred('p3m', 'pct3m', prediction.r3m, stock.price);

  const confBar = document.getElementById('confBar');
  const confPct = document.getElementById('confPct');
  if(confBar) confBar.style.width = prediction.confidence + '%';
  if(confPct) confPct.textContent = prediction.confidence + '%';

  // Chart
  renderChart(prices, labels, prediction, currency);
  
  const srcEl = document.getElementById('sourceLabel');
  if (srcEl) {
    if (data.source === 'simulated') {
      srcEl.textContent = 'SIMULATED FEED';
      srcEl.style.background = 'rgba(255,149,0,0.1)';
      srcEl.style.color = 'var(--sell)';
    } else {
      srcEl.textContent = 'REAL FEED';
      srcEl.style.background = 'rgba(0,229,255,0.1)';
      srcEl.style.color = 'var(--accent)';
    }
  }

  const calcRes = document.getElementById('calcResult');
  if(calcRes) calcRes.classList.remove('visible');
  showToast('Analysis complete for ' + stock.ticker);
}

// ── Watch List Logic ──
async function toggleWatch() {
  if (!currentStockData) return;
  const ticker = currentStockData.stock.ticker;
  
  try {
    const res = await fetch(`/api/watchlist/toggle/${ticker}`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      watchList = data.watchlist;
      showToast(`${ticker} ${data.action} Watch List`);
      updateWatchBtn();
    }
  } catch (err) {
    showToast('Failed to update watchlist');
  }
}

function updateWatchBtn() {
  const btn = document.getElementById('saveBtn');
  if (!currentStockData || !btn) return;
  const isWatched = watchList.includes(currentStockData.stock.ticker);
  
  if (isWatched) {
    btn.innerHTML = '<span>✓</span> Watched';
    btn.classList.add('active');
  } else {
    btn.innerHTML = '<span>+</span> Watch';
    btn.classList.remove('active');
  }
}

async function renderWatchlistPage() {
  const container = document.getElementById('watchlistContainer');
  if (!container) return;
  
  try {
    const res = await fetch('/api/get_watchlist');
    const data = await res.json();
    
    if (data.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="padding: 60px 0;">
          <div class="empty-icon">📂</div>
          <div class="empty-text">Your Watch List is empty. <br/> Add stocks from the Live Analyzer to track them here.</div>
        </div>`;
      return;
    }
    
    container.innerHTML = data.map(stock => {
      const currency = stock.ticker.endsWith('.NS') || stock.ticker.endsWith('.BSE') ? '₹' : '$';
      const isUp = stock.change >= 0;
      return `
        <div class="watchlist-item" onclick="window.location.href='/analyze?ticker=${stock.ticker}'">
          <div class="w-info">
            <div class="w-ticker">${stock.ticker}</div>
            <div class="w-name">${stock.name}</div>
          </div>
          <div class="w-price-block">
            <div class="w-price">${currency}${stock.price.toLocaleString()}</div>
            <div class="w-change ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${stock.change} (${isUp ? '+' : ''}${stock.pct}%)</div>
          </div>
          <div class="w-action" onclick="event.stopPropagation(); removeFromWatchlist('${stock.ticker}')">×</div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error(err);
  }
}

async function removeFromWatchlist(ticker) {
  try {
    const res = await fetch(`/api/watchlist/toggle/${ticker}`, { method: 'POST' });
    if (res.ok) {
        showToast(`${ticker} removed from Watch List`);
        await loadWatchlist();
        renderWatchlistPage();
    }
  } catch (err) {
    showToast('Error removing item');
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

    const fv = document.getElementById('futureVal');
    const pv = document.getElementById('profitVal');
    const rp = document.getElementById('returnPct');
    const se = document.getElementById('sharesEst');
    
    if(fv) fv.textContent = currency + fmt(res.futureValue);
    if(pv) {
      pv.textContent = (isPos ? '+' : '-') + currency + fmt(Math.abs(res.profit));
      pv.className = 'result-val ' + (isPos ? 'up' : 'down');
    }
    if(rp) {
      rp.textContent = (isPos ? '+' : '') + res.returnPct + '%';
      rp.className = 'result-val ' + (isPos ? 'up' : 'down');
    }
    if(se) se.textContent = res.shares;

    const cr = document.getElementById('calcResult');
    if(cr) cr.classList.add('visible');
  } catch (error) {
    showToast('Error: ' + error.message);
  }
}

// ── Chart ──────────────────────────────────────────────
function renderChart(prices, labels, prediction, currency) {
  const canvas = document.getElementById('priceChart');
  if(!canvas) return;
  const ctx = canvas.getContext('2d');
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
  const input = document.getElementById('tickerInput');
  if(input) input.value = ticker;
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
