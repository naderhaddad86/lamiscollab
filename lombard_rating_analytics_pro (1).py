"""
Lombard Rating Analytics Pro v2.0
=================================
Professional Risk Analytics Suite

Features:
- VaR (Parametric, Historical, Monte Carlo, Cornish-Fisher)
- Credit Risk (PD, LGD, EAD, EL, UL, Credit VaR, RWA)
- Bond Analytics (Duration, Convexity, DV01)
- Options (Black-Scholes with Greeks)
- Stress Testing
- Portfolio Metrics (Sharpe, Sortino, Treynor)
- Liquidity Risk (LCR, NSFR)

© 2026 Lombard Rating Agency | A FINADHAD Holding Company
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from scipy import stats
from scipy.stats import norm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime
import csv
from dataclasses import dataclass
from typing import List, Optional, Dict

# ============================================================================
# STYLING
# ============================================================================

COLORS = {
    'primary': '#1a1f36', 'secondary': '#2d3748', 'accent': '#c9a227',
    'background': '#0d1117', 'surface': '#161b22', 'surface_light': '#21262d',
    'text': '#f0f6fc', 'text_muted': '#8b949e', 'success': '#238636',
    'warning': '#d29922', 'danger': '#da3633', 'info': '#58a6ff', 'border': '#30363d',
}

FONTS = {
    'heading': ('Segoe UI Semibold', 14), 'heading_small': ('Segoe UI Semibold', 11),
    'body': ('Segoe UI', 10), 'body_small': ('Segoe UI', 9), 'mono': ('Consolas', 10),
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class VaRResult:
    parametric_var: float
    historical_var: float
    monte_carlo_var: float
    cornish_fisher_var: float
    expected_shortfall: float
    skewness: float
    kurtosis: float
    simulated_values: np.ndarray

@dataclass
class CreditResult:
    pd: float
    lgd: float
    ead: float
    el: float
    ul: float
    credit_var: float
    recovery: float
    rwa: float
    capital: float
    spread: float
    losses: np.ndarray

@dataclass
class BondResult:
    dirty_price: float
    clean_price: float
    ytm: float
    mac_duration: float
    mod_duration: float
    convexity: float
    dv01: float
    z_spread: float

@dataclass
class OptionResult:
    call: float
    put: float
    delta_c: float
    delta_p: float
    gamma: float
    theta: float
    vega: float
    rho: float

@dataclass
class PortfolioResult:
    sharpe: float
    sortino: float
    treynor: float
    info_ratio: float
    alpha: float
    max_dd: float
    var_95: float

@dataclass
class LiquidityResult:
    lcr: float
    nsfr: float
    gap: float
    cfar: float

# ============================================================================
# RISK ENGINE
# ============================================================================

class RiskEngine:
    @staticmethod
    def calc_var(portfolio, returns, conf=0.99, horizon=10, sims=100000):
        mu, sigma = np.mean(returns), np.std(returns)
        skew, kurt = stats.skew(returns), stats.kurtosis(returns)
        sigma_h, mu_h = sigma * np.sqrt(horizon), mu * horizon
    
        z = norm.ppf(1 - conf)
        param_var = abs(portfolio * (mu_h + z * sigma_h))
    
        hist_var = abs(portfolio * np.percentile(returns * np.sqrt(horizon), (1-conf)*100))
    
        np.random.seed(42)
        # CHANGED: Previously used simple returns: sim_vals = portfolio * (1 + sim_ret)
        # Now using GBM (Geometric Brownian Motion): dS = μS dt + σS dW
        # GBM assumes prices are log-normally distributed, not normally distributed
        sim_ret = np.random.normal(mu_h, sigma_h, sims)  # Same scaling as parametric VaR
        sim_vals = portfolio * np.exp(sim_ret)  # CHANGED: Using exp() for log-normal prices
        mc_var = portfolio - np.percentile(sim_vals, (1-conf)*100)
    
        # LEARNED: Simple returns (1 + ret) can become negative, allowing negative prices
        # GBM with exp() ensures prices always stay positive, which is realistic for assets
        # For small returns, exp(ret) ≈ 1 + ret, but GBM is theoretically correct
    
        z_cf = z + (z**2-1)*skew/6 + (z**3-3*z)*kurt/24 - (2*z**3-5*z)*skew**2/36
        cf_var = abs(portfolio * (mu_h + z_cf * sigma_h))
    
        var_thresh = np.percentile(sim_ret, (1-conf)*100)
        tail = sim_ret[sim_ret <= var_thresh]
        es = -portfolio * np.mean(tail) if len(tail) > 0 else mc_var * 1.2
    
        return VaRResult(param_var, hist_var, mc_var, cf_var, es, skew, kurt, sim_vals)
    
    @staticmethod
    def calc_credit(ead, pd_annual, lgd, horizon=1, sims=100000, corr=0.2, rfr=0.05):
        pd_h = 1 - (1 - pd_annual) ** horizon
        el = ead * pd_h * lgd
        recovery = 1 - lgd
        
        np.random.seed(42)
        sqrt_c, sqrt_1c = np.sqrt(corr), np.sqrt(1 - corr)
        thresh = norm.ppf(pd_h)
        
        sys = np.random.normal(0, 1, sims)
        idio = np.random.normal(0, 1, sims)
        assets = sqrt_c * sys + sqrt_1c * idio
        defaults = assets < thresh
        
        lgd_sim = np.clip(np.random.normal(lgd, 0.15, sims), 0, 1)
        losses = defaults.astype(float) * ead * lgd_sim
        
        ul = np.std(losses)
        cvar = max(0, np.percentile(losses, 99) - el)
        
        pd_safe = max(pd_annual, 0.0001)
        r = 0.12*(1-np.exp(-50*pd_safe))/(1-np.exp(-50)) + 0.24*(1-(1-np.exp(-50*pd_safe))/(1-np.exp(-50)))
        b = (0.11852 - 0.05478*np.log(pd_safe))**2
        ma = (1 + (horizon-2.5)*b) / (1 - 1.5*b)
        k = (lgd * norm.cdf(norm.ppf(pd_safe)/np.sqrt(1-r) + np.sqrt(r/(1-r))*norm.ppf(0.999)) - pd_safe*lgd) * ma
        rwa = ead * k * 12.5
        capital = ead * k
        
        spread = max(0, (-np.log(1 - pd_annual*lgd)/horizon - rfr) * 10000)
        
        return CreditResult(pd_h, lgd, ead, el, ul, cvar, recovery, rwa, capital, spread, losses)
    
    @staticmethod
    def calc_bond(face, coupon, years, yld, freq=2):
        periods = int(years * freq)
        c = face * coupon / freq
        y = yld / freq
        
        pv_c = sum([c/(1+y)**t for t in range(1, periods+1)])
        pv_f = face / (1+y)**periods
        dirty = pv_c + pv_f
        clean = dirty
        
        w = sum([t*c/(1+y)**t for t in range(1, periods+1)])
        w += periods * face / (1+y)**periods
        mac_dur = w / dirty / freq
        mod_dur = mac_dur / (1 + y)
        
        conv = sum([t*(t+1)*c/(1+y)**(t+2) for t in range(1, periods+1)])
        conv += periods*(periods+1)*face/(1+y)**(periods+2)
        convexity = conv / (dirty * freq**2)
        
        dv01 = mod_dur * dirty / 10000
        z_spread = (yld - 0.03) * 10000
        
        return BondResult(dirty, clean, yld, mac_dur, mod_dur, convexity, dv01, z_spread)
    
    @staticmethod
    def calc_option(spot, strike, time, rfr, vol, div=0):
        d1 = (np.log(spot/strike) + (rfr - div + 0.5*vol**2)*time) / (vol*np.sqrt(time))
        d2 = d1 - vol*np.sqrt(time)
        
        call = spot*np.exp(-div*time)*norm.cdf(d1) - strike*np.exp(-rfr*time)*norm.cdf(d2)
        put = strike*np.exp(-rfr*time)*norm.cdf(-d2) - spot*np.exp(-div*time)*norm.cdf(-d1)
        
        delta_c = np.exp(-div*time) * norm.cdf(d1)
        delta_p = np.exp(-div*time) * (norm.cdf(d1) - 1)
        gamma = np.exp(-div*time) * norm.pdf(d1) / (spot * vol * np.sqrt(time))
        theta = (-spot*vol*np.exp(-div*time)*norm.pdf(d1)/(2*np.sqrt(time)) - rfr*strike*np.exp(-rfr*time)*norm.cdf(d2))/365
        vega = spot * np.exp(-div*time) * norm.pdf(d1) * np.sqrt(time) / 100
        rho = strike * time * np.exp(-rfr*time) * norm.cdf(d2) / 100
        
        return OptionResult(call, put, delta_c, delta_p, gamma, theta, vega, rho)
    
    @staticmethod
    def calc_portfolio(ret, vol, rfr, bench, beta):
        sharpe = (ret - rfr) / vol if vol > 0 else 0
        sortino = (ret - rfr) / (vol * 0.7) if vol > 0 else 0
        treynor = (ret - rfr) / beta if beta != 0 else 0
        info = (ret - bench) / 0.05
        alpha = ret - (rfr + beta * (bench - rfr))
        mdd = -vol * 2.5
        var95 = vol * 1.645 * 10000000 / 100
        return PortfolioResult(sharpe, sortino, treynor, info, alpha, mdd, var95)
    
    @staticmethod
    def calc_liquidity(hqla, outflows, asf, rsf, cfvol):
        lcr = (hqla / outflows * 100) if outflows > 0 else 999
        nsfr = (asf / rsf * 100) if rsf > 0 else 999
        gap = hqla - outflows
        cfar = -hqla * cfvol * 1.645
        return LiquidityResult(lcr, nsfr, gap, cfar)
    
    @staticmethod
    def stress_test(portfolio, var99, scenarios):
        results = []
        for name, s in scenarios.items():
            shock = s.get('eq', 0)*0.4 + s.get('rt', 0)*0.2 + s.get('cr', 0)*0.3 + s.get('fx', 0)*0.1
            stressed = portfolio * (1 + shock)
            loss = portfolio - stressed
            results.append({'name': name, 'stressed': stressed, 'loss': loss, 
                          'pct': -shock*100, 'breach': loss > var99})
        return results
    
    @staticmethod
    def gen_returns(days=252, ret=0.08, vol=0.20):
        np.random.seed(42)
        return np.random.normal(ret/252, vol/np.sqrt(252), days)


# ============================================================================
# UI COMPONENTS
# ============================================================================

class GoldButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=200, height=34):
        super().__init__(parent, width=width, height=height, bg=COLORS['surface'], highlightthickness=0)
        self.txt, self.cmd, self.w, self.h, self.hover = text, command, width, height, False
        self._draw()
        self.bind('<Enter>', lambda e: self._set_hover(True))
        self.bind('<Leave>', lambda e: self._set_hover(False))
        self.bind('<Button-1>', lambda e: self.cmd() if self.cmd else None)
    
    def _draw(self):
        self.delete('all')
        bg = COLORS['accent'] if self.hover else COLORS['surface_light']
        fg = COLORS['primary'] if self.hover else COLORS['accent']
        self.create_rectangle(2, 2, self.w-2, self.h-2, fill=bg, outline=COLORS['accent'], width=2)
        self.create_text(self.w//2, self.h//2, text=self.txt, fill=fg, font=FONTS['heading_small'])
    
    def _set_hover(self, state):
        self.hover = state
        self._draw()
        self.config(cursor='hand2' if state else '')


class MetricCard(tk.Frame):
    def __init__(self, parent, title, value, sub="", color=COLORS['accent']):
        super().__init__(parent, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
        tk.Label(self, text=title, font=FONTS['body_small'], fg=COLORS['text_muted'], bg=COLORS['surface']).pack(anchor='w', padx=10, pady=(8, 1))
        self.lbl = tk.Label(self, text=value, font=FONTS['heading'], fg=color, bg=COLORS['surface'])
        self.lbl.pack(anchor='w', padx=10)
        if sub:
            tk.Label(self, text=sub, font=FONTS['body_small'], fg=COLORS['text_muted'], bg=COLORS['surface']).pack(anchor='w', padx=10, pady=(0, 8))
        else:
            self.lbl.pack_configure(pady=(0, 8))
    
    def update(self, val, color=None):
        self.lbl.config(text=val)
        if color: self.lbl.config(fg=color)


class InputField(tk.Frame):
    def __init__(self, parent, label, default=""):
        super().__init__(parent, bg=COLORS['surface'])
        tk.Label(self, text=label, font=FONTS['body_small'], fg=COLORS['text_muted'], bg=COLORS['surface']).pack(anchor='w', pady=(0, 2))
        self.entry = tk.Entry(self, font=FONTS['body'], bg=COLORS['surface_light'], fg=COLORS['text'],
                             insertbackground=COLORS['accent'], relief='flat', highlightthickness=1,
                             highlightbackground=COLORS['border'], highlightcolor=COLORS['accent'])
        self.entry.pack(fill='x')
        self.entry.insert(0, default)
    
    def get(self): return self.entry.get()
    def set(self, v): self.entry.delete(0, tk.END); self.entry.insert(0, str(v))
# ============================================================================
# MAIN APPLICATION
# ============================================================================

class LombardAnalyticsPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lombard Rating Analytics Pro")
        self.geometry("1400x880")
        self.configure(bg=COLORS['background'])
        self.minsize(1200, 750)
        
        self.engine = RiskEngine()
        self.var_res = self.cr_res = self.bond_res = self.opt_res = None
        self.port_res = self.liq_res = self.stress_res = None
        
        self._styles()
        self._header()
        self._content()
        self._status()
    
    def _styles(self):
        s = ttk.Style()
        s.theme_use('clam')
        s.configure('TNotebook', background=COLORS['background'])
        s.configure('TNotebook.Tab', background=COLORS['surface'], foreground=COLORS['text_muted'], padding=[12, 6], font=FONTS['body_small'])
        s.map('TNotebook.Tab', background=[('selected', COLORS['surface_light'])], foreground=[('selected', COLORS['accent'])])
    
    def _header(self):
        h = tk.Frame(self, bg=COLORS['primary'], height=65)
        h.pack(fill='x')
        h.pack_propagate(False)
        
        left = tk.Frame(h, bg=COLORS['primary'], width=450, height=65)
        left.pack(side='left', padx=20)
        left.pack_propagate(False)
        
        logo = tk.Canvas(left, width=42, height=42, bg=COLORS['primary'], highlightthickness=0)
        logo.place(x=0, y=11)
        logo.create_polygon([21, 3, 39, 21, 21, 39, 3, 21], fill=COLORS['accent'])
        logo.create_text(21, 21, text="L", font=('Segoe UI', 15, 'bold'), fill=COLORS['primary'])
        
        tk.Label(left, text="LOMBARD RATING", font=('Segoe UI', 18, 'bold'), fg=COLORS['text'], bg=COLORS['primary']).place(x=55, y=8)
        tk.Label(left, text="A N A L Y T I C S   P R O", font=('Segoe UI', 9, 'bold'), fg=COLORS['accent'], bg=COLORS['primary']).place(x=55, y=36)
        
        right = tk.Frame(h, bg=COLORS['primary'])
        right.pack(side='right', padx=20, pady=10)
        tk.Label(right, text="A FINADHAD Holding Company", font=FONTS['body_small'], fg=COLORS['text_muted'], bg=COLORS['primary']).pack(anchor='e')
        tk.Label(right, text=datetime.now().strftime("%Y-%m-%d %H:%M"), font=FONTS['mono'], fg=COLORS['accent'], bg=COLORS['primary']).pack(anchor='e')
    
    def _content(self):
        m = tk.Frame(self, bg=COLORS['background'])
        m.pack(fill='both', expand=True, padx=10, pady=10)
        self.nb = ttk.Notebook(m)
        self.nb.pack(fill='both', expand=True)
        
        self._var_tab()
        self._credit_tab()
        self._bond_tab()
        self._option_tab()
        self._portfolio_tab()
        self._stress_tab()
        self._liquidity_tab()
        self._report_tab()
    
    def _status(self):
        s = tk.Frame(self, bg=COLORS['primary'], height=25)
        s.pack(fill='x', side='bottom')
        s.pack_propagate(False)
        self.stat = tk.Label(s, text="Ready", font=FONTS['body_small'], fg=COLORS['text_muted'], bg=COLORS['primary'])
        self.stat.pack(side='left', padx=12)
        tk.Label(s, text="v2.0 | © 2026 Lombard Rating Agency", font=FONTS['body_small'], fg=COLORS['text_muted'], bg=COLORS['primary']).pack(side='right', padx=12)
    
    def _pn(self, v): return float(v.replace(',', '').replace('%', ''))
    def _fc(self, v): return f"${v/1e6:.2f}M" if v >= 1e6 else f"${v/1e3:.1f}K" if v >= 1e3 else f"${v:,.2f}"
    
    def _empty(self, fig, canvas, msg):
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS['surface'])
        ax.text(0.5, 0.5, msg, ha='center', va='center', fontsize=11, color=COLORS['text_muted'], transform=ax.transAxes)
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])
        canvas.draw()
    
    def _style_ax(self, ax):
        ax.set_facecolor(COLORS['surface'])
        ax.tick_params(colors=COLORS['text_muted'], labelsize=8)
        for s in ['bottom', 'left']: ax.spines[s].set_color(COLORS['border'])
        for s in ['top', 'right']: ax.spines[s].set_visible(False)
    
    # === VAR TAB ===
    def _var_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Value at Risk ')
        
        left = tk.Frame(t, bg=COLORS['surface'], width=280)
        left.pack(side='left', fill='y', padx=(0, 8), pady=4)
        left.pack_propagate(False)
        
        tk.Label(left, text="VaR Parameters", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=12, pady=(12, 4))
        tk.Frame(left, bg=COLORS['accent'], height=2).pack(fill='x', padx=12, pady=(0, 10))
        
        inp = tk.Frame(left, bg=COLORS['surface'])
        inp.pack(fill='x', padx=12)
        
        self.v_port = InputField(inp, "Portfolio Value ($)", "10,000,000"); self.v_port.pack(fill='x', pady=2)
        self.v_conf = InputField(inp, "Confidence (%)", "99"); self.v_conf.pack(fill='x', pady=2)
        self.v_hor = InputField(inp, "Horizon (days)", "10"); self.v_hor.pack(fill='x', pady=2)
        self.v_sim = InputField(inp, "Simulations", "100,000"); self.v_sim.pack(fill='x', pady=2)
        self.v_vol = InputField(inp, "Volatility (%)", "20"); self.v_vol.pack(fill='x', pady=2)
        self.v_ret = InputField(inp, "Expected Return (%)", "8"); self.v_ret.pack(fill='x', pady=2)
        
        GoldButton(left, "Calculate VaR", self._calc_var, width=240).pack(padx=12, pady=15)
        
        right = tk.Frame(t, bg=COLORS['background'])
        right.pack(side='right', fill='both', expand=True, pady=4)
        
        tk.Label(right, text="VaR Analysis Results", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['background']).pack(anchor='w', pady=(0, 6))
        
        r1 = tk.Frame(right, bg=COLORS['background']); r1.pack(fill='x', pady=3)
        self.v_p = MetricCard(r1, "Parametric VaR", "$0", "Var-Cov"); self.v_p.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.v_h = MetricCard(r1, "Historical VaR", "$0", "Hist Sim"); self.v_h.pack(side='left', fill='x', expand=True, padx=3)
        self.v_m = MetricCard(r1, "Monte Carlo VaR", "$0", "MC Sim"); self.v_m.pack(side='left', fill='x', expand=True, padx=3)
        self.v_cf = MetricCard(r1, "Cornish-Fisher VaR", "$0", "Skew/Kurt Adj"); self.v_cf.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        r2 = tk.Frame(right, bg=COLORS['background']); r2.pack(fill='x', pady=3)
        self.v_es = MetricCard(r2, "Expected Shortfall", "$0", "CVaR", COLORS['danger']); self.v_es.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.v_sk = MetricCard(r2, "Skewness", "0.00", "Shape"); self.v_sk.pack(side='left', fill='x', expand=True, padx=3)
        self.v_ku = MetricCard(r2, "Kurtosis", "0.00", "Tails"); self.v_ku.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        cf = tk.Frame(right, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
        cf.pack(fill='both', expand=True, pady=(6, 0))
        self.v_fig = Figure(figsize=(9, 3), facecolor=COLORS['surface'])
        self.v_can = FigureCanvasTkAgg(self.v_fig, cf)
        self.v_can.get_tk_widget().pack(fill='both', expand=True, padx=3, pady=3)
        self._empty(self.v_fig, self.v_can, "Run VaR calculation")
    
    def _calc_var(self):
        try:
            p = self._pn(self.v_port.get())
            c = self._pn(self.v_conf.get()) / 100
            h = int(self._pn(self.v_hor.get()))
            s = int(self._pn(self.v_sim.get()))
            v = self._pn(self.v_vol.get()) / 100
            r = self._pn(self.v_ret.get()) / 100
            
            rets = self.engine.gen_returns(252, r, v)
            self.var_res = self.engine.calc_var(p, rets, c, h, s)
            
            self.v_p.update(self._fc(self.var_res.parametric_var))
            self.v_h.update(self._fc(self.var_res.historical_var))
            self.v_m.update(self._fc(self.var_res.monte_carlo_var))
            self.v_cf.update(self._fc(self.var_res.cornish_fisher_var))
            self.v_es.update(self._fc(self.var_res.expected_shortfall))
            self.v_sk.update(f"{self.var_res.skewness:.3f}")
            self.v_ku.update(f"{self.var_res.kurtosis:.3f}")
            
            self._draw_var()
            self.stat.config(text=f"VaR complete | {s:,} simulations")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _draw_var(self):
        self.v_fig.clear()
        ax1, ax2 = self.v_fig.add_subplot(121), self.v_fig.add_subplot(122)
        self._style_ax(ax1); self._style_ax(ax2)
        
        vals = self.var_res.simulated_values
        thresh = vals.mean() - self.var_res.monte_carlo_var
        n, bins, patches = ax1.hist(vals, bins=60, density=True, alpha=0.7, color=COLORS['info'], edgecolor='none')
        for patch, b in zip(patches, bins[:-1]):
            if b < thresh: patch.set_facecolor(COLORS['danger']); patch.set_alpha(0.8)
        ax1.axvline(thresh, color=COLORS['accent'], linestyle='--', lw=2)
        ax1.set_title('MC Distribution', color=COLORS['text'], fontsize=9, fontweight='bold')
        ax1.set_xlabel('Portfolio Value', color=COLORS['text_muted'], fontsize=8)
        
        names = ['Param', 'Hist', 'MC', 'C-F', 'ES']
        vals = [self.var_res.parametric_var, self.var_res.historical_var, self.var_res.monte_carlo_var, self.var_res.cornish_fisher_var, self.var_res.expected_shortfall]
        colors = [COLORS['info']]*4 + [COLORS['danger']]
        ax2.barh(names, vals, color=colors, height=0.5)
        ax2.set_title('VaR Comparison', color=COLORS['text'], fontsize=9, fontweight='bold')
        
        self.v_fig.tight_layout(pad=1)
        self.v_can.draw()
    
    # === CREDIT TAB ===
    def _credit_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Credit Risk ')
        
        left = tk.Frame(t, bg=COLORS['surface'], width=280)
        left.pack(side='left', fill='y', padx=(0, 8), pady=4)
        left.pack_propagate(False)
        
        tk.Label(left, text="Credit Parameters", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=12, pady=(12, 4))
        tk.Frame(left, bg=COLORS['accent'], height=2).pack(fill='x', padx=12, pady=(0, 10))
        
        inp = tk.Frame(left, bg=COLORS['surface'])
        inp.pack(fill='x', padx=12)
        
        self.c_ead = InputField(inp, "EAD ($)", "5,000,000"); self.c_ead.pack(fill='x', pady=2)
        self.c_pd = InputField(inp, "Annual PD (%)", "2.5"); self.c_pd.pack(fill='x', pady=2)
        self.c_lgd = InputField(inp, "LGD (%)", "45"); self.c_lgd.pack(fill='x', pady=2)
        self.c_hor = InputField(inp, "Horizon (years)", "1"); self.c_hor.pack(fill='x', pady=2)
        self.c_cor = InputField(inp, "Correlation (%)", "20"); self.c_cor.pack(fill='x', pady=2)
        self.c_rfr = InputField(inp, "Risk-Free Rate (%)", "5"); self.c_rfr.pack(fill='x', pady=2)
        
        # Rating guide
        g = tk.Frame(left, bg=COLORS['surface_light'])
        g.pack(fill='x', padx=12, pady=6)
        tk.Label(g, text="PD Reference", font=FONTS['body_small'], fg=COLORS['text_muted'], bg=COLORS['surface_light']).pack(anchor='w', padx=6, pady=(4, 2))
        for rt, pd in [("AAA","0.01%"),("AA","0.02%"),("A","0.05%"),("BBB","0.20%"),("BB","1.00%"),("B","4.00%")]:
            row = tk.Frame(g, bg=COLORS['surface_light']); row.pack(fill='x', padx=6)
            tk.Label(row, text=rt, font=FONTS['mono'], fg=COLORS['accent'], bg=COLORS['surface_light'], width=4).pack(side='left')
            tk.Label(row, text=pd, font=FONTS['mono'], fg=COLORS['text_muted'], bg=COLORS['surface_light']).pack(side='left')
        tk.Frame(g, height=4, bg=COLORS['surface_light']).pack()
        
        GoldButton(left, "Calculate Credit Risk", self._calc_credit, width=240).pack(padx=12, pady=10)
        
        right = tk.Frame(t, bg=COLORS['background'])
        right.pack(side='right', fill='both', expand=True, pady=4)
        
        tk.Label(right, text="Credit Risk Analysis", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['background']).pack(anchor='w', pady=(0, 6))
        
        r1 = tk.Frame(right, bg=COLORS['background']); r1.pack(fill='x', pady=3)
        self.c_pd_c = MetricCard(r1, "Prob of Default", "0%", "Cumulative"); self.c_pd_c.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.c_lgd_c = MetricCard(r1, "LGD", "0%", "Expected"); self.c_lgd_c.pack(side='left', fill='x', expand=True, padx=3)
        self.c_rec_c = MetricCard(r1, "Recovery", "0%", "Rate", COLORS['success']); self.c_rec_c.pack(side='left', fill='x', expand=True, padx=3)
        self.c_spr_c = MetricCard(r1, "Credit Spread", "0 bps", "Implied"); self.c_spr_c.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        r2 = tk.Frame(right, bg=COLORS['background']); r2.pack(fill='x', pady=3)
        self.c_el_c = MetricCard(r2, "Expected Loss", "$0", "EL", COLORS['warning']); self.c_el_c.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.c_ul_c = MetricCard(r2, "Unexpected Loss", "$0", "UL", COLORS['danger']); self.c_ul_c.pack(side='left', fill='x', expand=True, padx=3)
        self.c_var_c = MetricCard(r2, "Credit VaR 99%", "$0", "CVaR", COLORS['danger']); self.c_var_c.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        r3 = tk.Frame(right, bg=COLORS['background']); r3.pack(fill='x', pady=3)
        self.c_rwa_c = MetricCard(r3, "Risk-Weighted Assets", "$0", "Basel IRB"); self.c_rwa_c.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.c_cap_c = MetricCard(r3, "Capital Requirement", "$0", "Regulatory"); self.c_cap_c.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        cf = tk.Frame(right, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
        cf.pack(fill='both', expand=True, pady=(6, 0))
        self.c_fig = Figure(figsize=(9, 2.5), facecolor=COLORS['surface'])
        self.c_can = FigureCanvasTkAgg(self.c_fig, cf)
        self.c_can.get_tk_widget().pack(fill='both', expand=True, padx=3, pady=3)
        self._empty(self.c_fig, self.c_can, "Run credit calculation")
    
    def _calc_credit(self):
        try:
            ead = self._pn(self.c_ead.get())
            pd = self._pn(self.c_pd.get()) / 100
            lgd = self._pn(self.c_lgd.get()) / 100
            h = int(self._pn(self.c_hor.get()))
            cor = self._pn(self.c_cor.get()) / 100
            rfr = self._pn(self.c_rfr.get()) / 100
            
            self.cr_res = self.engine.calc_credit(ead, pd, lgd, h, 100000, cor, rfr)
            
            self.c_pd_c.update(f"{self.cr_res.pd*100:.2f}%")
            self.c_lgd_c.update(f"{self.cr_res.lgd*100:.1f}%")
            self.c_rec_c.update(f"{self.cr_res.recovery*100:.1f}%")
            self.c_spr_c.update(f"{self.cr_res.spread:.0f} bps")
            self.c_el_c.update(self._fc(self.cr_res.el))
            self.c_ul_c.update(self._fc(self.cr_res.ul))
            self.c_var_c.update(self._fc(self.cr_res.credit_var))
            self.c_rwa_c.update(self._fc(self.cr_res.rwa))
            self.c_cap_c.update(self._fc(self.cr_res.capital))
            
            self._draw_credit()
            self.stat.config(text="Credit risk complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _draw_credit(self):
        self.c_fig.clear()
        ax1, ax2 = self.c_fig.add_subplot(121), self.c_fig.add_subplot(122)
        self._style_ax(ax1); self._style_ax(ax2)
        
        losses = self.cr_res.losses[self.cr_res.losses > 0]
        if len(losses) > 0:
            ax1.hist(losses, bins=35, density=True, alpha=0.7, color=COLORS['danger'], edgecolor='none')
            ax1.axvline(self.cr_res.el, color=COLORS['warning'], linestyle='--', lw=2)
        ax1.set_title('Loss Distribution', color=COLORS['text'], fontsize=9, fontweight='bold')
        
        names = ['EL', 'UL', 'CVaR']
        vals = [self.cr_res.el, self.cr_res.ul, self.cr_res.credit_var]
        ax2.bar(names, vals, color=[COLORS['warning'], COLORS['danger'], COLORS['danger']], width=0.5)
        ax2.set_title('Credit Components', color=COLORS['text'], fontsize=9, fontweight='bold')
        
        self.c_fig.tight_layout(pad=1)
        self.c_can.draw()
    # === BOND TAB ===
    def _bond_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Bond Analytics ')
        
        left = tk.Frame(t, bg=COLORS['surface'], width=280)
        left.pack(side='left', fill='y', padx=(0, 8), pady=4)
        left.pack_propagate(False)
        
        tk.Label(left, text="Bond Parameters", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=12, pady=(12, 4))
        tk.Frame(left, bg=COLORS['accent'], height=2).pack(fill='x', padx=12, pady=(0, 10))
        
        inp = tk.Frame(left, bg=COLORS['surface'])
        inp.pack(fill='x', padx=12)
        
        self.b_face = InputField(inp, "Face Value ($)", "1,000"); self.b_face.pack(fill='x', pady=2)
        self.b_coup = InputField(inp, "Coupon Rate (%)", "5"); self.b_coup.pack(fill='x', pady=2)
        self.b_yrs = InputField(inp, "Years to Maturity", "10"); self.b_yrs.pack(fill='x', pady=2)
        self.b_yld = InputField(inp, "Yield to Maturity (%)", "4.5"); self.b_yld.pack(fill='x', pady=2)
        self.b_freq = InputField(inp, "Frequency (per year)", "2"); self.b_freq.pack(fill='x', pady=2)
        
        GoldButton(left, "Calculate Bond", self._calc_bond, width=240).pack(padx=12, pady=15)
        
        right = tk.Frame(t, bg=COLORS['background'])
        right.pack(side='right', fill='both', expand=True, pady=4)
        
        tk.Label(right, text="Bond Analysis", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['background']).pack(anchor='w', pady=(0, 6))
        
        r1 = tk.Frame(right, bg=COLORS['background']); r1.pack(fill='x', pady=3)
        self.b_dirty = MetricCard(r1, "Dirty Price", "$0", "Full"); self.b_dirty.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.b_clean = MetricCard(r1, "Clean Price", "$0", "Quoted"); self.b_clean.pack(side='left', fill='x', expand=True, padx=3)
        self.b_ytm = MetricCard(r1, "YTM", "0%", "Yield"); self.b_ytm.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        r2 = tk.Frame(right, bg=COLORS['background']); r2.pack(fill='x', pady=3)
        self.b_mac = MetricCard(r2, "Macaulay Duration", "0.00", "Years", COLORS['info']); self.b_mac.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.b_mod = MetricCard(r2, "Modified Duration", "0.00", "Sensitivity", COLORS['info']); self.b_mod.pack(side='left', fill='x', expand=True, padx=3)
        self.b_conv = MetricCard(r2, "Convexity", "0.00", "Curvature"); self.b_conv.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        r3 = tk.Frame(right, bg=COLORS['background']); r3.pack(fill='x', pady=3)
        self.b_dv01 = MetricCard(r3, "DV01", "$0.00", "Dollar Duration", COLORS['warning']); self.b_dv01.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.b_zsp = MetricCard(r3, "Z-Spread", "0 bps", "Over Treasury"); self.b_zsp.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        cf = tk.Frame(right, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
        cf.pack(fill='both', expand=True, pady=(6, 0))
        self.b_fig = Figure(figsize=(9, 2.5), facecolor=COLORS['surface'])
        self.b_can = FigureCanvasTkAgg(self.b_fig, cf)
        self.b_can.get_tk_widget().pack(fill='both', expand=True, padx=3, pady=3)
        self._empty(self.b_fig, self.b_can, "Run bond calculation")
    
    def _calc_bond(self):
        try:
            face = self._pn(self.b_face.get())
            coup = self._pn(self.b_coup.get()) / 100
            yrs = self._pn(self.b_yrs.get())
            yld = self._pn(self.b_yld.get()) / 100
            freq = int(self._pn(self.b_freq.get()))
            
            self.bond_res = self.engine.calc_bond(face, coup, yrs, yld, freq)
            
            self.b_dirty.update(f"${self.bond_res.dirty_price:.2f}")
            self.b_clean.update(f"${self.bond_res.clean_price:.2f}")
            self.b_ytm.update(f"{self.bond_res.ytm*100:.2f}%")
            self.b_mac.update(f"{self.bond_res.mac_duration:.2f}")
            self.b_mod.update(f"{self.bond_res.mod_duration:.2f}")
            self.b_conv.update(f"{self.bond_res.convexity:.2f}")
            self.b_dv01.update(f"${self.bond_res.dv01:.4f}")
            self.b_zsp.update(f"{self.bond_res.z_spread:.0f} bps")
            
            self._draw_bond()
            self.stat.config(text="Bond calculation complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _draw_bond(self):
        self.b_fig.clear()
        ax = self.b_fig.add_subplot(111)
        self._style_ax(ax)
        
        face = self._pn(self.b_face.get())
        coup = self._pn(self.b_coup.get()) / 100
        yrs = self._pn(self.b_yrs.get())
        freq = int(self._pn(self.b_freq.get()))
        
        yields = np.linspace(0.01, 0.10, 40)
        prices = [self.engine.calc_bond(face, coup, yrs, y, freq).dirty_price for y in yields]
        
        ax.plot(yields*100, prices, color=COLORS['info'], lw=2)
        ax.scatter([self.bond_res.ytm*100], [self.bond_res.dirty_price], color=COLORS['accent'], s=80, zorder=5)
        ax.axhline(self.bond_res.dirty_price, color=COLORS['accent'], linestyle='--', alpha=0.5)
        ax.axvline(self.bond_res.ytm*100, color=COLORS['accent'], linestyle='--', alpha=0.5)
        ax.set_title('Price-Yield Curve', color=COLORS['text'], fontsize=9, fontweight='bold')
        ax.set_xlabel('Yield (%)', color=COLORS['text_muted'], fontsize=8)
        ax.set_ylabel('Price ($)', color=COLORS['text_muted'], fontsize=8)
        
        self.b_fig.tight_layout(pad=1)
        self.b_can.draw()
    
    # === OPTIONS TAB ===
    def _option_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Options Pricing ')
        
        left = tk.Frame(t, bg=COLORS['surface'], width=280)
        left.pack(side='left', fill='y', padx=(0, 8), pady=4)
        left.pack_propagate(False)
        
        tk.Label(left, text="Black-Scholes", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=12, pady=(12, 4))
        tk.Frame(left, bg=COLORS['accent'], height=2).pack(fill='x', padx=12, pady=(0, 10))
        
        inp = tk.Frame(left, bg=COLORS['surface'])
        inp.pack(fill='x', padx=12)
        
        self.o_spot = InputField(inp, "Spot Price ($)", "100"); self.o_spot.pack(fill='x', pady=2)
        self.o_strike = InputField(inp, "Strike Price ($)", "105"); self.o_strike.pack(fill='x', pady=2)
        self.o_time = InputField(inp, "Time (years)", "0.5"); self.o_time.pack(fill='x', pady=2)
        self.o_rfr = InputField(inp, "Risk-Free Rate (%)", "5"); self.o_rfr.pack(fill='x', pady=2)
        self.o_vol = InputField(inp, "Volatility (%)", "20"); self.o_vol.pack(fill='x', pady=2)
        self.o_div = InputField(inp, "Dividend Yield (%)", "0"); self.o_div.pack(fill='x', pady=2)
        
        GoldButton(left, "Calculate Options", self._calc_option, width=240).pack(padx=12, pady=15)
        
        right = tk.Frame(t, bg=COLORS['background'])
        right.pack(side='right', fill='both', expand=True, pady=4)
        
        tk.Label(right, text="Option Pricing & Greeks", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['background']).pack(anchor='w', pady=(0, 6))
        
        r1 = tk.Frame(right, bg=COLORS['background']); r1.pack(fill='x', pady=3)
        self.o_call = MetricCard(r1, "Call Price", "$0", "European", COLORS['success']); self.o_call.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.o_put = MetricCard(r1, "Put Price", "$0", "European", COLORS['danger']); self.o_put.pack(side='left', fill='x', expand=True, padx=3)
        self.o_dc = MetricCard(r1, "Delta (Call)", "0.00", "Δ"); self.o_dc.pack(side='left', fill='x', expand=True, padx=3)
        self.o_dp = MetricCard(r1, "Delta (Put)", "0.00", "Δ"); self.o_dp.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        r2 = tk.Frame(right, bg=COLORS['background']); r2.pack(fill='x', pady=3)
        self.o_gam = MetricCard(r2, "Gamma", "0.0000", "Γ"); self.o_gam.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.o_the = MetricCard(r2, "Theta", "$0.00", "Θ/day"); self.o_the.pack(side='left', fill='x', expand=True, padx=3)
        self.o_veg = MetricCard(r2, "Vega", "$0.00", "ν", COLORS['info']); self.o_veg.pack(side='left', fill='x', expand=True, padx=3)
        self.o_rho = MetricCard(r2, "Rho", "$0.00", "ρ"); self.o_rho.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        cf = tk.Frame(right, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
        cf.pack(fill='both', expand=True, pady=(6, 0))
        self.o_fig = Figure(figsize=(9, 2.5), facecolor=COLORS['surface'])
        self.o_can = FigureCanvasTkAgg(self.o_fig, cf)
        self.o_can.get_tk_widget().pack(fill='both', expand=True, padx=3, pady=3)
        self._empty(self.o_fig, self.o_can, "Run options calculation")
    
    def _calc_option(self):
        try:
            spot = self._pn(self.o_spot.get())
            strike = self._pn(self.o_strike.get())
            time = self._pn(self.o_time.get())
            rfr = self._pn(self.o_rfr.get()) / 100
            vol = self._pn(self.o_vol.get()) / 100
            div = self._pn(self.o_div.get()) / 100
            
            self.opt_res = self.engine.calc_option(spot, strike, time, rfr, vol, div)
            
            self.o_call.update(f"${self.opt_res.call:.2f}")
            self.o_put.update(f"${self.opt_res.put:.2f}")
            self.o_dc.update(f"{self.opt_res.delta_c:.4f}")
            self.o_dp.update(f"{self.opt_res.delta_p:.4f}")
            self.o_gam.update(f"{self.opt_res.gamma:.4f}")
            self.o_the.update(f"${self.opt_res.theta:.4f}")
            self.o_veg.update(f"${self.opt_res.vega:.4f}")
            self.o_rho.update(f"${self.opt_res.rho:.4f}")
            
            self._draw_option()
            self.stat.config(text="Options calculation complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _draw_option(self):
        self.o_fig.clear()
        ax = self.o_fig.add_subplot(111)
        self._style_ax(ax)
        
        spot = self._pn(self.o_spot.get())
        strike = self._pn(self.o_strike.get())
        
        prices = np.linspace(spot*0.7, spot*1.3, 80)
        call_pl = np.maximum(prices - strike, 0) - self.opt_res.call
        put_pl = np.maximum(strike - prices, 0) - self.opt_res.put
        
        ax.plot(prices, call_pl, color=COLORS['success'], lw=2, label='Call P/L')
        ax.plot(prices, put_pl, color=COLORS['danger'], lw=2, label='Put P/L')
        ax.axhline(0, color=COLORS['text_muted'], linestyle='-', alpha=0.3)
        ax.axvline(strike, color=COLORS['accent'], linestyle='--', alpha=0.7, label='Strike')
        ax.axvline(spot, color=COLORS['info'], linestyle='--', alpha=0.7, label='Spot')
        ax.set_title('Payoff Diagram', color=COLORS['text'], fontsize=9, fontweight='bold')
        ax.set_xlabel('Underlying ($)', color=COLORS['text_muted'], fontsize=8)
        ax.set_ylabel('P/L ($)', color=COLORS['text_muted'], fontsize=8)
        ax.legend(fontsize=7, facecolor=COLORS['surface_light'], edgecolor=COLORS['border'], labelcolor=COLORS['text'])
        
        self.o_fig.tight_layout(pad=1)
        self.o_can.draw()
    
    # === PORTFOLIO TAB ===
    def _portfolio_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Portfolio Risk ')
        
        left = tk.Frame(t, bg=COLORS['surface'], width=280)
        left.pack(side='left', fill='y', padx=(0, 8), pady=4)
        left.pack_propagate(False)
        
        tk.Label(left, text="Portfolio Parameters", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=12, pady=(12, 4))
        tk.Frame(left, bg=COLORS['accent'], height=2).pack(fill='x', padx=12, pady=(0, 10))
        
        inp = tk.Frame(left, bg=COLORS['surface'])
        inp.pack(fill='x', padx=12)
        
        self.p_ret = InputField(inp, "Expected Return (%)", "10"); self.p_ret.pack(fill='x', pady=2)
        self.p_vol = InputField(inp, "Volatility (%)", "15"); self.p_vol.pack(fill='x', pady=2)
        self.p_rfr = InputField(inp, "Risk-Free Rate (%)", "3"); self.p_rfr.pack(fill='x', pady=2)
        self.p_ben = InputField(inp, "Benchmark Return (%)", "8"); self.p_ben.pack(fill='x', pady=2)
        self.p_beta = InputField(inp, "Portfolio Beta", "1.1"); self.p_beta.pack(fill='x', pady=2)
        
        GoldButton(left, "Calculate Portfolio", self._calc_portfolio, width=240).pack(padx=12, pady=15)
        
        right = tk.Frame(t, bg=COLORS['background'])
        right.pack(side='right', fill='both', expand=True, pady=4)
        
        tk.Label(right, text="Portfolio Risk Metrics", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['background']).pack(anchor='w', pady=(0, 6))
        
        r1 = tk.Frame(right, bg=COLORS['background']); r1.pack(fill='x', pady=3)
        self.p_sha = MetricCard(r1, "Sharpe Ratio", "0.00", "Risk-Adj", COLORS['info']); self.p_sha.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.p_sor = MetricCard(r1, "Sortino Ratio", "0.00", "Downside"); self.p_sor.pack(side='left', fill='x', expand=True, padx=3)
        self.p_tre = MetricCard(r1, "Treynor Ratio", "0.00", "Beta-Adj"); self.p_tre.pack(side='left', fill='x', expand=True, padx=3)
        self.p_inf = MetricCard(r1, "Info Ratio", "0.00", "Active/TE"); self.p_inf.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        r2 = tk.Frame(right, bg=COLORS['background']); r2.pack(fill='x', pady=3)
        self.p_alp = MetricCard(r2, "Jensen's Alpha", "0.00%", "Excess", COLORS['success']); self.p_alp.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.p_mdd = MetricCard(r2, "Max Drawdown", "0.00%", "Peak-Trough", COLORS['danger']); self.p_mdd.pack(side='left', fill='x', expand=True, padx=3)
        self.p_var = MetricCard(r2, "VaR (95%)", "$0", "1-Day"); self.p_var.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        cf = tk.Frame(right, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
        cf.pack(fill='both', expand=True, pady=(6, 0))
        self.p_fig = Figure(figsize=(9, 2.5), facecolor=COLORS['surface'])
        self.p_can = FigureCanvasTkAgg(self.p_fig, cf)
        self.p_can.get_tk_widget().pack(fill='both', expand=True, padx=3, pady=3)
        self._empty(self.p_fig, self.p_can, "Run portfolio calculation")
    
    def _calc_portfolio(self):
        try:
            ret = self._pn(self.p_ret.get()) / 100
            vol = self._pn(self.p_vol.get()) / 100
            rfr = self._pn(self.p_rfr.get()) / 100
            ben = self._pn(self.p_ben.get()) / 100
            beta = self._pn(self.p_beta.get())
            
            self.port_res = self.engine.calc_portfolio(ret, vol, rfr, ben, beta)
            
            self.p_sha.update(f"{self.port_res.sharpe:.2f}")
            self.p_sor.update(f"{self.port_res.sortino:.2f}")
            self.p_tre.update(f"{self.port_res.treynor:.2f}")
            self.p_inf.update(f"{self.port_res.info_ratio:.2f}")
            self.p_alp.update(f"{self.port_res.alpha*100:.2f}%")
            self.p_mdd.update(f"{self.port_res.max_dd*100:.1f}%")
            self.p_var.update(self._fc(self.port_res.var_95))
            
            self._draw_portfolio()
            self.stat.config(text="Portfolio calculation complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _draw_portfolio(self):
        self.p_fig.clear()
        ax = self.p_fig.add_subplot(111)
        self._style_ax(ax)
        
        names = ['Sharpe', 'Sortino', 'Treynor', 'Info Ratio']
        vals = [self.port_res.sharpe, self.port_res.sortino, self.port_res.treynor, self.port_res.info_ratio]
        colors = [COLORS['info'] if v > 0 else COLORS['danger'] for v in vals]
        
        ax.bar(names, vals, color=colors, width=0.5)
        ax.axhline(0, color=COLORS['text_muted'], linestyle='-', alpha=0.3)
        ax.set_title('Risk-Adjusted Metrics', color=COLORS['text'], fontsize=9, fontweight='bold')
        
        self.p_fig.tight_layout(pad=1)
        self.p_can.draw()
    
    # === STRESS TAB ===
    def _stress_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Stress Testing ')
        
        left = tk.Frame(t, bg=COLORS['surface'], width=280)
        left.pack(side='left', fill='y', padx=(0, 8), pady=4)
        left.pack_propagate(False)
        
        tk.Label(left, text="Stress Parameters", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=12, pady=(12, 4))
        tk.Frame(left, bg=COLORS['accent'], height=2).pack(fill='x', padx=12, pady=(0, 10))
        
        inp = tk.Frame(left, bg=COLORS['surface'])
        inp.pack(fill='x', padx=12)
        
        self.s_port = InputField(inp, "Portfolio ($)", "10,000,000"); self.s_port.pack(fill='x', pady=2)
        self.s_var = InputField(inp, "Current VaR ($)", "500,000"); self.s_var.pack(fill='x', pady=2)
        
        tk.Label(inp, text="Custom Shocks (%)", font=FONTS['body_small'], fg=COLORS['accent'], bg=COLORS['surface']).pack(anchor='w', pady=(8, 3))
        self.s_eq = InputField(inp, "Equity", "-30"); self.s_eq.pack(fill='x', pady=2)
        self.s_rt = InputField(inp, "Rates", "2"); self.s_rt.pack(fill='x', pady=2)
        self.s_cr = InputField(inp, "Credit", "3"); self.s_cr.pack(fill='x', pady=2)
        self.s_fx = InputField(inp, "FX", "-15"); self.s_fx.pack(fill='x', pady=2)
        
        GoldButton(left, "Run Stress Tests", self._calc_stress, width=240).pack(padx=12, pady=15)
        
        right = tk.Frame(t, bg=COLORS['background'])
        right.pack(side='right', fill='both', expand=True, pady=4)
        
        tk.Label(right, text="Stress Test Results", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['background']).pack(anchor='w', pady=(0, 6))
        
        self.s_frame = tk.Frame(right, bg=COLORS['background'])
        self.s_frame.pack(fill='both', expand=True)
        tk.Label(self.s_frame, text="Run stress tests to view scenarios", font=FONTS['body'], fg=COLORS['text_muted'], bg=COLORS['background']).pack(pady=30)
    
    def _calc_stress(self):
        try:
            port = self._pn(self.s_port.get())
            var99 = self._pn(self.s_var.get())
            
            scenarios = {
                '2008 Financial Crisis': {'eq': -0.40, 'rt': 0.02, 'cr': 0.05, 'fx': -0.15},
                'COVID-19 Shock': {'eq': -0.35, 'rt': -0.01, 'cr': 0.03, 'fx': -0.10},
                'Rate Shock +300bp': {'eq': -0.15, 'rt': 0.03, 'cr': 0.02, 'fx': -0.05},
                'Custom Scenario': {
                    'eq': self._pn(self.s_eq.get())/100,
                    'rt': self._pn(self.s_rt.get())/100,
                    'cr': self._pn(self.s_cr.get())/100,
                    'fx': self._pn(self.s_fx.get())/100
                }
            }
            
            self.stress_res = self.engine.stress_test(port, var99, scenarios)
            
            for w in self.s_frame.winfo_children(): w.destroy()
            
            for r in self.stress_res:
                f = tk.Frame(self.s_frame, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
                f.pack(fill='x', pady=3)
                
                bc = COLORS['danger'] if r['breach'] else COLORS['success']
                
                tk.Label(f, text=r['name'], font=FONTS['heading_small'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=10, pady=(6, 2))
                
                d = tk.Frame(f, bg=COLORS['surface'])
                d.pack(fill='x', padx=10, pady=(0, 6))
                
                tk.Label(d, text=f"Loss: {self._fc(r['loss'])} ({r['pct']:.1f}%)", font=FONTS['mono'], fg=COLORS['danger'], bg=COLORS['surface']).pack(side='left', padx=(0, 15))
                tk.Label(d, text=f"Stressed: {self._fc(r['stressed'])}", font=FONTS['mono'], fg=COLORS['text_muted'], bg=COLORS['surface']).pack(side='left', padx=(0, 15))
                tk.Label(d, text=f"VaR Breach: {'YES' if r['breach'] else 'NO'}", font=FONTS['mono'], fg=bc, bg=COLORS['surface']).pack(side='left')
            
            self.stat.config(text="Stress tests complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    # === LIQUIDITY TAB ===
    def _liquidity_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Liquidity Risk ')
        
        left = tk.Frame(t, bg=COLORS['surface'], width=280)
        left.pack(side='left', fill='y', padx=(0, 8), pady=4)
        left.pack_propagate(False)
        
        tk.Label(left, text="Liquidity Parameters", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['surface']).pack(anchor='w', padx=12, pady=(12, 4))
        tk.Frame(left, bg=COLORS['accent'], height=2).pack(fill='x', padx=12, pady=(0, 10))
        
        inp = tk.Frame(left, bg=COLORS['surface'])
        inp.pack(fill='x', padx=12)
        
        self.l_hqla = InputField(inp, "HQLA ($)", "5,000,000"); self.l_hqla.pack(fill='x', pady=2)
        self.l_out = InputField(inp, "Net Outflows 30d ($)", "4,000,000"); self.l_out.pack(fill='x', pady=2)
        self.l_asf = InputField(inp, "Avail Stable Funding ($)", "8,000,000"); self.l_asf.pack(fill='x', pady=2)
        self.l_rsf = InputField(inp, "Req Stable Funding ($)", "7,000,000"); self.l_rsf.pack(fill='x', pady=2)
        self.l_cfv = InputField(inp, "CF Volatility (%)", "15"); self.l_cfv.pack(fill='x', pady=2)
        
        GoldButton(left, "Calculate Liquidity", self._calc_liquidity, width=240).pack(padx=12, pady=15)
        
        right = tk.Frame(t, bg=COLORS['background'])
        right.pack(side='right', fill='both', expand=True, pady=4)
        
        tk.Label(right, text="Liquidity Risk (Basel III)", font=FONTS['heading'], fg=COLORS['text'], bg=COLORS['background']).pack(anchor='w', pady=(0, 6))
        
        r1 = tk.Frame(right, bg=COLORS['background']); r1.pack(fill='x', pady=3)
        self.l_lcr = MetricCard(r1, "LCR", "0%", "Min: 100%", COLORS['info']); self.l_lcr.pack(side='left', fill='x', expand=True, padx=(0, 3))
        self.l_nsfr = MetricCard(r1, "NSFR", "0%", "Min: 100%", COLORS['info']); self.l_nsfr.pack(side='left', fill='x', expand=True, padx=3)
        self.l_gap = MetricCard(r1, "Liquidity Gap", "$0", "HQLA-Outflows"); self.l_gap.pack(side='left', fill='x', expand=True, padx=3)
        self.l_cfar = MetricCard(r1, "CF at Risk", "$0", "95%"); self.l_cfar.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        cf = tk.Frame(right, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
        cf.pack(fill='both', expand=True, pady=(6, 0))
        self.l_fig = Figure(figsize=(9, 3), facecolor=COLORS['surface'])
        self.l_can = FigureCanvasTkAgg(self.l_fig, cf)
        self.l_can.get_tk_widget().pack(fill='both', expand=True, padx=3, pady=3)
        self._empty(self.l_fig, self.l_can, "Run liquidity calculation")
    
    def _calc_liquidity(self):
        try:
            hqla = self._pn(self.l_hqla.get())
            out = self._pn(self.l_out.get())
            asf = self._pn(self.l_asf.get())
            rsf = self._pn(self.l_rsf.get())
            cfv = self._pn(self.l_cfv.get()) / 100
            
            self.liq_res = self.engine.calc_liquidity(hqla, out, asf, rsf, cfv)
            
            lc = COLORS['success'] if self.liq_res.lcr >= 100 else COLORS['danger']
            nc = COLORS['success'] if self.liq_res.nsfr >= 100 else COLORS['danger']
            
            self.l_lcr.update(f"{self.liq_res.lcr:.1f}%", lc)
            self.l_nsfr.update(f"{self.liq_res.nsfr:.1f}%", nc)
            self.l_gap.update(self._fc(self.liq_res.gap))
            self.l_cfar.update(self._fc(abs(self.liq_res.cfar)))
            
            self._draw_liquidity()
            self.stat.config(text="Liquidity calculation complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _draw_liquidity(self):
        self.l_fig.clear()
        ax = self.l_fig.add_subplot(111)
        self._style_ax(ax)
        
        names = ['LCR', 'NSFR']
        vals = [self.liq_res.lcr, self.liq_res.nsfr]
        colors = [COLORS['success'] if v >= 100 else COLORS['danger'] for v in vals]
        
        ax.bar(names, vals, color=colors, width=0.4)
        ax.axhline(100, color=COLORS['accent'], linestyle='--', lw=2, label='Min 100%')
        ax.set_title('Basel III Liquidity Ratios', color=COLORS['text'], fontsize=9, fontweight='bold')
        ax.set_ylabel('Ratio (%)', color=COLORS['text_muted'], fontsize=8)
        ax.legend(fontsize=7, facecolor=COLORS['surface_light'], edgecolor=COLORS['border'], labelcolor=COLORS['text'])
        
        self.l_fig.tight_layout(pad=1)
        self.l_can.draw()
    
    # === REPORTS TAB ===
    def _report_tab(self):
        t = tk.Frame(self.nb, bg=COLORS['background'])
        self.nb.add(t, text=' Reports ')
        
        c = tk.Frame(t, bg=COLORS['background'])
        c.place(relx=0.5, rely=0.5, anchor='center')
        
        tk.Label(c, text="Export Risk Reports", font=('Segoe UI', 20, 'bold'), fg=COLORS['text'], bg=COLORS['background']).pack(pady=(0, 6))
        tk.Label(c, text="Generate comprehensive CSV reports", font=FONTS['body'], fg=COLORS['text_muted'], bg=COLORS['background']).pack(pady=(0, 25))
        
        btns = tk.Frame(c, bg=COLORS['background'])
        btns.pack()
        
        for title, cmd in [("VaR Report", self._exp_var), ("Credit Report", self._exp_credit), ("Full Report", self._exp_full)]:
            f = tk.Frame(btns, bg=COLORS['surface'], highlightbackground=COLORS['border'], highlightthickness=1)
            f.pack(side='left', padx=12, pady=10)
            tk.Label(f, text="📊", font=('Segoe UI', 24), bg=COLORS['surface']).pack(pady=(15, 6))
            tk.Label(f, text=title, font=FONTS['heading_small'], fg=COLORS['text'], bg=COLORS['surface']).pack()
            GoldButton(f, "Export CSV", cmd, width=130).pack(pady=(8, 15))
    
    def _exp_var(self):
        if not self.var_res: messagebox.showwarning("No Data", "Run VaR first"); return
        self._save([["Lombard Rating Analytics - VaR"], [f"Generated: {datetime.now()}"], [],
            ["Parametric VaR", f"${self.var_res.parametric_var:,.2f}"],
            ["Historical VaR", f"${self.var_res.historical_var:,.2f}"],
            ["Monte Carlo VaR", f"${self.var_res.monte_carlo_var:,.2f}"],
            ["Cornish-Fisher VaR", f"${self.var_res.cornish_fisher_var:,.2f}"],
            ["Expected Shortfall", f"${self.var_res.expected_shortfall:,.2f}"],
            ["Skewness", f"{self.var_res.skewness:.4f}"],
            ["Kurtosis", f"{self.var_res.kurtosis:.4f}"]], "VaR_Report")
    
    def _exp_credit(self):
        if not self.cr_res: messagebox.showwarning("No Data", "Run Credit first"); return
        self._save([["Lombard Rating Analytics - Credit Risk"], [f"Generated: {datetime.now()}"], [],
            ["EAD", f"${self.cr_res.ead:,.2f}"],
            ["PD", f"{self.cr_res.pd*100:.4f}%"],
            ["LGD", f"{self.cr_res.lgd*100:.2f}%"],
            ["Expected Loss", f"${self.cr_res.el:,.2f}"],
            ["Unexpected Loss", f"${self.cr_res.ul:,.2f}"],
            ["Credit VaR", f"${self.cr_res.credit_var:,.2f}"],
            ["RWA", f"${self.cr_res.rwa:,.2f}"],
            ["Capital", f"${self.cr_res.capital:,.2f}"],
            ["Spread", f"{self.cr_res.spread:.0f} bps"]], "Credit_Report")
    
    def _exp_full(self):
        rows = [["="*40], ["LOMBARD RATING ANALYTICS"], ["Full Risk Report"], ["="*40], [f"Generated: {datetime.now()}"], []]
        if self.var_res:
            rows += [["--- VaR ---"], ["MC VaR", f"${self.var_res.monte_carlo_var:,.2f}"], ["ES", f"${self.var_res.expected_shortfall:,.2f}"], []]
        if self.cr_res:
            rows += [["--- Credit ---"], ["EL", f"${self.cr_res.el:,.2f}"], ["CVaR", f"${self.cr_res.credit_var:,.2f}"], ["Capital", f"${self.cr_res.capital:,.2f}"], []]
        if self.bond_res:
            rows += [["--- Bond ---"], ["Price", f"${self.bond_res.dirty_price:.2f}"], ["Duration", f"{self.bond_res.mod_duration:.2f}"], []]
        if self.opt_res:
            rows += [["--- Options ---"], ["Call", f"${self.opt_res.call:.2f}"], ["Put", f"${self.opt_res.put:.2f}"], []]
        if self.port_res:
            rows += [["--- Portfolio ---"], ["Sharpe", f"{self.port_res.sharpe:.2f}"], ["Alpha", f"{self.port_res.alpha*100:.2f}%"], []]
        if self.liq_res:
            rows += [["--- Liquidity ---"], ["LCR", f"{self.liq_res.lcr:.1f}%"], ["NSFR", f"{self.liq_res.nsfr:.1f}%"], []]
        rows += [["="*40], ["END"]]
        self._save(rows, "Full_Report")
    
    def _save(self, rows, name):
        fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfilename=f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if fp:
            try:
                with open(fp, 'w', newline='') as f: csv.writer(f).writerows(rows)
                messagebox.showinfo("Success", f"Exported: {fp}")
                self.stat.config(text=f"Report exported")
            except Exception as e: messagebox.showerror("Error", str(e))


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = LombardAnalyticsPro()
    app.mainloop()
