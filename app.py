import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BENCHMARK_PATH = "data/processed/salary_benchmark.csv"
JOB_ADS_PATH = "data/raw/job_ads_104.csv"
SOURCE_URL = "https://statdb.mol.gov.tw/"

# Fixed colour per occupation group, so filtering never repaints the remaining groups.
GROUP_ORDER = [
    "Managers and supervisors",
    "Professionals",
    "Technicians and associate professionals",
    "Clerical support",
    "Machine operators and assemblers",
]
GROUP_COLOURS = dict(zip(GROUP_ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))

st.set_page_config(page_title="Taiwan Salary Benchmark", layout="wide")


@st.cache_data
def load_data():
    benchmark = pd.read_csv(BENCHMARK_PATH, dtype={"occupation_code": str})
    ads = pd.read_csv(JOB_ADS_PATH, dtype={"occupation_code": str})
    return benchmark, ads


def twd(value: float) -> str:
    return f"NT${value:,.0f}"


df, ads = load_data()

st.title("Salary Benchmark: Taiwan Electronic Components Manufacturing")
st.caption(
    "Average July regular monthly earnings by occupation, 2021–2024. "
    f"Source: Ministry of Labor (Taiwan), Occupational Wage Survey 職類別薪資調查 ([link]({SOURCE_URL}))."
)
st.info(
    "Each data point is the survey's **average salary for one occupation in one year**, not an "
    "individual's salary. Summary figures below describe the spread across occupations and are "
    "not weighted by headcount, which the survey does not publish."
)

# ---------- Filters ----------
st.sidebar.header("Filters")
years = sorted(df["year"].unique())
selected_years = st.sidebar.multiselect("Years", years, default=years)
selected_groups = st.sidebar.multiselect("Occupation groups", GROUP_ORDER, default=GROUP_ORDER)
st.sidebar.divider()
st.sidebar.markdown(
    "**Data notes**\n\n"
    "- 2021 covers all employees; 2022–2024 cover full-time employees only.\n"
    "- Some 2021 categories were finer than in later years and have been combined. "
    "See `clean.py` for the mapping."
)

filtered = df[df["year"].isin(selected_years) & df["occupation_group"].isin(selected_groups)]

if filtered.empty:
    st.warning("No data matches these filters.")
    st.stop()

# ---------- Overview ----------
st.subheader("Overview")
year_min, year_max = filtered["year"].min(), filtered["year"].max()
salaries = filtered["monthly_salary_twd"]
c1, c2, c3 = st.columns(3)
c1.metric("Years", f"{year_min}–{year_max}" if year_min != year_max else str(year_min))
c2.metric("Occupations", filtered["occupation_code"].nunique())
c3.metric("Median of occupation averages", twd(salaries.median()))
st.caption(
    # "$" is escaped because Streamlit captions treat a pair of "$" as LaTeX.
    f"Middle 50% of occupation averages: {twd(salaries.quantile(0.25))} – {twd(salaries.quantile(0.75))}."
    .replace("$", "\\$")
)

st.divider()

# ---------- Ranking for one year ----------
st.subheader("Occupation ranking")
rank_year = st.selectbox("Year", sorted(filtered["year"].unique(), reverse=True), key="rank_year")
ranking = filtered[filtered["year"] == rank_year].sort_values("monthly_salary_twd")
fig_rank = px.bar(
    ranking,
    x="monthly_salary_twd",
    y="occupation_en",
    color="occupation_group",
    orientation="h",
    color_discrete_map=GROUP_COLOURS,
    category_orders={"occupation_group": GROUP_ORDER},
    custom_data=["occupation_zh", "occupation_group"],
    labels={"monthly_salary_twd": "Average monthly salary (NT$)", "occupation_en": "", "occupation_group": "Group"},
)
fig_rank.update_traces(
    hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>%{customdata[1]}<br>NT$%{x:,.0f}<extra></extra>"
)
fig_rank.update_layout(
    height=max(320, 26 * len(ranking)),
    yaxis={"categoryorder": "array", "categoryarray": ranking["occupation_en"].tolist()},
    xaxis_tickformat=",",
    legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0, "title": None},
    bargap=0.25,
    margin={"l": 10, "r": 10, "t": 40, "b": 10},
)
st.plotly_chart(fig_rank, width="stretch")

# ---------- Spread by group ----------
st.subheader(f"Spread of occupation averages by group, {rank_year}")
fig_strip = px.strip(
    ranking,
    x="monthly_salary_twd",
    y="occupation_group",
    color="occupation_group",
    color_discrete_map=GROUP_COLOURS,
    category_orders={"occupation_group": GROUP_ORDER},
    hover_name="occupation_en",
    labels={"monthly_salary_twd": "Average monthly salary (NT$)", "occupation_group": ""},
)
fig_strip.update_traces(marker={"size": 11, "opacity": 0.85}, jitter=0.5)
fig_strip.update_layout(showlegend=False, xaxis_tickformat=",", height=300, margin={"l": 10, "r": 10, "t": 10, "b": 10})
st.plotly_chart(fig_strip, width="stretch")
st.caption("Each dot is one occupation.")

st.divider()

# ---------- Trend for chosen occupations ----------
st.subheader("Change over time")
default_trend = [
    o for o in [
        "ICT professionals (systems analysis, programming, database and network)",
        "Electrical and electronics engineers",
        "Assemblers",
        "Semiconductor production line operators",
    ] if o in set(filtered["occupation_en"])
]
chosen = st.multiselect(
    "Occupations to compare (up to 6)",
    sorted(filtered["occupation_en"].unique()),
    default=default_trend,
    max_selections=6,
)
if chosen:
    trend = filtered[filtered["occupation_en"].isin(chosen)].sort_values("year")
    fig_trend = px.line(
        trend,
        x="year",
        y="monthly_salary_twd",
        color="occupation_en",
        markers=True,
        color_discrete_sequence=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"],
        category_orders={"occupation_en": chosen},
        labels={"year": "", "monthly_salary_twd": "Average monthly salary (NT$)", "occupation_en": ""},
    )
    fig_trend.update_traces(line={"width": 2}, marker={"size": 8})
    if 2021 in trend["year"].values and 2022 in trend["year"].values:
        fig_trend.add_vline(x=2021.5, line_dash="dot", line_color="grey")
        fig_trend.add_annotation(
            x=2021.5, y=1, yref="paper", text="Survey population changes", showarrow=False,
            xanchor="left", xshift=4, font={"size": 11, "color": "grey"},
        )
    fig_trend.update_layout(
        xaxis={"dtick": 1},
        yaxis_tickformat=",",
        hovermode="x unified",
        legend={"orientation": "h", "y": -0.15, "x": 0},
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
    )
    st.plotly_chart(fig_trend, width="stretch")
    st.caption(
        "Changes between 2021 and 2022 partly reflect the switch from all employees to full-time "
        "employees, so 2022–2024 is the cleaner comparison."
    )

st.divider()

# ---------- Job ads vs survey ----------
st.subheader("Advertised salaries vs the survey benchmark")
st.markdown(
    "A small manual sample of job ads from 104, Taiwan's largest job board, for three occupations. "
    "Most of these ads are for entry or junior roles, while the survey averages all employees in the "
    "occupation, so advertised pay is expected to sit lower."
)
latest_year = df["year"].max()
survey_latest = df[df["year"] == latest_year].set_index("occupation_code")
ads = ads.assign(occupation_en=ads["occupation_code"].map(survey_latest["occupation_en"]))
summary = (
    ads.groupby(["occupation_code", "occupation_en"])["salary_used_twd"]
    .agg(ad_average="mean", ads="count")
    .reset_index()
)
summary["survey"] = summary["occupation_code"].map(survey_latest["monthly_salary_twd"])

fig_ads = go.Figure()
fig_ads.add_trace(go.Scatter(
    x=ads["salary_used_twd"], y=ads["occupation_en"], mode="markers", name="Individual ad",
    marker={"size": 9, "color": "#86b6ef", "line": {"width": 1, "color": "white"}},
    customdata=ads[["advertised_title", "advertised_salary"]],
    hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
))
fig_ads.add_trace(go.Scatter(
    x=summary["ad_average"], y=summary["occupation_en"], mode="markers", name="Average of ads",
    marker={"size": 14, "color": "#2a78d6", "symbol": "diamond", "line": {"width": 2, "color": "white"}},
    hovertemplate="Average of ads: NT$%{x:,.0f}<extra></extra>",
))
fig_ads.add_trace(go.Scatter(
    x=summary["survey"], y=summary["occupation_en"], mode="markers", name=f"Survey average ({latest_year})",
    marker={"size": 14, "color": "#eb6834", "symbol": "line-ns", "line": {"width": 3, "color": "#eb6834"}},
    hovertemplate="Survey: NT$%{x:,.0f}<extra></extra>",
))
fig_ads.update_layout(
    xaxis={"title": "Monthly salary (NT$)", "tickformat": ","},
    yaxis={"title": ""},
    height=340,
    legend={"orientation": "h", "y": 1.0, "yanchor": "bottom", "x": 0},
    margin={"l": 10, "r": 10, "t": 60, "b": 10},
)
st.plotly_chart(fig_ads, width="stretch")
st.caption(
    "Ads with a range use the midpoint; ads stating only a minimum (\"or above\") use that minimum."
)

# ---------- Data ----------
with st.expander("View and download the filtered data"):
    st.dataframe(
        filtered.rename(columns={"monthly_salary_twd": "monthly_salary (NT$)"}),
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Download CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="salary_benchmark_filtered.csv",
        mime="text/csv",
    )
