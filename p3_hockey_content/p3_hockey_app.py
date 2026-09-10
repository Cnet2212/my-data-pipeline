import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px

from shared_dashboard_filters import render_filters

st.set_page_config(page_title='NHL Historical Stats Dashboard', page_icon='🏒', layout='wide')

st.markdown('''
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    div[data-testid='stMetricValue'] { color: #38bdf8; font-size: 24px; font-weight: bold; }
    /* Widget labels (multiselect, selectbox, slider, text_input...) use a
       dark-gray color by default, designed for a light theme — invisible
       against our dark background unless forced. */
    [data-testid='stWidgetLabel'] p { color: #e2e8f0 !important; }
    label { color: #e2e8f0 !important; }
    </style>
''', unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if os.path.exists('p3_hockey_data.json'):
        with open('p3_hockey_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)

    try:
        from p3_hockey_db import get_supabase_client
        supabase = get_supabase_client()
        response = supabase.table('hockey_stats').select('*').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.warning(f'No local data and could not connect to Supabase: {e}')
        return pd.DataFrame(columns=['team_name', 'year', 'wins', 'losses', 'win_pct'])


df = load_data()

st.title('🏒 NHL Historical Team Stats')
st.caption('Full season-by-season records via scrapethissite.com — form-filter and full-pagination crawl')

if df.empty:
    st.info('No data yet. Run `python p3_hockey_pipeline.py` first.')
    st.stop()

st.divider()

# ot_losses is excluded from the generic filter panel: it's legitimately
# null for pre-2000 seasons, and a plain numeric range slider would
# silently drop every null row even at its default full-range setting
# (NaN comparisons evaluate False in pandas). Handled with its own
# 3-way selectbox instead.
filtered = render_filters(df, exclude_cols=['ot_losses'])

ot_filter = st.selectbox('OT Losses tracked?', ['All', 'Only tracked (1999+)', 'Only untracked (pre-2000)'])
if ot_filter == 'Only tracked (1999+)':
    filtered = filtered[filtered['ot_losses'].notna()]
elif ot_filter == 'Only untracked (pre-2000)':
    filtered = filtered[filtered['ot_losses'].isna()]

chart_col, table_col = st.columns([1, 1])
with chart_col:
    st.markdown('### 📊 Win % Over Time')
    if filtered['team_name'].nunique() == 1:
        fig = px.line(filtered.sort_values('year'), x='year', y='win_pct', template='plotly_dark')
    else:
        top_teams = filtered.groupby('team_name')['win_pct'].mean().nlargest(10).index
        fig = px.line(filtered[filtered['team_name'].isin(top_teams)].sort_values('year'),
                      x='year', y='win_pct', color='team_name', template='plotly_dark')
    fig.update_layout(paper_bgcolor='#1e293b', plot_bgcolor='#1e293b')
    st.plotly_chart(fig, use_container_width=True)

with table_col:
    st.markdown('### 📋 Records')
    st.dataframe(
        filtered[['team_name', 'year', 'wins', 'losses', 'ot_losses', 'win_pct', 'goals_for', 'goals_against', 'goal_diff']],
        use_container_width=True, hide_index=True,
    )
    csv_data = filtered.to_csv(index=False).encode('utf-8')
    st.download_button('📥 Export CSV', data=csv_data, file_name='hockey_stats.csv', mime='text/csv')
