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

# Cache the QUERY RESULTS instead, not the connection
@st.cache_data(ttl=600)  # cache results for 10 minutes
def run_query(query):
    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# Sidebar navigation
page = st.sidebar.radio("Navigate", ["📊 Dashboard", "💡 Business Insights", "🔍 Content Gap Analysis"])

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
    st.caption("Data pipeline: AWS S3 → Snowflake → Streamlit | Built by Pallabi S Roy")

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

    # ============================================
# PAGE 3: CONTENT GAP ANALYSIS
# ============================================
elif page == "🔍 Content Gap Analysis":
    st.title("🔍 Content Gap Analysis")
    st.write("Identifying underserved content segments using K-Means clustering on country-genre profiles")
    st.divider()

    # Get country-genre data
    df_gap = run_query("""
        SELECT 
            TRIM(c.value) AS country,
            TRIM(g.value) AS genre,
            COUNT(*) AS title_count
        FROM NETFLIX_CLEAN,
            LATERAL FLATTEN(input => SPLIT(country, ',')) c,
            LATERAL FLATTEN(input => SPLIT(listed_in, ',')) g
        WHERE country != 'Unknown'
        GROUP BY TRIM(c.value), TRIM(g.value)
    """)

    if not df_gap.empty:
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans

        # Build country-genre matrix
        matrix = df_gap.pivot_table(index='COUNTRY', columns='GENRE', values='TITLE_COUNT', fill_value=0)
        matrix['total'] = matrix.sum(axis=1)
        matrix = matrix[matrix['total'] >= 20].drop(columns=['total'])

        # Convert to percentages
        matrix_pct = matrix.div(matrix.sum(axis=1), axis=0) * 100

        # Cluster
        scaler = StandardScaler()
        matrix_scaled = scaler.fit_transform(matrix_pct)
        km = KMeans(n_clusters=4, random_state=42, n_init=10)
        matrix_pct['cluster'] = km.fit_predict(matrix_scaled)

        # Display clusters
        st.subheader("Market Clusters")
        st.write("Countries grouped by similar content profiles using K-Means clustering (K=4)")

        cluster_names = {
            0: "Latin America",
            1: "Europe, India & SE Asia",
            2: "Niche Markets",
            3: "English-speaking & East Asia"
        }

        for c in sorted(matrix_pct['cluster'].unique()):
            countries = matrix_pct[matrix_pct['cluster'] == c].index.tolist()
            cluster_data = matrix_pct[matrix_pct['cluster'] == c].drop(columns=['cluster'])
            top_genres = cluster_data.mean().sort_values(ascending=False).head(5)

            name = cluster_names.get(c, f"Cluster {c}")
            with st.expander(f"Cluster {c+1}: {name} ({len(countries)} countries)", expanded=True):
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.write("**Countries:**")
                    st.write(", ".join(countries))
                with col2:
                    st.write("**Top Genres (% of content):**")
                    st.dataframe(top_genres.reset_index().rename(columns={'index': 'Genre', 0: 'Percentage'}).round(1), hide_index=True)

        st.divider()

        # Gap analysis
        st.subheader("Content Gaps — Investment Opportunities")
        st.write("Genres where each cluster is underserved compared to the global average")

        global_avg = matrix_pct.drop(columns=['cluster']).mean()

        gap_data = []
        for c in sorted(matrix_pct['cluster'].unique()):
            cluster_avg = matrix_pct[matrix_pct['cluster'] == c].drop(columns=['cluster']).mean()
            diff = global_avg - cluster_avg
            top_gaps = diff.sort_values(ascending=False).head(3)
            countries = matrix_pct[matrix_pct['cluster'] == c].index.tolist()
            name = cluster_names.get(c, f"Cluster {c}")

            for genre, gap_size in top_gaps.items():
                if gap_size > 1:
                    gap_data.append({
                        'Market': name,
                        'Sample Countries': ', '.join(countries[:3]),
                        'Underserved Genre': genre,
                        'Gap (%)': round(gap_size, 1)
                    })

        if gap_data:
            gap_df = pd.DataFrame(gap_data)
            st.dataframe(gap_df, hide_index=True, use_container_width=True)

        st.divider()

        # Prescriptive recommendations
        st.subheader("Strategic Recommendations")

        st.success("""
        **1. Latin America: Invest in Action & Adventure**
        Argentina, Brazil, Chile, Colombia, and Mexico are underserved in Action & Adventure content 
        by 2.7% compared to the global average. This is a high-growth region with strong Netflix adoption.
        """)

        st.success("""
        **2. Europe, India & SE Asia: Expand TV Show Production**
        This 32-country cluster is underserved in International TV Shows by 2.8% and Crime TV Shows by 1.0%. 
        Given the global trend toward TV Shows, this represents the largest market opportunity by audience size.
        """)

        st.success("""
        **3. English-speaking & East Asian Markets: More Local Dramas and Comedies**
        Australia, Canada, Japan, and similar markets are underserved in Dramas by 5.7% and Comedies by 3.1%. 
        These are mature markets where localized content can drive retention and reduce churn.
        """)

        st.info("""
        **Methodology:** K-Means clustering (K=4) on country-genre percentage profiles. 
        Countries with fewer than 20 titles were excluded. Gaps measured as the difference between 
        global genre average and cluster genre average.
        """)

    st.divider()
    st.caption("Data pipeline: AWS S3 → Snowflake → ML Clustering → Streamlit | Built by Pallabi S Roy")
