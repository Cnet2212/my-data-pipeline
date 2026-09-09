import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Multi-Source Jobs Dashboard', page_icon='💼', layout='wide')

st.markdown('''
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    div[data-testid='stMetricValue'] { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
''', unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if os.path.exists('p2_jobs_unified_data.json'):
        with open('p2_jobs_unified_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)

    try:
        from p2_jobs_unified_db import get_supabase_client
        supabase = get_supabase_client()
        response = supabase.table('jobs_unified').select('*').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f'No local data and could not connect to Supabase: {e}')
        return pd.DataFrame(columns=['source', 'title', 'company', 'location', 'remote', 'url'])


df = load_data()

st.title('💼 Multi-Source Job Aggregation Pipeline')
st.markdown('_Sources: [Remotive](https://remotive.com) + [Arbeitnow](https://www.arbeitnow.com) — normalized, deduplicated, and tracked over time_')

if df.empty:
    st.info('No data yet. Run `python p2_jobs_multisource_pipeline.py` first.')
    st.stop()

# 'status' only exists once history tracking has run at least once
if 'status' in df.columns:
    active_df = df[df['status'] != 'removed']
else:
    active_df = df

c1, c2, c3, c4 = st.columns(4)
c1.metric('Active Postings', f'{len(active_df)}')
c2.metric('Sources', f"{active_df['source'].nunique()}")
c3.metric('Companies', f"{active_df['company'].nunique()}")
salary_count = active_df['salary_min'].notna().sum() if 'salary_min' in active_df.columns else 0
c4.metric('With Parsed Salary', f'{salary_count}')

st.divider()

col_source, col_search = st.columns([1, 3])
with col_source:
    source_filter = st.selectbox('Source', ['All'] + sorted(active_df['source'].unique().tolist()))
with col_search:
    query = st.text_input('🔍 Search title', placeholder='e.g. Engineer, Marketing, QA')

filtered = active_df.copy()
if source_filter != 'All':
    filtered = filtered[filtered['source'] == source_filter]
if query:
    filtered = filtered[filtered['title'].str.contains(query, case=False)]

chart_col, table_col = st.columns([1, 1])
with chart_col:
    st.markdown('### 📊 Postings by Source')
    counts = filtered['source'].value_counts().reset_index()
    counts.columns = ['source', 'count']
    fig = px.bar(counts, x='source', y='count', template='plotly_dark')
    fig.update_layout(paper_bgcolor='#1e293b', plot_bgcolor='#1e293b')
    st.plotly_chart(fig, use_container_width=True)

with table_col:
    st.markdown('### 📋 Postings')
    display_cols = ['source', 'title', 'company', 'location', 'remote', 'url']
    display_cols = [c for c in display_cols if c in filtered.columns]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True, hide_index=True,
        column_config={'url': st.column_config.LinkColumn('Apply')},
    )
    csv_data = filtered.to_csv(index=False).encode('utf-8')
    st.download_button('📥 Export CSV', data=csv_data, file_name='unified_jobs.csv', mime='text/csv')

# Recent activity section — only meaningful once history tracking has run
# more than once (otherwise everything is trivially "new").
if 'status' in df.columns and (df['status'] == 'removed').any():
    st.divider()
    st.markdown('### 🕒 Recently Removed Postings')
    removed = df[df['status'] == 'removed'][['source', 'title', 'company', 'last_seen_at']]
    st.dataframe(removed, use_container_width=True, hide_index=True)
