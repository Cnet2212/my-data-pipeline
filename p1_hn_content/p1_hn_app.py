import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='HN Live Content Dashboard', page_icon='📰', layout='wide')

st.markdown('''
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    div[data-testid='stMetricValue'] { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
''', unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if os.path.exists('p1_hn_data.json'):
        with open('p1_hn_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)

    try:
        from p1_hn_db import get_supabase_client
        supabase = get_supabase_client()
        response = supabase.table('hn_stories').select('*').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f'No local data and could not connect to Supabase: {e}')
        return pd.DataFrame(columns=['id', 'title', 'url', 'score', 'author', 'num_comments', 'posted_at'])


df = load_data()

st.title('📰 Hacker News — Live Content Pipeline')
st.caption('Real, live data via the official Hacker News public API')

if df.empty:
    st.info('No data yet. Run `python p1_hn_crawler.py` first.')
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric('Stories Pulled', f'{len(df)}')
c2.metric('Avg Score', f"{df['score'].mean():.0f}")
c3.metric('Avg Comments', f"{df['num_comments'].mean():.0f}")

st.divider()

query = st.text_input('🔍 Search title', placeholder='e.g. AI, rust, startup')
filtered = df.copy()
if query:
    filtered = filtered[filtered['title'].str.contains(query, case=False)]
filtered = filtered.sort_values('score', ascending=False)

chart_col, table_col = st.columns([1, 1])
with chart_col:
    st.markdown('### 📊 Top 15 by Score')
    top15 = filtered.head(15)
    fig = px.bar(top15, x='title', y='score', template='plotly_dark')
    fig.update_layout(paper_bgcolor='#1e293b', plot_bgcolor='#1e293b', xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with table_col:
    st.markdown('### 📋 Stories')
    st.dataframe(
        filtered[['title', 'author', 'score', 'num_comments', 'url']],
        use_container_width=True, hide_index=True,
        column_config={'url': st.column_config.LinkColumn('Link')},
    )
    csv_data = filtered.to_csv(index=False).encode('utf-8')
    st.download_button('📥 Export CSV', data=csv_data, file_name='hn_stories.csv', mime='text/csv')
