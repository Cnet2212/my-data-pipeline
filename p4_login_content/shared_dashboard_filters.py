"""
Shared "Excel-like" filter panel for Streamlit dashboards — reused
identically across every project (same pattern as shared_data_quality.py).

Every column (numeric or text) gets a multiselect checklist of its exact
unique values by default — genuine Excel-column-filter behavior, not a
"contains" search. st.multiselect already has a type-to-filter search box
built into its own dropdown, so this stays usable even with many distinct
values; you don't lose search, it's just search-within-the-checklist
rather than search-instead-of-a-checklist.

Column type handling:
  - list-valued column (tags)  -> multiselect built from the union of all values
  - boolean column              -> All/True/False selectbox
  - column in force_search_cols -> free-text "contains" search (explicit opt-in only —
                                    use this only for a genuinely long free-text field,
                                    like a full description, where listing every
                                    unique value would be meaningless)
  - everything else              -> multiselect of exact unique values (default)

Usage in any project's app.py:

    from shared_dashboard_filters import render_filters

    filtered_df = render_filters(df, exclude_cols=['url'])
    # or, to force one specific free-text field to use search instead of a checklist:
    filtered_df = render_filters(df, exclude_cols=['url'], force_search_cols=['description'])

CAVEAT — nullable numeric columns: a column with legitimately missing
values (NaN) for some rows should go in exclude_cols and be handled with
a separate manual widget (e.g. an "All / only present / only missing"
selectbox), since a checklist of exact values can't represent "no value"
cleanly alongside real values.
"""
import pandas as pd
import streamlit as st


def render_filters(
    df: pd.DataFrame,
    exclude_cols: list[str] | None = None,
    force_search_cols: list[str] | None = None,
) -> pd.DataFrame:
    exclude_cols = set(exclude_cols or [])
    force_search_cols = set(force_search_cols or [])
    filtered = df.copy()

    with st.expander('🔧 Filters', expanded=False):
        for col in df.columns:
            if col in exclude_cols:
                continue
            series = df[col]

            # List-valued column (e.g. tags) — checked first since a list
            # column's dtype otherwise reads as generic "object".
            if series.apply(lambda v: isinstance(v, list)).any():
                all_values = sorted({v for row in series.dropna() for v in (row or [])})
                if not all_values:
                    continue
                selected = st.multiselect(col, all_values, key=f'filt_{col}')
                if selected:
                    filtered = filtered[filtered[col].apply(
                        lambda row, sel=selected: any(v in (row or []) for v in sel)
                    )]
                continue

            if pd.api.types.is_bool_dtype(series):
                choice = st.selectbox(col, ['All', 'True', 'False'], key=f'filt_{col}')
                if choice != 'All':
                    filtered = filtered[filtered[col] == (choice == 'True')]
                continue

            if col in force_search_cols:
                query = st.text_input(f'{col} contains', key=f'filt_{col}')
                if query:
                    filtered = filtered[filtered[col].astype(str).str.contains(query, case=False, na=False)]
                continue

            # Default: Excel-style checklist of exact values, for numeric
            # AND text columns alike.
            options = sorted(series.dropna().unique().tolist())
            if not options:
                continue
            selected = st.multiselect(col, options, key=f'filt_{col}')
            if selected:
                filtered = filtered[filtered[col].isin(selected)]

    st.caption(f'Showing {len(filtered)} of {len(df)} records')
    return filtered
