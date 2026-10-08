from openai import OpenAI
import pandas as pd

def generate_openai_report(kpis, df_clean, date_col, region_col, product_col, revenue_col, profit_col, api_key, model, industry):
    """Generates an executive briefing report using OpenAI's API. Gracefully handles missing profit data."""
    if df_clean is None or df_clean.empty:
        return "## Executive Summary\nStrategic briefing unavailable because the loaded dataset is empty or invalid."
        
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

    # Context prompts based on selected industry
    industry_contexts = {
        "Retail": "Focus heavily on inventory optimization, promotional effectiveness, demand forecasting accuracy, and changing consumer purchasing behaviors.",
        "Banking": "Focus heavily on customer retention rates, fraud prevention measures, regulatory compliance standards, and digital banking platform adoption.",
        "Healthcare": "Focus heavily on patient outcomes, regulatory compliance, operational throughput efficiency, and insurance/billing reimbursement cycles.",
        "Manufacturing": "Focus heavily on COGS optimization, factory capacity utilization, quality control statistics, and inventory carrying cost management.",
        "Technology": "Focus heavily on R&D ROI, cloud infrastructure hosting costs, developer sprint velocity, and hardware/software time-to-market.",
        "SaaS": "Focus heavily on customer churn rates, monthly subscription expansion growth, ARR run-rates, and Customer Acquisition Cost (CAC) efficiency.",
        "Telecommunications": "Focus heavily on Average Revenue Per User (ARPU), cellular/broadband network capacity, subscriber acquisition costs, and infrastructure CAPEX efficiency."
    }
    
    industry_guidelines = industry_contexts.get(industry, "")

    system_prompt = f"""You are a Senior Strategic Director at Accenture Strategy & Consulting, hired to compile high-grade executive briefing reports for C-Suite executives (CEO, CFO, COO). 
You write with structured precision, avoiding analytical filler. The target industry sector is: {industry}. {industry_guidelines}"""

    # If profit information is not available, instruct the LLM to focus on sales distribution, growth, and operations
    profit_context_line = f"""- Total Profit: ${kpis['total_profit']:,.2f}
    - Average Net Profit Margin: {kpis['profit_margin']:.2f}%
    - Lowest-Margin Region: {worst_region} ({worst_region_margin:.2f}% margin)
    - Lowest-Margin Product Segment: {worst_product} ({worst_product_margin:.2f}% margin)
    - Highest-Margin Product Segment: {kpis['top_product']} ({best_product_margin:.2f}% margin)""" if has_profit else "Profit information is NOT available in the uploaded dataset. Focus purely on revenue generation, growth trends, geographical sales distribution, and customer metrics."

    user_prompt = f"""
    Compile a formal executive decision brief based on the following corporate performance aggregates:
    
    Corporate KPI Summary:
    - Target Industry Sector: {industry}
    - Business Health Score: {kpis['health_score']}/100 ({kpis['health_status']})
    - Total Revenue: ${kpis['total_revenue']:,.2f}
    {profit_context_line}
    - Top Region by Volume: {kpis['top_region']} (Revenue: ${kpis['top_region_rev']:,.2f})
    - Top Product Segment by Volume: {kpis['top_product']} (Revenue: ${kpis['top_product_rev']:,.2f})
    
    Growth & Trends:
    - Overall timeline displays {growth_stmt}.
    
    Your response MUST format exactly as a Markdown document with these specific sections. Do NOT deviate from this structure:

    ## Executive Summary
    [A concise 2-3 paragraph summary of overall health, key performance drivers, and the strategic outlook for the company, incorporating the Business Health Score and high-level KPIs.]

    ## Key Business Findings
    [Provide 3-4 bulleted structural insights on business operations, region distribution, product performance, and growth trends. Highlight a Priority Matrix.]

    ## Critical Risks
    [Detail 2 critical risks using this structured C-suite template for each risk. Use the exact formatting below:
    - **Issue**: [Short Description]
    - **Priority**: [HIGH/MEDIUM/LOW]
    - **Confidence**: [Percentage]%
    - **Evidence**: [Data-backed evidence from metrics]
    - **Business Impact**: [Potential corporate financial/operational impact]
    - **Recommendation**: [Actionable consulting guidance]
    ]

    ## Growth Opportunities
    [Provide 2 structural growth opportunities utilizing the exact same template style:
    - **Issue**: [Short Description]
    - **Priority**: [HIGH/MEDIUM/LOW]
    - **Confidence**: [Percentage]%
    - **Evidence**: [Data-backed evidence from metrics]
    - **Business Impact**: [Potential corporate financial/operational impact]
    - **Recommendation**: [Actionable consulting guidance]
    ]

    ## Strategic Recommendations
    [Provide 3-4 highly detailed, actionable recommendations specifically matching the {industry} sector to improve margins/sales and sustain growth. Highlight the next quarter action plan.]

    ## Expected Business Impact
    [Explain the expected quantitative and qualitative business impact of implementing these recommendations (e.g. ARR improvements, operational cost reductions, customer retention wins).]

    Tone: Formal, strategic, quantitative, and consulting-ready. Do not mention Python, Pandas, dataframes, or dashboards.
    """
    
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6
    )
    return response.choices[0].message.content


def generate_rule_based_report(kpis, df_clean, date_col, region_col, product_col, revenue_col, profit_col, industry):
    """Generates an executive-level strategic report based on analytical rules. Gracefully handles missing profit data."""
    if df_clean is None or df_clean.empty:
        return "## Executive Summary\nStrategic briefing unavailable because the loaded dataset is empty or invalid."
        
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

    # Executive Summary Text
    if has_profit:
        exec_summary_text = (
            f"The corporation completed the observed period with **Total Revenue** of **${kpis['total_revenue']:,.2f}** "
            f"and **Total Profit** of **${kpis['total_profit']:,.2f}**, indicating a consolidated operational "
            f"**Profit Margin of {kpis['profit_margin']:.1f}%**. According to our assessment framework, the business registers a "
            f"**Business Health Score of {kpis['health_score']}/100**, placing it in the **{kpis['health_status']}** category. "
            f"Operational volume remains heavily reliant on the **{kpis['top_region']}** market and sales of the **{kpis['top_product']}** segment. "
            f"The macro trend displays {growth_stmt}."
        )
    else:
        exec_summary_text = (
            f"The corporation completed the observed period with **Total Revenue** of **${kpis['total_revenue']:,.2f}**. "
            f"Net profit data is not available in the uploaded dataset. According to our assessment framework, the business registers a "
            f"**Business Health Score of {kpis['health_score']}/100**, placing it in the **{kpis['health_status']}** category. "
            f"Operational volume remains heavily reliant on the **{kpis['top_region']}** market and sales of the **{kpis['top_product']}** segment. "
            f"The macro trend displays {growth_stmt}."
        )

    # Key Findings text
    if has_profit:
        findings_text = (
            f"- **Segment Performance Concentration**: **{kpis['top_product']}** remains the cornerstone of the company's "
            f"sales framework, maintaining a healthy margin of **{best_product_margin:.1f}%**.\n"
            f"- **Regional Dispersion**: The **{kpis['top_region']}** represents the leading geography by sales volume. "
            f"However, significant margin leakages are observed in the **{worst_region}** region.\n"
            f"- **Timeline Analysis**: The company exhibits {growth_stmt}. Sustaining baseline profit levels will require "
            f"immediate cost adjustments and pricing optimizations in lagging sectors."
        )
    else:
        findings_text = (
            f"- **Segment Performance Concentration**: **{kpis['top_product']}** remains the cornerstone of the company's "
            f"sales framework, driving the highest volume equivalent to **${kpis['top_product_rev']:,.2f}**.\n"
            f"- **Regional Dispersion**: The **{kpis['top_region']}** represents the leading geography by sales volume with "
            f"**${kpis['top_region_rev']:,.2f}**. Local operations in other markets lag behind.\n"
            f"- **Timeline Analysis**: The company exhibits {growth_stmt}. Increasing baseline sales levels will require "
            f"expanding customer acquisition and geographic penetration."
        )

    # Industry-specific customized details for Risks/Opportunities/Recommendations
    industry_details = {
        "Retail": {
            "risk_name": f"Inventory Bottlenecks in {worst_product}" if has_profit else "Channel Customer Concentration",
            "risk_evidence": f"Net margin of {worst_product_margin:.1f}% in the {worst_product} segment." if has_profit else f"Category {kpis['top_product']} represents the primary revenue driver.",
            "risk_impact": "Excess working capital tied up in slow-moving stock, driving up warehousing lease expenses.",
            "risk_rec": f"Leverage JIT (just-in-time) inventory ordering systems and execute targeted clearance promotions." if has_profit else "Diversify product offerings across multiple adjacent consumer categories.",
            
            "opp_name": f"Omnichannel Sales Expansion in {kpis['top_region']}",
            "opp_evidence": f"High volume sales in {kpis['top_region']} totaling ${kpis['top_region_rev']:,.0f}.",
            "opp_impact": "Capturing higher customer wallet share and digital sales conversion rates.",
            "opp_rec": f"Deploy personalized digital loyalty campaigns and localized mobile advertising in {kpis['top_region']}.",
            
            "recs": [
                f"**Optimize Retail Supply Chain**: Audit transportation and distribution lanes servicing the low-margin **{worst_region}** region to reduce regional logistics overhead.",
                f"**Establish Dynamic Markdown Rules**: Implement automated markdown analytics to clear underperforming **{worst_product}** stock without destroying base product margins." if has_profit else f"Scale inventory allocations in **{kpis['top_region']}** to match high seasonal demand.",
                f"**Improve In-store and Online Placement**: Cross-sell the high-margin **{kpis['top_product']}** segment with slower-moving inventories to increase basket size."
            ],
            "impact": "Expected to improve regional retail margins by 4.5% and increase inventory turnover velocity by 18% in the next quarter."
        },
        "SaaS": {
            "risk_name": f"Customer Churn & Inefficient CAC for {worst_product}" if has_profit else "Subscription Billing Churn",
            "risk_evidence": f"Net profit margin at {worst_product_margin:.1f}% for {worst_product}." if has_profit else "Vulnerability to multi-period contract dropouts.",
            "risk_impact": "Diluted customer lifetime value (LTV) and high cash burn rate on customer acquisition.",
            "risk_rec": "Revamp customer success onboarding and adjust sales commission structures to prioritize NRR.",
            
            "opp_name": f"Enterprise Tier Upselling in {kpis['top_region']}",
            "opp_evidence": f"High volume regional sales in {kpis['top_region']} (Total: ${kpis['top_region_rev']:,.0f}).",
            "opp_impact": "Increased Average Contract Value (ACV) and higher ARR expansion opportunities.",
            "opp_rec": f"Introduce dedicated enterprise support bundles and custom security SLA add-ons for clients in {kpis['top_region']}.",
            
            "recs": [
                f"**Reduce Customer Success Churn Points**: Deploy automated usage triggers to identify inactive accounts before they churn.",
                f"**Optimize LTV/CAC Metrics**: Redirect paid acquisition budget from the low-performing **{worst_region}** sector to high-performing target demographics.",
                f"**Tiered Feature Pricing**: Move advanced features out of the basic tier into a premium high-margin tier to boost ARPU."
            ],
            "impact": "Anticipated to reduce user churn by 14%, resulting in an ARR expansion of approximately 11% in the next quarter."
        }
    }
 
    ind_data = industry_details.get(industry, industry_details["SaaS"])

    risk_block_1 = f"""- **Issue**: {ind_data['risk_name']}
- **Priority**: HIGH
- **Confidence**: 92%
- **Evidence**: {ind_data['risk_evidence']}
- **Business Impact**: {ind_data['risk_impact']}
- **Recommendation**: {ind_data['risk_rec']}"""

    risk_block_2 = f"""- **Issue**: Regional Operating Cost Inefficiencies in {worst_region}
- **Priority**: MEDIUM
- **Confidence**: 85%
- **Evidence**: Operations based in the {worst_region} territory.
- **Business Impact**: Slower profitability growth and poor regional cash flow generation.
- **Recommendation**: Conduct an operational cost audit of regional offices; consolidate overhead structures."""

    opp_block_1 = f"""- **Issue**: {ind_data['opp_name']}
- **Priority**: HIGH
- **Confidence**: 88%
- **Evidence**: {ind_data['opp_evidence']}
- **Business Impact**: {ind_data['opp_impact']}
- **Recommendation**: {ind_data['opp_rec']}"""

    opp_block_2 = f"""- **Issue**: Margin Expansion for {kpis['top_product']}
- **Priority**: HIGH
- **Confidence**: 90%
- **Evidence**: High demand for the {kpis['top_product']} category.
- **Business Impact**: Major incremental cash flows with minimal operational investment.
- **Recommendation**: Run value-based upsell campaigns; introduce high-margin add-ons to the existing base."""

    report_markdown = f"""
## Executive Summary
{exec_summary_text}

## Key Business Findings
{findings_text}

## Critical Risks
{risk_block_1}

{risk_block_2}

## Growth Opportunities
{opp_block_1}

{opp_block_2}

## Strategic Recommendations
- {ind_data['recs'][0]}
- {ind_data['recs'][1]}
- {ind_data['recs'][2]}

## Expected Business Impact
{ind_data['impact']}
"""
    return report_markdown
