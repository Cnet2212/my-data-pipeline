import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px

from shared_dashboard_filters import render_filters

st.set_page_config(page_title='Quotes Dashboard (Authenticated)', page_icon='🔐', layout='wide')

st.markdown('''
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    div[data-testid='stMetricValue'] { color: #38bdf8; font-size: 24px; font-weight: bold; }
    [data-testid='stWidgetLabel'] p { color: #e2e8f0 !important; }
    label { color: #e2e8f0 !important; }
    </style>
''', unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if os.path.exists('p4_login_data.json'):
        with open('p4_login_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)

    try:
        from p4_login_db import get_supabase_client
        supabase = get_supabase_client()
        response = supabase.table('quotes').select('*').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f'No local data and could not connect to Supabase: {e}')
        return pd.DataFrame(columns=['text', 'author', 'tags'])


df = load_data()

st.title('🔐 Quotes Pipeline (Authenticated Session)')
st.caption('Fetched via CSRF-token login + session cookie — the session-handling pattern for any login-gated site')

if df.empty:
    st.info('No data yet. Run `python p4_login_pipeline.py` first.')
    st.stop()

filtered = render_filters(df)

chart_col, table_col = st.columns([1, 1])
with chart_col:
    st.markdown('### 📊 Quotes by Author')
    if filtered.empty:
        st.info('No records match the current filters.')
    else:
        author_counts = filtered['author'].value_counts().reset_index()
        author_counts.columns = ['author', 'count']
        fig = px.bar(author_counts, x='author', y='count', template='plotly_dark')
        fig.update_layout(paper_bgcolor='#1e293b', plot_bgcolor='#1e293b', xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

with table_col:
    st.markdown('### 📋 Quotes')
    st.dataframe(filtered[['text', 'author', 'tags']], use_container_width=True, hide_index=True)
    csv_data = filtered.to_csv(index=False).encode('utf-8')
    st.download_button('📥 Export CSV', data=csv_data, file_name='quotes.csv', mime='text/csv')
