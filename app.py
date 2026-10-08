import streamlit as st
import pandas as pd
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

from src.data_processing import load_data, detect_columns, clean_dataset
from src.kpis import calculate_kpis, format_metric_val, truncate_label
from src.charts import (
    render_revenue_by_region,
    render_profit_by_product,
    render_monthly_revenue_trend,
    render_revenue_vs_profit
)
from src.report import generate_openai_report, generate_rule_based_report
from src.pdf_generator import generate_pdf_report
from src.copilot import (
    is_question_related_to_data,
    calculate_business_confidence,
    generate_openai_copilot_response,
    generate_rule_based_copilot_response
)
from src.ppt_generator import generate_executive_presentation

st.set_page_config(
    page_title="AI Executive Decision Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
    .block-container {
        max-width: 1400px;
        padding-left: 2rem;
        padding-right: 2rem;
        margin: 0 auto;
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1a365d 0%, #319795 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 1rem;
        color: #718096;
        margin-bottom: 25px;
    }
    
    .kpi-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 18px 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s, border-color 0.2s;
        text-align: left;
        height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 15px;
    }
    @media (prefers-color-scheme: light) {
        .kpi-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.015);
        }
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px rgba(0, 0, 0, 0.08);
        border-color: rgba(49, 151, 149, 0.4);
    }
    .kpi-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #718096;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        margin: 4px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #1a202c;
    }
    @media (prefers-color-scheme: dark) {
        .kpi-value {
            color: #f7fafc;
        }
    }
    .kpi-delta {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .kpi-delta.positive {
        color: #38a169;
    }
    .kpi-delta.neutral {
        color: #3182ce;
    }
    .kpi-delta.negative {
        color: #e53e3e;
    }

    section[data-testid="stSidebar"] {
        background-color: #0f172a !important; 
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #e2e8f0 !important;
    }
    
    div.element-container:has(iframe) {
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.02);
        padding: 10px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    @media (prefers-color-scheme: light) {
        div.element-container:has(iframe) {
            background: #ffffff;
            border: 1px solid #e2e8f0;
        }
    }
    
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        color: #718096 !important;
        border-bottom: 2px solid transparent !important;
        transition: color 0.15s, border-color 0.15s;
    }
    button[aria-selected="true"] {
        color: #1a365d !important;
        border-bottom: 2px solid #319795 !important;
    }
    @media (prefers-color-scheme: dark) {
        button[aria-selected="true"] {
            color: #f7fafc !important;
            border-bottom: 2px solid #319795 !important;
        }
    }
    
    div.stButton button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: background-color 0.15s, transform 0.1s !important;
    }
    div.stButton button:hover {
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("## 📊 Control Panel")

industry = st.sidebar.selectbox(
    "💼 Industry Focus",
    ["SaaS", "Retail", "Banking", "Healthcare", "Manufacturing", "Technology", "Telecommunications"],
    index=0,
    help="Modifies the executive briefing rules and prompt configurations to target industry-specific metrics."
)

uploaded_file = st.sidebar.file_uploader("Upload Business Dataset (CSV)", type=["csv"])

openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
openai_model = "gpt-4o" 

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ System Status")
if openai_api_key:
    st.sidebar.success("🟢 AI Mode: Enabled")
else:
    st.sidebar.info("🔵 AI Mode: Rule-based fallback")

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size:0.8rem; color:#718096; line-height:1.4;'>
Developed by <b>Tetali Naga Sai Sushumna Reddy</b><br>
B.Tech Electrical Engineering,<br>
IIT (ISM) Dhanbad
</div>
""", unsafe_allow_html=True)

if 'report_markdown' not in st.session_state:
    st.session_state.report_markdown = None
if 'report_industry' not in st.session_state:
    st.session_state.report_industry = industry

if st.session_state.report_industry != industry:
    st.session_state.report_markdown = None
    st.session_state.report_industry = industry

uploaded_dataset = None
using_sample = False

if uploaded_file is not None:
    uploaded_dataset = load_data(uploaded_file)
else:
    sample_path = "sample_sales_data.csv"
    if os.path.exists(sample_path):
        uploaded_dataset = load_data(sample_path)
        using_sample = True
    else:
        st.sidebar.warning("No dataset uploaded, and sample_sales_data.csv not found.")

st.markdown("<h1 class='main-title'>AI Executive Decision Intelligence Platform</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>AI-powered executive analytics for business strategy, performance monitoring and decision support.</p>", unsafe_allow_html=True)

if uploaded_dataset is not None:
    if using_sample:
        st.info("ℹ️ Automatically loaded **sample_sales_data.csv** for demonstration. Upload your own CSV in the sidebar at any time!")

    detected_cols = detect_columns(uploaded_dataset)

    with st.sidebar.expander("🔧 Column Mapping Configuration", expanded=False):
        st.markdown("Ensure the fields below map correctly to your CSV columns:")
        date_col = st.selectbox("Date / Month Column", uploaded_dataset.columns, index=list(uploaded_dataset.columns).index(detected_cols['date']))
        region_col = st.selectbox("Region Column", uploaded_dataset.columns, index=list(uploaded_dataset.columns).index(detected_cols['region']))
        product_col = st.selectbox("Product / Category Column", uploaded_dataset.columns, index=list(uploaded_dataset.columns).index(detected_cols['product']))
        revenue_col = st.selectbox("Revenue / Sales Column", uploaded_dataset.columns, index=list(uploaded_dataset.columns).index(detected_cols['revenue']))
        
        profit_options = [None] + list(uploaded_dataset.columns)
        profit_index = profit_options.index(detected_cols['profit']) if detected_cols['profit'] in profit_options else 0
        profit_col = st.selectbox("Profit Column (Optional)", profit_options, index=profit_index)

    cleaned_dataset = clean_dataset(uploaded_dataset, date_col, region_col, product_col, revenue_col, profit_col)

    if cleaned_dataset is None or cleaned_dataset.empty:
        st.warning("⚠️ The mapped dataset contains no valid records or matches. Please adjust your Column Mapping Configuration or upload a valid CSV file.")
        
        st.markdown("### Diagnostic: Raw CSV Preview")
        st.dataframe(uploaded_dataset, width='stretch')
    else:
        kpis = calculate_kpis(cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col)
        has_profit = profit_col and profit_col in cleaned_dataset.columns

        tab_dash, tab_report, tab_copilot, tab_preview = st.tabs([
            "📊 Executive Dashboard", 
            "💼 Executive Brief", 
            "🤖 AI Consultant", 
            "🔍 Data Preview"
        ])

        with tab_dash:
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            formatted_revenue = format_metric_val(kpis['total_revenue'], prefix="$")
            formatted_profit = format_metric_val(kpis['total_profit'], prefix="$") if has_profit else "N/A"
            formatted_margin = f"{kpis['profit_margin']:.1f}%" if has_profit else "N/A"
            
            with col1:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Total Revenue</div>
                    <div class="kpi-value">{formatted_revenue}</div>
                    <div class="kpi-delta positive">▲ Consolidated</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Total Profit</div>
                    <div class="kpi-value">{formatted_profit}</div>
                    <div class="kpi-delta positive">▲ Net Earnings</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col3:
                margin_color_class = "positive" if kpis['profit_margin'] >= 15 else ("neutral" if kpis['profit_margin'] >= 5 else "negative")
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Profit Margin</div>
                    <div class="kpi-value">{formatted_margin}</div>
                    <div class="kpi-delta {margin_color_class}">● Operating ratio</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col4:
                health_color_map = {
                    "Robust": "#38a169",
                    "Stable": "#3182ce",
                    "Vulnerable": "#e53e3e"
                }
                health_color = health_color_map.get(kpis['health_status'], "#3182ce")
                st.markdown(f"""
                <div class="kpi-card" style="border-left: 5px solid {health_color};">
                    <div class="kpi-label">Health Score</div>
                    <div class="kpi-value" style="color: {health_color};">{kpis['health_score']}<span style="font-size: 0.8rem; color: #718096; font-weight: normal;">/100</span></div>
                    <div class="kpi-delta" style="color: {health_color}; font-weight: 700;">● {kpis['health_status']}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col5:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Top Region</div>
                    <div class="kpi-value" style="font-size: 1.25rem;">{truncate_label(kpis['top_region'], 15)}</div>
                    <div class="kpi-delta neutral">Sales: {format_metric_val(kpis['top_region_rev'], prefix="$")}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col6:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Top Category</div>
                    <div class="kpi-value" style="font-size: 1.25rem;">{truncate_label(kpis['top_product'], 15)}</div>
                    <div class="kpi-delta neutral">Sales: {format_metric_val(kpis['top_product_rev'], prefix="$")}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                try:
                    fig_region = render_revenue_by_region(cleaned_dataset, region_col, revenue_col)
                    st.plotly_chart(fig_region, use_container_width=True)
                except Exception as e:
                    st.error(f"Error rendering Regional chart: {e}")

            with chart_col2:
                if has_profit:
                    try:
                        fig_product = render_profit_by_product(cleaned_dataset, product_col, profit_col)
                        st.plotly_chart(fig_product, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error rendering Product chart: {e}")
                else:
                    st.info("📊 **Top 10 Products by Profitability**: This visualization is unavailable because the uploaded dataset does not contain profit information.")

            chart_col3, chart_col4 = st.columns(2)

            with chart_col3:
                try:
                    fig_trend = render_monthly_revenue_trend(cleaned_dataset, date_col, revenue_col)
                    st.plotly_chart(fig_trend, use_container_width=True)
                except Exception as e:
                    st.error(f"Error rendering Revenue Trend: {e}")

            with chart_col4:
                if has_profit:
                    try:
                        fig_comp = render_revenue_vs_profit(cleaned_dataset, date_col, revenue_col, profit_col)
                        st.plotly_chart(fig_comp, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error rendering Revenue vs Profit chart: {e}")
                else:
                    st.info("🔄 **Revenue vs Profit Comparison**: This visualization is unavailable because the uploaded dataset does not contain profit information.")

        with tab_report:
            st.markdown("## 🤖 C-Suite Decision Support Engine")
            st.markdown(f"Generate consulting-ready briefings tailored for **{industry}** sector leadership.")
            st.info("💡 **AI Transparency Note:** Recommendations are generated using calculated KPIs, detected trends, and the uploaded dataset. They are intended to support decision-making and should be validated by a human analyst before business use.")
            
            if st.session_state.report_markdown is not None:
                gen_col1, gen_col2, gen_col3 = st.columns([1.5, 2, 2.5])
                with gen_col1:
                    btn_generate = st.button("🚀 Regenerate Briefing", type="primary", use_container_width=True)
                with gen_col2:
                    try:
                        pdf_data = generate_pdf_report(
                            kpis, cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col,
                            st.session_state.report_markdown, industry
                        )
                        st.download_button(
                            label="📥 Download Executive Brief (PDF)",
                            data=pdf_data,
                            file_name=f"Executive_Brief_{industry}_{datetime.date.today().strftime('%Y-%m-%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="pdf_download_btn"
                        )
                    except Exception as e:
                        st.error(f"Failed to generate PDF Brief: {e}")
                with gen_col3:
                    try:
                        pptx_data = generate_executive_presentation(
                            kpis, cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col,
                            st.session_state.report_markdown, industry
                        )
                        st.download_button(
                            label="📊 Download Board PPTX",
                            data=pptx_data,
                            file_name=f"Executive_Business_Report_{industry}_{datetime.date.today().strftime('%Y-%m-%d')}.pptx",
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            use_container_width=True,
                            key="pptx_download_btn"
                        )
                    except Exception as e:
                        st.error(f"Failed to generate Presentation: {e}")
            else:
                btn_generate = st.button("🚀 Generate Briefing", type="primary")

            if btn_generate:
                if openai_api_key:
                    st.info("Querying OpenAI Decision Engine...")
                    try:
                        report_content = generate_openai_report(
                            kpis, cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col,
                            openai_api_key, openai_model, industry
                        )
                        st.session_state.report_markdown = report_content
                        st.success("Board briefing successfully compiled via LLM engine!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"LLM compilation failed: {e}. Defaulting to Local Heuristics engine.")
                        try:
                            report_content = generate_rule_based_report(
                                kpis, cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col, industry
                            )
                            st.session_state.report_markdown = report_content
                            st.success("Board briefing compiled successfully via Local Heuristics engine!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Fallback generation failed: {ex}")
                else:
                    try:
                        report_content = generate_rule_based_report(
                            kpis, cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col, industry
                        )
                        st.session_state.report_markdown = report_content
                        st.success("Board briefing compiled successfully via Local Heuristics engine!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Local heuristics report generation failed: {e}")

            if st.session_state.report_markdown is not None:
                st.markdown("---")
                
                formatted_report = st.session_state.report_markdown
                
                formatted_report = formatted_report.replace("## Executive Summary", "### 📝 Executive Summary")
                formatted_report = formatted_report.replace("## Key Business Findings", "### 🔍 Key Business Findings")
                formatted_report = formatted_report.replace("## Critical Risks", "### ⚠️ Critical Risks")
                formatted_report = formatted_report.replace("## Growth Opportunities", "### 📈 Growth Opportunities")
                formatted_report = formatted_report.replace("## Strategic Recommendations", "### 🎯 Strategic Recommendations")
                formatted_report = formatted_report.replace("## Expected Business Impact", "### 📊 Expected Business Impact")
                
                st.markdown(formatted_report)

        with tab_copilot:
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            if 'pending_question' not in st.session_state:
                st.session_state.pending_question = None
            if 'copilot_input' not in st.session_state:
                st.session_state.copilot_input = ""

            st.markdown("### 🤖 Business Consultant Copilot")
            st.markdown("Ask a question about your uploaded business data. The copilot analyzes the dataset and presents findings in C-suite structured briefing templates.")
            st.info("💡 **AI Transparency Note:** Recommendations are generated using calculated KPIs, detected trends, and the uploaded dataset. They are intended to support decision-making and should be validated by a human analyst before business use.")

            if st.session_state.pending_question:
                pending_query = st.session_state.pending_question
                st.session_state.pending_question = None
                
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": pending_query,
                    "timestamp": timestamp
                })
                
                if not is_question_related_to_data(pending_query):
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": "I can only answer questions related to the uploaded business dataset.",
                        "timestamp": timestamp,
                        "confidence": 100
                    })
                else:
                    with st.spinner("Accenture Strategy Consultant is analyzing dataset..."):
                        confidence = calculate_business_confidence(cleaned_dataset)
                        if openai_api_key:
                            try:
                                copilot_response = generate_openai_copilot_response(
                                    pending_query, st.session_state.chat_history[:-1], kpis, cleaned_dataset, 
                                    date_col, region_col, product_col, revenue_col, profit_col,
                                    openai_api_key, openai_model, industry
                                )
                            except Exception as e:
                                copilot_response = f"Failed to generate response via OpenAI: {e}. Defaulting to Local Heuristics."
                                try:
                                    copilot_response = generate_rule_based_copilot_response(
                                        pending_query, kpis, cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col, industry
                                    )
                                except Exception as ex:
                                    copilot_response = f"Error in local heuristics copilot: {ex}"
                        else:
                            try:
                                copilot_response = generate_rule_based_copilot_response(
                                    pending_query, kpis, cleaned_dataset, date_col, region_col, product_col, revenue_col, profit_col, industry
                                )
                            except Exception as e:
                                copilot_response = f"Error generating rule-based response: {e}"
                        
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": copilot_response,
                            "timestamp": timestamp,
                            "confidence": confidence
                        })
                st.rerun()

            col_desc, col_clear = st.columns([5, 1])
            with col_clear:
                if st.button("🧹 Clear Chat History", use_container_width=True):
                    st.session_state.chat_history = []
                    st.session_state.copilot_input = ""
                    st.rerun()

            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        with st.chat_message("user", avatar="👤"):
                            st.markdown(msg["content"])
                            st.markdown(f"<p style='font-size:0.75rem; color:#718096; margin:0;'>{msg['timestamp']}</p>", unsafe_allow_html=True)
                    else:
                        with st.chat_message("assistant", avatar="💼"):
                            st.markdown(f"**Business Confidence:** `{msg['confidence']}%` (based on data completeness)")
                            st.markdown(msg["content"])
                            st.markdown(f"<p style='font-size:0.75rem; color:#718096; margin:0;'>{msg['timestamp']}</p>", unsafe_allow_html=True)

            with st.form(key="copilot_form", clear_on_submit=True):
                user_question = st.text_input(
                    "Ask a question about your uploaded business data:",
                    value=st.session_state.copilot_input,
                    placeholder="Ask anything, e.g., Suggest three strategic initiatives..."
                )
                submit_clicked = st.form_submit_button("💬 Ask AI", type="primary")
                if submit_clicked and user_question.strip():
                    st.session_state.copilot_input = ""
                    st.session_state.pending_question = user_question.strip()
                    st.rerun()

            st.markdown("#### 💡 Example Questions")
            ex_col1, ex_col2, ex_col3 = st.columns(3)
            ex_col4, ex_col5, ex_col6 = st.columns(3)
            
            examples = [
                "Why is revenue decreasing?",
                "Which product performs the worst?",
                "What are the major business risks?",
                "Suggest three strategic initiatives.",
                "Which region should receive additional investment?",
                "Summarize this dataset for the CEO."
            ]
            
            with ex_col1:
                if st.button(examples[0], use_container_width=True):
                    st.session_state.copilot_input = examples[0]
                    st.rerun()
            with ex_col2:
                if st.button(examples[1], use_container_width=True):
                    st.session_state.copilot_input = examples[1]
                    st.rerun()
            with ex_col3:
                if st.button(examples[2], use_container_width=True):
                    st.session_state.copilot_input = examples[2]
                    st.rerun()
            with ex_col4:
                if st.button(examples[3], use_container_width=True):
                    st.session_state.copilot_input = examples[3]
                    st.rerun()
            with ex_col5:
                if st.button(examples[4], use_container_width=True):
                    st.session_state.copilot_input = examples[4]
                    st.rerun()
            with ex_col6:
                if st.button(examples[5], use_container_width=True):
                    st.session_state.copilot_input = examples[5]
                    st.rerun()

        with tab_preview:
            st.markdown("## 🔍 Data Preview & Descriptive Statistics")
            
            col_shape, col_types = st.columns(2)
            with col_shape:
                st.metric("Total Rows", cleaned_dataset.shape[0])
            with col_types:
                st.metric("Total Columns", cleaned_dataset.shape[1])

            st.markdown("### Descriptive Statistics")
            st.dataframe(cleaned_dataset.describe(include='all').astype(str), width='stretch')

            st.markdown("### Raw Loaded Data")
            st.dataframe(cleaned_dataset, width='stretch')

else:
    st.warning("⚠️ Welcome! Please upload a valid CSV file in the sidebar, or place a file named `sample_sales_data.csv` in the root directory to automatically load mock sales records.")
