import pandas as pd
import streamlit as st

@st.cache_data
def load_data(file_path_or_buffer):
    """Safely loads CSV data into a Pandas DataFrame."""
    try:
        data = pd.read_csv(file_path_or_buffer)
        return data
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def detect_columns(df):
    """Detects sales metrics, categories, date, and region columns using smart heuristics."""
    cols = list(df.columns)
    
    # Priority keywords matching business headers (suited for Olist & standard sheets)
    rev_keys = ['revenue', 'sales', 'grand total', 'turnover', 'payment_value', 'price', 'amount', 'total']
    profit_keys = ['profit', 'margin', 'net income', 'earnings', 'gain', 'net']
    date_keys = ['purchase_timestamp', 'order_date', 'date', 'month', 'year', 'timestamp', 'time', 'period']
    region_keys = ['customer_state', 'region', 'country', 'state', 'city', 'territory', 'location', 'zone']
    product_keys = ['product_category_name', 'product', 'category', 'item', 'sku', 'segment', 'type']
    
    def match_col(keys):
        for col in cols:
            col_lower = str(col).lower().strip()
            if col_lower in keys:
                return col
        for col in cols:
            col_lower = str(col).lower()
            if any(k in col_lower for k in keys):
                return col
        return None

    detected = {}
    detected['revenue'] = match_col(rev_keys)
    detected['profit'] = match_col(profit_keys)
    detected['date'] = match_col(date_keys)
    detected['region'] = match_col(region_keys)
    detected['product'] = match_col(product_keys)
    
    # Fallback to numerical non-ID columns for revenue if direct key fails
    if not detected['revenue']:
        for col in cols:
            if df[col].dtype in ['int64', 'float64'] and not any(x in str(col).lower() for x in ['id', 'date', 'year', 'code']):
                detected['revenue'] = col
                break
        if not detected['revenue']:
            detected['revenue'] = cols[3] if len(cols) > 3 else cols[0]
            
    if not detected['date']:
        for col in cols:
            if any(x in str(col).lower() for x in ['date', 'time', 'timestamp', 'day', 'year']):
                detected['date'] = col
                break
        if not detected['date']:
            detected['date'] = cols[0]
            
    if not detected['region']:
        for col in cols:
            if any(x in str(col).lower() for x in ['state', 'country', 'city', 'region', 'location']):
                detected['region'] = col
                break
        if not detected['region']:
            detected['region'] = cols[1] if len(cols) > 1 else cols[0]
            
    if not detected['product']:
        for col in cols:
            if any(x in str(col).lower() for x in ['cat', 'prod', 'name', 'item', 'sku']):
                detected['product'] = col
                break
        if not detected['product']:
            detected['product'] = cols[2] if len(cols) > 2 else cols[0]

    return detected

def clean_dataset(df, date_col, region_col, product_col, revenue_col, profit_col):
    """Cleans types, sanitizes currency formatting, and drops invalid rows without crashing on missing profit metrics."""
    if df is None or df.empty:
        return pd.DataFrame()
        
    df_clean = df.copy()
    
    # Verify column existence for core fields to prevent KeyErrors
    core_cols = [c for c in [date_col, region_col, product_col, revenue_col] if c and c in df_clean.columns]
    if not core_cols:
        return pd.DataFrame()
        
    df_clean = df_clean.dropna(subset=core_cols, how='any')
    
    if date_col in df_clean.columns:
        df_clean[date_col] = pd.to_datetime(df_clean[date_col], errors='coerce')
        df_clean = df_clean.dropna(subset=[date_col])
    
    numeric_cols = []
    if revenue_col in df_clean.columns:
        numeric_cols.append(revenue_col)
    if profit_col and profit_col in df_clean.columns:
        numeric_cols.append(profit_col)
        
    for col in numeric_cols:
        if df_clean[col].dtype == object:
            # Strip currency symbols, commas, spaces before casting
            df_clean[col] = df_clean[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        df_clean = df_clean.dropna(subset=[col])
            
    return df_clean
