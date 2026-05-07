import streamlit as st
import snowflake.connector
import pandas as pd

st.set_page_config(page_title="Netflix Analytics Dashboard", page_icon="🎬", layout="wide")

# Snowflake connection
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        account=st.secrets["snowflake"]["account"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"]
    )

def run_query(query):
    conn = get_connection()
    return pd.read_sql(query, conn)

# Title
st.title("🎬 Netflix Content Analytics Dashboard")
st.write("Live data from Snowflake analytics views — powered by the Netflix Data Pipeline")
st.divider()

# Row 1: Key Metrics
col1, col2, col3, col4 = st.columns(4)

total = run_query("SELECT COUNT(*) AS cnt FROM NETFLIX_CLEAN")
movies = run_query("SELECT COUNT(*) AS cnt FROM NETFLIX_CLEAN WHERE type = 'Movie'")
tv_shows = run_query("SELECT COUNT(*) AS cnt FROM NETFLIX_CLEAN WHERE type = 'TV Show'")
countries = run_query("SELECT COUNT(DISTINCT country) AS cnt FROM NETFLIX_CLEAN WHERE country != 'Unknown'")

col1.metric("Total Titles", f"{total['CNT'][0]:,}")
col2.metric("Movies", f"{movies['CNT'][0]:,}")
col3.metric("TV Shows", f"{tv_shows['CNT'][0]:,}")
col4.metric("Countries", f"{countries['CNT'][0]:,}")

st.divider()

# Row 2: Content by Year and Top Countries
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Content Added by Year")
    yearly = run_query("SELECT * FROM CONTENT_BY_YEAR WHERE YEAR_ADDED >= 2010")
    if not yearly.empty:
        chart_data = yearly.pivot(index='YEAR_ADDED', columns='TYPE', values='TITLE_COUNT').fillna(0)
        st.bar_chart(chart_data)

with col_right:
    st.subheader("Top 15 Countries")
    countries_df = run_query("SELECT * FROM TOP_COUNTRIES")
    if not countries_df.empty:
        st.bar_chart(countries_df.set_index('COUNTRY_NAME')['TITLE_COUNT'])

st.divider()

# Row 3: Top Genres and Rating Distribution
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Top 15 Genres")
    genres = run_query("SELECT * FROM TOP_GENRES")
    if not genres.empty:
        st.bar_chart(genres.set_index('GENRE')['TITLE_COUNT'])

with col_right2:
    st.subheader("Rating Distribution")
    ratings = run_query("SELECT RATING, SUM(TITLE_COUNT) AS TOTAL FROM RATING_DISTRIBUTION GROUP BY RATING ORDER BY TOTAL DESC")
    if not ratings.empty:
        st.bar_chart(ratings.set_index('RATING')['TOTAL'])

st.divider()

# Row 4: Monthly Patterns
st.subheader("Monthly Content Addition Patterns")
monthly = run_query("SELECT * FROM MONTHLY_ADDITIONS")
if not monthly.empty:
    month_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
                   7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    monthly['MONTH_NAME'] = monthly['MONTH_ADDED'].map(month_names)
    chart_data = monthly.pivot(index='MONTH_NAME', columns='TYPE', values='TITLE_COUNT').fillna(0)
    # Reorder months
    month_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    chart_data = chart_data.reindex(month_order)
    st.bar_chart(chart_data)

# Footer
st.divider()
st.caption("Data pipeline: AWS S3 → Snowflake → Streamlit | Built by Pallabi S Roy")
