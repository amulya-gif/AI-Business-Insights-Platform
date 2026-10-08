import pandas as pd
import numpy as np

def truncate_label(label, max_len=20):
    """Wraps and truncates labels to prevent dashboard overflow."""
    if label is None or pd.isna(label):
        return "N/A"
    s = str(label).strip()
    if len(s) > max_len:
        return s[:max_len-3] + "..."
    return s

def format_metric_val(val, prefix="$"):
    """Formats raw floats into consulting-grade short representations (M, K, units) using locale settings."""
    if val is None or pd.isna(val):
        return "N/A"
    is_negative = val < 0
    abs_val = abs(val)
    
    if abs_val >= 1_000_000:
        formatted = f"{abs_val/1_000_000:.2f}M"
    elif abs_val >= 1_000:
        formatted = f"{abs_val/1_000:.1f}K"
    else:
        formatted = f"{abs_val:,.0f}"
        
    sign = "-" if is_negative else ""
    return f"{sign}{prefix}{formatted}"

def calculate_kpis(df, date_col, region_col, product_col, revenue_col, profit_col):
    """Calculates high-level metrics and a weighted Business Health Score. Handles datasets with missing profit details."""
    if df is None or df.empty or revenue_col not in df.columns:
        return {
            'total_revenue': 0.0,
            'total_profit': 0.0,
            'profit_margin': 0.0,
            'top_region': "N/A",
            'top_region_rev': 0.0,
            'top_product': "N/A",
            'top_product_rev': 0.0,
            'health_score': 0,
            'health_status': "Vulnerable"
        }
        
    total_rev = df[revenue_col].sum() if revenue_col in df.columns else 0.0
    
    has_profit = profit_col and profit_col in df.columns
    if has_profit:
        total_profit = df[profit_col].sum()
        profit_margin = (total_profit / total_rev * 100) if total_rev != 0 else 0.0
    else:
        total_profit = 0.0
        profit_margin = 0.0

    # Top Region and Product based on Revenue volume
    region_summary = df.groupby(region_col)[revenue_col].sum() if region_col in df.columns else pd.Series()
    top_region = region_summary.idxmax() if not region_summary.empty else "N/A"
    top_region_rev = region_summary.max() if not region_summary.empty else 0.0

    product_summary = df.groupby(product_col)[revenue_col].sum() if product_col in df.columns else pd.Series()
    top_product = product_summary.idxmax() if not product_summary.empty else "N/A"
    top_product_rev = product_summary.max() if not product_summary.empty else 0.0

    monthly_revs = pd.Series()
    if date_col in df.columns:
        df_m = df.copy()
        df_m['Month'] = df_m[date_col].dt.to_period('M')
        monthly_revs = df_m.groupby('Month')[revenue_col].sum().sort_index()

    # 1. Revenue Growth Score (25% or 35% Weight)
    if len(monthly_revs) > 1:
        first_month_rev = monthly_revs.iloc[0]
        last_month_rev = monthly_revs.iloc[-1]
        growth_rate = (last_month_rev - first_month_rev) / first_month_rev if first_month_rev != 0 else 0.0
        growth_score = min(100.0, max(0.0, 50.0 + (growth_rate * 100.0 * 2.5)))
    else:
        growth_score = 75.0

    # 2. Revenue Consistency Score (25% or 35% Weight)
    if len(monthly_revs) > 1:
        mean_rev = monthly_revs.mean()
        std_rev = monthly_revs.std()
        cv = (std_rev / mean_rev) if mean_rev > 0 else 1.0
        consistency_score = max(0.0, min(100.0, 100.0 - (cv * 100.0)))
    else:
        consistency_score = 85.0

    # 3. Regional Balance Score (20% or 30% Weight) - HHI Index based
    if total_rev > 0 and len(region_summary) > 1:
        shares = region_summary / total_rev
        hhi = (shares ** 2).sum()
        n_regions = len(region_summary)
        balance_score = max(0.0, min(100.0, (1.0 - hhi) / (1.0 - (1.0 / n_regions)) * 100.0))
    else:
        balance_score = 50.0

    # Business Health Score Calculation (C-suite Grade)
    if has_profit:
        # Profit Margin Score (30% Weight) - Benchmark 40% Margin
        margin_score = min(100.0, max(0.0, (profit_margin / 40.0) * 100.0))
        health_score = int(round(
            0.30 * margin_score + 
            0.25 * growth_score + 
            0.25 * consistency_score + 
            0.20 * balance_score
        ))
    else:
        # Re-distribute 30% margin weight proportionally to other metrics (0.35, 0.35, 0.30)
        health_score = int(round(
            0.35 * growth_score + 
            0.35 * consistency_score + 
            0.30 * balance_score
        ))

    if health_score >= 80:
        health_status = "Robust"
    elif health_score >= 60:
        health_status = "Stable"
    else:
        health_status = "Vulnerable"

    return {
        'total_revenue': total_rev,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'top_region': top_region,
        'top_region_rev': top_region_rev,
        'top_product': top_product,
        'top_product_rev': top_product_rev,
        'health_score': health_score,
        'health_status': health_status
    }
