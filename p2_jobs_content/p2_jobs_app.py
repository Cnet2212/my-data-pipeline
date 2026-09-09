import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Remote Jobs Dashboard', page_icon='💼', layout='wide')

st.markdown('''
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    div[data-testid='stMetricValue'] { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
''', unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if os.path.exists('p2_jobs_data.json'):
        with open('p2_jobs_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)

    try:
        from p2_jobs_db import get_supabase_client
        supabase = get_supabase_client()
        response = supabase.table('jobs').select('*').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f'No local data and could not connect to Supabase: {e}')
        return pd.DataFrame(columns=['id', 'title', 'company', 'category', 'job_type', 'location', 'url'])


df = load_data()

st.title('💼 Remote Job Listings — Live Pipeline')
st.caption('Real, live data via the official Remotive public API')
st.markdown('_Job data provided by [Remotive](https://remotive.com) — visit Remotive for the full listing board._')

if df.empty:
    st.info('No data yet. Run `python p2_jobs_fetcher.py` first.')
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric('Total Jobs', f'{len(df)}')
c2.metric('Categories', f"{df['category'].nunique()}")
c3.metric('Companies', f"{df['company'].nunique()}")

st.divider()

col_search, col_filter = st.columns([3, 1])
with col_search:
    query = st.text_input('🔍 Search title', placeholder='e.g. Python, DevOps, QA')
with col_filter:
    category = st.selectbox('Category', ['All'] + sorted(df['category'].unique().tolist()))

filtered = df.copy()
if category != 'All':
    filtered = filtered[filtered['category'] == category]
if query:
    filtered = filtered[filtered['title'].str.contains(query, case=False)]

chart_col, table_col = st.columns([1, 1])
with chart_col:
    st.markdown('### 📊 Jobs by Category')
    counts = filtered['category'].value_counts().reset_index()
    counts.columns = ['category', 'count']
    fig = px.bar(counts, x='category', y='count', template='plotly_dark')
    fig.update_layout(paper_bgcolor='#1e293b', plot_bgcolor='#1e293b', xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with table_col:
    st.markdown('### 📋 Listings')
    st.dataframe(
        filtered[['title', 'company', 'category', 'job_type', 'location', 'url']],
        use_container_width=True, hide_index=True,
        column_config={'url': st.column_config.LinkColumn('Apply')},
    )
    csv_data = filtered.to_csv(index=False).encode('utf-8')
    st.download_button('📥 Export CSV', data=csv_data, file_name='remote_jobs.csv', mime='text/csv')
