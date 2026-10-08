import plotly.express as px
import pandas as pd
from src.kpis import truncate_label

def render_revenue_by_region(df, region_col, revenue_col):
    """Generates a centered donut chart displaying regional sales distribution (Top 8 + Others)."""
    # Aggregate data before plotting to optimize charting performance
    df_region_agg = df.groupby(region_col)[revenue_col].sum().reset_index()
    df_region_agg = df_region_agg.sort_values(by=revenue_col, ascending=False)
    
    if len(df_region_agg) > 8:
        top_8 = df_region_agg.head(8)
        others_val = df_region_agg.iloc[8:][revenue_col].sum()
        others_row = pd.DataFrame([{region_col: 'Others', revenue_col: others_val}])
        df_region_agg = pd.concat([top_8, others_row], ignore_index=True)
        
    df_region_agg[region_col] = df_region_agg[region_col].apply(lambda x: truncate_label(x, 20))
    
    fig = px.pie(
        df_region_agg,
        values=revenue_col,
        names=region_col,
        hole=0.4,
        title="Regional Sales Distribution",
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title_x=0.5,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        margin=dict(t=50, b=40, l=10, r=10),
        height=380
    )
    return fig

def render_profit_by_product(df, product_col, profit_col):
    """Generates a sorted horizontal bar chart displaying Top 10 products by profitability."""
    df_product_agg = df.groupby(product_col)[profit_col].sum().reset_index().sort_values(by=profit_col, ascending=False)
    df_product_agg = df_product_agg.head(10)
    df_product_agg[product_col] = df_product_agg[product_col].apply(lambda x: truncate_label(x, 20))
    
    # Sort ascending for horizontal bar format (largest elements displayed at the top)
    df_product_agg = df_product_agg.iloc[::-1]
    
    fig = px.bar(
        df_product_agg,
        x=profit_col,
        y=product_col,
        orientation='h',
        title="Top 10 Products by Profitability",
        color=profit_col,
        color_continuous_scale=px.colors.sequential.Tealgrn
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title_x=0.5,
        coloraxis_showscale=False,
        margin=dict(t=50, b=10, l=10, r=10),
        height=380,
        xaxis_title="Profit",
        yaxis_title=None
    )
    return fig

def render_monthly_revenue_trend(df, date_col, revenue_col):
    """Generates a line chart showing monthly sales trends aggregated over billing periods."""
    df_trend = df.copy()
    df_trend['Month'] = df_trend[date_col].dt.to_period('M').astype(str)
    df_trend_agg = df_trend.groupby('Month')[revenue_col].sum().reset_index().sort_values(by='Month')
    
    fig = px.line(
        df_trend_agg,
        x='Month',
        y=revenue_col,
        title="Monthly Revenue Trend",
        markers=True,
        line_shape='spline'
    )
    fig.update_traces(line_color='#319795', line_width=3, marker=dict(size=8, color='#2b6cb0'))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title_x=0.5,
        margin=dict(t=50, b=10, l=10, r=10),
        height=380,
        xaxis_title="Billing Month",
        yaxis_title="Revenue"
    )
    return fig

def render_revenue_vs_profit(df, date_col, revenue_col, profit_col):
    """Generates a grouped bar chart comparing monthly revenue against net profits."""
    df_rev_prof = df.copy()
    df_rev_prof['Month'] = df_rev_prof[date_col].dt.to_period('M').astype(str)
    df_rev_prof_agg = df_rev_prof.groupby('Month')[[revenue_col, profit_col]].sum().reset_index().sort_values(by='Month')
    
    df_melted = pd.melt(
        df_rev_prof_agg,
        id_vars=['Month'],
        value_vars=[revenue_col, profit_col],
        var_name='Metric',
        value_name='Amount'
    )
    
    fig = px.bar(
        df_melted,
        x='Month',
        y='Amount',
        color='Metric',
        barmode='group',
        title="Revenue vs Profit Comparison",
        color_discrete_sequence=['#2b6cb0', '#319795']
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title_x=0.5,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        margin=dict(t=50, b=40, l=10, r=10),
        height=380,
        xaxis_title="Billing Month",
        yaxis_title="Amount"
    )
    return fig
