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

# Sidebar navigation
page = st.sidebar.radio("Navigate", ["📊 Dashboard", "💡 Business Insights"])

# ============================================
# PAGE 1: DASHBOARD
# ============================================
if page == "📊 Dashboard":
    st.title("🎬 Netflix Content Analytics Dashboard")
    st.write("Live data from Snowflake analytics views — powered by the Netflix Data Pipeline")
    st.divider()

    # Key Metrics
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

    # Content by Year and Top Countries
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

    # Top Genres and Rating Distribution
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

    # Monthly Patterns
    st.subheader("Monthly Content Addition Patterns")
    monthly = run_query("SELECT * FROM MONTHLY_ADDITIONS")
    if not monthly.empty:
        month_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
                       7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
        monthly['MONTH_NAME'] = monthly['MONTH_ADDED'].map(month_names)
        chart_data = monthly.pivot(index='MONTH_NAME', columns='TYPE', values='TITLE_COUNT').fillna(0)
        month_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        chart_data = chart_data.reindex(month_order)
        st.bar_chart(chart_data)

    st.divider()
    st.caption("Data pipeline: AWS S3 → Snowflake → Streamlit | Built by Pallabi Roy Singh")

# ============================================
# PAGE 2: BUSINESS INSIGHTS
# ============================================
elif page == "💡 Business Insights":
    st.title("💡 Business Insights & Recommendations")
    st.write("Data-driven strategic recommendations for Netflix content investment")
    st.divider()

    # Insight 1: TV Show Shift
    st.subheader("1. The TV Show Shift")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("""
        Netflix is actively shifting its content mix toward TV Shows. The TV Show share 
        has grown from under 10% before 2015 to over 40% by 2021. TV shows drive longer 
        engagement through multiple episodes and seasons, which directly reduces subscriber churn.
        """)
    with col2:
        tv_ratio = run_query("""
            SELECT type, COUNT(*) AS cnt FROM NETFLIX_CLEAN GROUP BY type
        """)
        if not tv_ratio.empty:
            st.dataframe(tv_ratio, hide_index=True)

    st.success("**Recommendation:** Continue increasing TV Show production toward a 50/50 split with movies by 2025.")
    st.divider()

    # Insight 2: India Opportunity
    st.subheader("2. India is the Biggest Growth Opportunity")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("""
        India is the second-largest content market on Netflix with 1,046 titles, but relative 
        to its 1.4 billion population, it is massively underrepresented. Indian content also 
        performs well in the International category, which is Netflix's fastest-growing genre segment.
        """)
    with col2:
        top5 = run_query("SELECT * FROM TOP_COUNTRIES LIMIT 5")
        if not top5.empty:
            st.dataframe(top5, hide_index=True)

    st.success("**Recommendation:** Invest heavily in Indian original content across Bollywood, regional languages, and documentaries.")
    st.divider()

    # Insight 3: Family Content Gap
    st.subheader("3. The Family Content Gap")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("""
        TV-MA (mature audiences) dominates the catalog with 3,207 titles. Family-friendly content 
        (TV-Y, TV-Y7, TV-G, PG) combined accounts for only about 13% of the library. This is a 
        segment where competitors like Disney+ dominate. A family subscribing for kids' content 
        often stays for adult content too — it's a two-for-one acquisition strategy.
        """)
    with col2:
        family = run_query("""
            SELECT rating, SUM(TITLE_COUNT) AS total 
            FROM RATING_DISTRIBUTION 
            GROUP BY rating 
            ORDER BY total DESC LIMIT 8
        """)
        if not family.empty:
            st.dataframe(family, hide_index=True)

    st.success("**Recommendation:** Expand family-friendly programming to capture household subscriptions and compete with Disney+.")
    st.divider()

    # Insight 4: Single Season Problem
    st.subheader("4. The Single-Season Problem")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("""
        Most TV shows on Netflix have only 1 season. This could indicate high cancellation rates 
        or a deliberate limited-series strategy. Either way, multi-season shows create appointment 
        viewing — subscribers waiting for the next season are significantly less likely to cancel.
        """)
    with col2:
        seasons = run_query("""
            SELECT duration_num AS seasons, COUNT(*) AS shows 
            FROM NETFLIX_CLEAN 
            WHERE type = 'TV Show' AND duration_num IS NOT NULL
            GROUP BY duration_num 
            ORDER BY duration_num
        """)
        if not seasons.empty:
            st.dataframe(seasons, hide_index=True)

    st.success("**Recommendation:** Invest in renewing successful shows for multiple seasons to build franchise value and reduce churn.")
    st.divider()

    # Insight 5: South Korea
    st.subheader("5. South Korean Content Has Global Appeal")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("""
        South Korea has only 231 titles on Netflix but Korean content (K-dramas, K-movies) has 
        demonstrated massive global appeal. The success of titles like Squid Game proves that 
        Korean content transcends language barriers. This market is significantly underinvested 
        relative to its global impact potential.
        """)
    with col2:
        korea = run_query("""
            SELECT TRIM(value) AS country, COUNT(*) AS titles
            FROM NETFLIX_CLEAN,
                LATERAL FLATTEN(input => SPLIT(country, ','))
            WHERE TRIM(value) IN ('South Korea', 'Japan', 'India', 'United Kingdom', 'United States')
            GROUP BY TRIM(value)
            ORDER BY titles DESC
        """)
        if not korea.empty:
            st.dataframe(korea, hide_index=True)

    st.success("**Recommendation:** Significantly expand South Korean content investment — high global appeal with relatively low production costs.")
    st.divider()

    # Insight 6: Release Timing
    st.subheader("6. Strategic Release Timing")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("""
        Content additions peak in December-January (holiday season) and July (summer). 
        February and April see the lowest additions. Netflix already optimizes for peak 
        viewing periods, but quiet months represent an opportunity — a major release in 
        February faces less competition for viewer attention.
        """)
    with col2:
        monthly = run_query("SELECT * FROM MONTHLY_ADDITIONS")
        if not monthly.empty:
            month_total = monthly.groupby('MONTH_ADDED')['TITLE_COUNT'].sum().reset_index()
            month_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
                           7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
            month_total['MONTH'] = month_total['MONTH_ADDED'].map(month_names)
            st.dataframe(month_total[['MONTH', 'TITLE_COUNT']], hide_index=True)

    st.success("**Recommendation:** Use quiet months (February, April) for tentpole releases to maximize impact with less competition.")
    st.divider()

    st.caption("Data pipeline: AWS S3 → Snowflake → Streamlit | Built by Pallabi S Roy")
