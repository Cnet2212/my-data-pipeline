import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Data Intelligence Dashboard', page_icon='⚡', layout='wide')

st.markdown('''
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    div[data-testid='stMetricValue'] { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
''', unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    # Prefer the local data.json (written by crawler.py) for quick local testing,
    # so Supabase isn't a hard requirement just to try the dashboard.
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)

    # Otherwise, fall back to Supabase
    try:
        from db import get_supabase_client
        supabase = get_supabase_client()
        response = supabase.table('products').select('*').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f'No local data.json and could not connect to Supabase: {e}')
        return pd.DataFrame(columns=['title', 'price', 'category', 'in_stock'])


df = load_data()

st.title('⚡ Enterprise Data Intelligence Pipeline')
st.caption('Real Data Extraction from books.toscrape.com | $0 Infrastructure Cost')

if df.empty:
    st.info('No data yet. Run `python crawler.py` first to generate data.json.')
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric('Total Records', f'{len(df)}')
c2.metric('Categories', f"{df['category'].nunique()}")
c3.metric('Avg Price', f"£{df['price'].mean():.2f}")
c4.metric('In Stock', f"{df['in_stock'].sum()} / {len(df)}")

st.divider()

col_search, col_filter = st.columns([3, 1])
with col_search:
    query = st.text_input('🔍 Quick Keyword Search', placeholder='e.g. Mystery or Travel')
with col_filter:
    category = st.selectbox('Category Filter', ['All'] + sorted(df['category'].unique().tolist()))

filtered_df = df.copy()
if category != 'All':
    filtered_df = filtered_df[filtered_df['category'] == category]
if query:
    filtered_df = filtered_df[filtered_df['title'].str.contains(query, case=False)]

chart_col, table_col = st.columns([1, 1])
with chart_col:
    st.markdown('### 📊 Price Distribution')
    fig = px.bar(filtered_df, x='title', y='price', color='category', template='plotly_dark')
    fig.update_layout(paper_bgcolor='#1e293b', plot_bgcolor='#1e293b', xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with table_col:
    st.markdown('### 📋 Captured Data Records')
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button('📥 Export Cleaned Data (CSV)', data=csv_data, file_name='scraped_data.csv', mime='text/csv')
