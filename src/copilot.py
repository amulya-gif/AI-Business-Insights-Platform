import pandas as pd
import numpy as np
from openai import OpenAI

def is_question_related_to_data(question):
    """Filters out questions completely unrelated to the business dataset."""
    q_lower = question.lower()
    
    # Comprehensive keyword mapping matching business domain indicators
    valid_keywords = [
        'revenue', 'sales', 'profit', 'margin', 'date', 'month', 'year', 'trend', 
        'region', 'product', 'category', 'risk', 'recommendation', 'health', 'score', 
        'swot', 'performance', 'grow', 'decrease', 'decline', 'top', 'worst', 
        'underperform', 'invest', 'action', 'focus', 'business', 'company', 'executive', 
        'ceo', 'cfo', 'coo', 'sell', 'cost', 'cogs', 'saas', 'retail', 'banking', 
        'healthcare', 'manufacturing', 'technology', 'telecom', 'arr', 'churn', 'cac', 
        'ltv', 'customer', 'retention', 'fraud', 'compliance', 'digital', 'inventory', 
        'forecast', 'demand', 'capacity', 'waste', 'quality', 'r&d', 'roi', 'development', 
        'market', 'arpu', 'subscriber', 'capex', 'billing', 'outperforming', 'summary', 'north', 'east', 'west', 'south'
    ]
    
    # If the user asks an extremely short question that might be a follow-up, allow it
    if len(q_lower.split()) < 3:
        return True
        
    return any(k in q_lower for k in valid_keywords)


def calculate_business_confidence(df_clean):
    """Calculates a business confidence score based on dataset size and completeness."""
    if df_clean.empty:
        return 50
        
    base_confidence = 80
    
    # Row volume adjustment (up to +10%)
    row_count = len(df_clean)
    row_adj = min(10, int(row_count / 10))
    
    # Completeness adjustment (up to +10%)
    total_elements = df_clean.shape[0] * df_clean.shape[1]
    missing_elements = df_clean.isnull().sum().sum()
    completeness = 1.0 - (missing_elements / total_elements) if total_elements > 0 else 1.0
    comp_adj = int(completeness * 10)
    
    return min(99, max(50, base_confidence + row_adj + comp_adj))


def generate_openai_copilot_response(question, chat_history, kpis, df_clean, date_col, region_col, product_col, revenue_col, profit_col, api_key, model, industry):
    """Generates a consulting copilot response via OpenAI API, preserving session memory and handling optional profit data."""
    if df_clean is None or df_clean.empty:
        return "### Executive Answer\nThe loaded dataset is empty or invalid. Strategic briefing unavailable."
        
    has_profit = profit_col and profit_col in df_clean.columns
    
    if has_profit:
        region_perf = df_clean.groupby(region_col)[[revenue_col, profit_col]].sum()
        region_perf['margin'] = (region_perf[profit_col] / region_perf[revenue_col]) * 100
        worst_region = region_perf['margin'].idxmin() if not region_perf.empty else "N/A"
        worst_region_margin = region_perf['margin'].min() if not region_perf.empty else 0.0

        product_perf = df_clean.groupby(product_col)[[revenue_col, profit_col]].sum()
        product_perf['margin'] = (product_perf[profit_col] / product_perf[revenue_col]) * 100
        worst_product = product_perf['margin'].idxmin() if not product_perf.empty else "N/A"
        worst_product_margin = product_perf['margin'].min() if not product_perf.empty else 0.0
        best_product_margin = product_perf.loc[kpis['top_product'], 'margin'] if kpis['top_product'] in product_perf.index else 0.0
    else:
        worst_region = "N/A"
        worst_region_margin = 0.0
        worst_product = "N/A"
        worst_product_margin = 0.0
        best_product_margin = 0.0

    # Monthly trends compilation
    df_monthly = df_clean.copy()
    df_monthly['Month_Period'] = df_monthly[date_col].dt.to_period('M')
    
    monthly_cols = [revenue_col]
    if has_profit:
        monthly_cols.append(profit_col)
    monthly_perf = df_monthly.groupby('Month_Period')[monthly_cols].sum().sort_index()

    growth_stmt = ""
    if len(monthly_perf) > 1:
        first_rev = monthly_perf.iloc[0][revenue_col]
        last_rev = monthly_perf.iloc[-1][revenue_col]
        pct_change = ((last_rev - first_rev) / first_rev) * 100 if first_rev != 0 else 0
        trend_direction = "upward" if pct_change > 5 else ("downward" if pct_change < -5 else "stable")
        growth_stmt = f"a monthly revenue {trend_direction} trend of {pct_change:+.1f}% from {monthly_perf.index[0]} to {monthly_perf.index[-1]}"
    else:
        growth_stmt = "flat growth over the observed single billing period"

    profit_stmt = f"""- Total Profit: ${kpis['total_profit']:,.2f}
- Profit Margin: {kpis['profit_margin']:.1f}%
- Worst Margin Region: {worst_region} at {worst_region_margin:.1f}%
- Best Segment Margin: {best_product_margin:.1f}%
- Worst Segment Margin: {worst_product} at {worst_product_margin:.1f}%""" if has_profit else "Profit/Margin metrics: NOT available in the uploaded dataset. Focus on sales growth and regional distribution."

    # Assemble system instructions
    system_prompt = f"""You are an elite Senior Management Consultant at Accenture Strategy & Consulting.
Your role is to act as a Business Consulting Copilot, answering strategic questions based ONLY on the provided business dataset.

Current Dataset Context ({industry} Sector):
- Business Health Score: {kpis['health_score']}/100 ({kpis['health_status']})
- Total Revenue: ${kpis['total_revenue']:,.2f}
{profit_stmt}
- Top Region: {kpis['top_region']} (Revenue: ${kpis['top_region_rev']:,.2f})
- Top Product Segment: {kpis['top_product']} (Revenue: ${kpis['top_product_rev']:,.2f})
- Growth Trend: {growth_stmt}

Guidelines:
1. Answer the user's question ONLY using facts from the provided dataset context. Do not invent information.
2. If the data is insufficient to answer the question, clearly state so.
3. You must format your response exactly under these five C-suite headers:

### Executive Answer
[Provide a direct, concise strategic answer to the question.]

### Supporting Evidence
[Detail specific data-backed metrics, margins, and trends from the dataset.]

### Business Impact
[Describe the financial and operational impact on the company.]

### Recommendation
[Provide actionable consulting advice suited for leadership decision making.]

### Priority
[HIGH, MEDIUM, or LOW]

Keep the tone formal, quantitative, and consulting-ready.
"""
    
    # Format messages array including history
    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # Append current question
    messages.append({"role": "user", "content": question})
    
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4
    )
    return response.choices[0].message.content


def generate_rule_based_copilot_response(question, kpis, df_clean, date_col, region_col, product_col, revenue_col, profit_col, industry):
    """Generates structured local heuristics-based answers when OpenAI API is unavailable. Gracefully handles missing profit info."""
    if df_clean is None or df_clean.empty:
        return "### Executive Answer\nThe loaded dataset is empty or invalid. Strategic briefing unavailable."
        
    q_lower = question.lower()
    has_profit = profit_col and profit_col in df_clean.columns
    
    if has_profit:
        region_perf = df_clean.groupby(region_col)[[revenue_col, profit_col]].sum()
        region_perf['margin'] = (region_perf[profit_col] / region_perf[revenue_col]) * 100
        worst_region = region_perf['margin'].idxmin() if not region_perf.empty else "N/A"
        worst_region_margin = region_perf['margin'].min() if not region_perf.empty else 0.0

        product_perf = df_clean.groupby(product_col)[[revenue_col, profit_col]].sum()
        product_perf['margin'] = (product_perf[profit_col] / product_perf[revenue_col]) * 100
        worst_product = product_perf['margin'].idxmin() if not product_perf.empty else "N/A"
        worst_product_margin = product_perf['margin'].min() if not product_perf.empty else 0.0
        best_product_margin = product_perf.loc[kpis['top_product'], 'margin'] if kpis['top_product'] in product_perf.index else 0.0
    else:
        worst_region = "N/A"
        worst_region_margin = 0.0
        worst_product = "N/A"
        worst_product_margin = 0.0
        best_product_margin = 0.0
        # Create dummy group Series to avoid KeyError
        region_perf = df_clean.groupby(region_col)[revenue_col].sum().to_frame()
        region_perf['margin'] = 0.0

    # Intent Detection
    if "why" in q_lower and ("revenue" in q_lower or "sales" in q_lower) and ("decrease" in q_lower or "decline" in q_lower or "drop" in q_lower or "down" in q_lower):
        if has_profit:
            exec_answer = f"Revenue performance is primarily bottlenecked by compressed margins in the **{worst_product}** segment and overall low performance in the **{worst_region}** region."
            evidence = f"The **{worst_product}** segment operates at a sub-par margin of **{worst_product_margin:.1f}%**, while the **{worst_region}** region records a margin of **{worst_region_margin:.1f}%**."
            impact = f"Erodes corporate profits, leading to a consolidated margin of **{kpis['profit_margin']:.1f}%** and diluting the Business Health Score to **{kpis['health_score']}/100**."
            recommendation = f"Initiate a cost audit on **{worst_product}** supply economics and reallocate marketing budgets."
        else:
            exec_answer = f"Revenue performance is primarily lagging in underperforming categories outside the leading **{kpis['top_product']}** segment."
            evidence = f"The leading product **{kpis['top_product']}** drives **${kpis['top_product_rev']:,.2f}** in sales, whereas other product offerings fail to scale."
            impact = f"Limits corporate topline expansion, keeping the consolidated Business Health Score at **{kpis['health_score']}/100**."
            recommendation = "Relaunch marketing campaigns targeting under-penetrated product categories."
        priority = "HIGH"
        
    elif "worst" in q_lower or "underperform" in q_lower or "lagging" in q_lower:
        if has_profit:
            exec_answer = f"The most underperforming category in the company's product line is **{worst_product}**, and the weakest geographic sector is the **{worst_region}** region."
            evidence = f"**{worst_product}** reports an operating margin of only **{worst_product_margin:.1f}%** (compared to **{best_product_margin:.1f}%** for **{kpis['top_product']}**)."
            impact = f"Operational leakage is dragging down total profits to **${kpis['total_profit']:,.2f}**."
            recommendation = f"Audit regional fulfillment structures in **{worst_region}** and adjust pricing tiers for **{worst_product}**."
        else:
            exec_answer = f"Geographic performance highlights a sales deficit in regions outside the primary **{kpis['top_region']}** market."
            evidence = f"The top region **{kpis['top_region']}** dominates with **${kpis['top_region_rev']:,.2f}** in revenue, showing high concentration risk."
            impact = "Revenue is highly vulnerable to local economic shocks in a single region."
            recommendation = "Establish local sales teams in adjacent regional markets to diversify revenue."
        priority = "HIGH"
        
    elif "risk" in q_lower or "danger" in q_lower:
        if has_profit:
            exec_answer = f"The primary operational risks are severe segment margin erosion in **{worst_product}** and a lack of regional revenue diversification."
            evidence = f"**{worst_product}** operates at a low margin of **{worst_product_margin:.1f}%**. Furthermore, the company is highly dependent on **{kpis['top_region']}**."
            impact = f"Extreme vulnerability to localized market downturns in **{kpis['top_region']}**."
            recommendation = "Consolidate overhead and establish a margin floor for all service catalog offerings."
        else:
            exec_answer = f"The primary operational risk is high customer and category concentration in **{kpis['top_product']}**."
            evidence = f"The category **{kpis['top_product']}** represents the majority of overall revenue."
            impact = "Any disruption in consumer demand for this category would severely damage corporate sales."
            recommendation = "Expand product line options to diversify user purchase patterns."
        priority = "HIGH"
        
    elif "invest" in q_lower or "funding" in q_lower:
        exec_answer = f"Additional corporate investment should be channeled into expanding operations in **{kpis['top_region']}** and scaling the high-volume **{kpis['top_product']}** segment."
        evidence = f"**{kpis['top_region']}** is our highest revenue driver, representing **${kpis['top_region_rev']:,.2f}** in sales."
        impact = "Accelerates ARR growth and compound net returns on capital invested."
        recommendation = f"Redirect 15% of the operational budget to support sales incentives in **{kpis['top_region']}**."
        priority = "MEDIUM"
        
    elif "strategic" in q_lower or "initiative" in q_lower or "action" in q_lower or "improve" in q_lower:
        exec_answer = "We recommend three strategic initiatives: Product Line Expansion, Regional Playbook Standardization, and Customer Success Upgrades."
        evidence = f"The consolidated Business Health Score stands at **{kpis['health_score']}/100**."
        impact = f"Aims to increase the consolidated Business Health rating from **{kpis['health_status']}** to **Robust**."
        recommendation = f"1. Re-evaluate supplier agreements. 2. Replicate sales plays from **{kpis['top_region']}** in other regions. 3. Bundle slow-moving inventory with **{kpis['top_product']}**."
        priority = "HIGH"
        
    elif "health" in q_lower or "score" in q_lower:
        exec_answer = f"The company records an overall Business Health Score of **{kpis['health_score']}/100**, which is rated as **{kpis['health_status']}**."
        evidence = f"This composite score aggregates monthly revenue growth, regional sales balance (HHI), and sales consistency."
        impact = f"Indicates that while the business is fundamentally viable, it requires strategic adjustments to reach a 'Robust' rating."
        recommendation = "Focus on raising regional balance and month-over-month growth to boost the composite score."
        priority = "MEDIUM"
        
    elif "swot" in q_lower:
        exec_answer = f"SWOT Matrix Compiled for **{industry}** Sector operations."
        evidence = f"Strengths: High-volume sales of **{kpis['top_product']}** (${kpis['top_product_rev']:,.2f}). Opportunities: High demand in **{kpis['top_region']}**. Weaknesses/Threats: High concentration dependency."
        impact = "Vulnerability to localized market disruptions if the primary region underperforms."
        recommendation = f"Capitalize on **{kpis['top_product']}** demand, and re-engineer fulfillment logistics."
        priority = "MEDIUM"
        
    elif "ceo" in q_lower or "summarize" in q_lower or "executive summary" in q_lower or "summary" in q_lower:
        exec_answer = f"The business reports steady operational revenue of **${kpis['total_revenue']:,.2f}** driven by **{kpis['top_product']}**."
        evidence = f"The business health rating is **{kpis['health_status']}** (Health Score: **{kpis['health_score']}/100**)."
        impact = "The corporation has a solid sales foundation but requires structural category diversification."
        recommendation = "Implement the next-quarter action plan focusing on geographical expansion and category alignment."
        priority = "HIGH"
        
    elif "north" in q_lower or "south" in q_lower or "east" in q_lower or "west" in q_lower or any(state in q_lower for state in ["sp", "rj", "mg", "rs", "pr", "sc", "ba", "pe"]):
        # Support Olist states too!
        ref_region = None
        # Check standard regions
        for r in ["north", "south", "east", "west"]:
            if r in q_lower:
                ref_region = r.capitalize()
                break
        # Check Olist state codes if standard region is not matched
        if not ref_region:
            for state in ["sp", "rj", "mg", "rs", "pr", "sc", "ba", "pe"]:
                if state in q_lower:
                    ref_region = state.upper()
                    break
        
        if ref_region and ref_region in region_perf.index:
            reg_rev = region_perf.loc[ref_region, revenue_col]
            reg_margin = region_perf.loc[ref_region, 'margin'] if has_profit else 0.0
            
            exec_answer = f"Geographic performance breakdown compiled for the **{ref_region}** market."
            evidence = f"**{ref_region}** generates **${reg_rev:,.2f}** in revenue." + (f" Net margin is **{reg_margin:.1f}%**." if has_profit else "")
            impact = f"Contributes **{(reg_rev/kpis['total_revenue']*100):.1f}%** to corporate topline sales."
            recommendation = f"Maintain sales velocity in **{ref_region}**." + (f" If margin is under 15%, adjust unit economics." if has_profit else "")
            priority = "MEDIUM"
        else:
            exec_answer = "Region stats requested, but the specified location is not present in the current dataset."
            evidence = "The query did not map to any active records in the geographic list."
            impact = "Cannot compile regional breakdown."
            recommendation = "Review the Data Preview tab to see the exact state/region codes present in the CSV."
            priority = "LOW"
            
    else:
        exec_answer = f"General performance review generated for the uploaded **{industry}** business records."
        evidence = f"Total Revenue: **${kpis['total_revenue']:,.2f}**." + (f" Total Profit: **${kpis['total_profit']:,.2f}**." if has_profit else "")
        impact = f"Business health rating is **{kpis['health_status']}** (Health Score: **{kpis['health_score']}/100**)."
        recommendation = "Select one of the Example Questions below to investigate specific business problems."
        priority = "LOW"

    # Assemble structured response markdown
    report_markdown = f"""### Executive Answer
{exec_answer}

### Supporting Evidence
{evidence}

### Business Impact
{impact}

### Recommendation
{recommendation}

### Priority
{priority}"""
    return report_markdown
