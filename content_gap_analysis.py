import snowflake.connector
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

def get_connection():
    return snowflake.connector.connect(
        user='PALLABISROY',
        password='Maadeuta@505050',
        account='ou22699.ap-southeast-7.aws',
        warehouse='NETFLIX_WH',
        database='NETFLIX_DB',
        schema='ANALYTICS'
    )

def run_analysis():
    conn = get_connection()
    
    # Get country-genre matrix
    df = pd.read_sql("""
        SELECT 
            TRIM(c.value) AS country,
            TRIM(g.value) AS genre,
            COUNT(*) AS title_count
        FROM NETFLIX_CLEAN,
            LATERAL FLATTEN(input => SPLIT(country, ',')) c,
            LATERAL FLATTEN(input => SPLIT(listed_in, ',')) g
        WHERE country != 'Unknown'
        GROUP BY TRIM(c.value), TRIM(g.value)
        ORDER BY title_count DESC
    """, conn)
    
    # Pivot: rows = countries, columns = genres, values = title count
    matrix = df.pivot_table(index='COUNTRY', columns='GENRE', values='TITLE_COUNT', fill_value=0)
    
    # Keep only countries with at least 20 titles
    matrix['total'] = matrix.sum(axis=1)
    matrix = matrix[matrix['total'] >= 20].drop(columns=['total'])
    
    print(f"Countries with 20+ titles: {len(matrix)}")
    print(f"Genres: {len(matrix.columns)}")
    
    # Normalize: convert counts to percentages (content profile)
    matrix_pct = matrix.div(matrix.sum(axis=1), axis=0) * 100
    
    # Scale for clustering
    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix_pct)
    
    # Find optimal K using inertia
    inertias = []
    for k in range(2, 8):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(matrix_scaled)
        inertias.append((k, km.inertia_))
        print(f"K={k}, Inertia={km.inertia_:.0f}")
    
    # Use K=4 (good balance for this data)
    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    matrix_pct['cluster'] = km.fit_predict(matrix_scaled)
    
    # Analyze each cluster
    print("\n" + "=" * 60)
    print("CLUSTER PROFILES")
    print("=" * 60)
    
    for c in sorted(matrix_pct['cluster'].unique()):
        cluster_countries = matrix_pct[matrix_pct['cluster'] == c]
        print(f"\nCluster {c}: {len(cluster_countries)} countries")
        print(f"Countries: {', '.join(cluster_countries.index.tolist()[:10])}")
        
        # Top genres in this cluster
        genre_means = cluster_countries.drop(columns=['cluster']).mean().sort_values(ascending=False)
        print(f"Top genres: {', '.join(genre_means.head(3).index.tolist())}")
    
    # Gap analysis: compare each cluster to global average
    global_avg = matrix_pct.drop(columns=['cluster']).mean()
    
    print("\n" + "=" * 60)
    print("CONTENT GAPS (Underserved genres by cluster)")
    print("=" * 60)
    
    gaps = []
    for c in sorted(matrix_pct['cluster'].unique()):
        cluster_avg = matrix_pct[matrix_pct['cluster'] == c].drop(columns=['cluster']).mean()
        diff = global_avg - cluster_avg
        # Positive diff = global has more of this genre than this cluster
        top_gaps = diff.sort_values(ascending=False).head(3)
        
        countries = matrix_pct[matrix_pct['cluster'] == c].index.tolist()[:5]
        
        for genre, gap_size in top_gaps.items():
            if gap_size > 1:  # Only meaningful gaps
                gaps.append({
                    'cluster': c,
                    'countries': ', '.join(countries),
                    'underserved_genre': genre,
                    'gap_percentage': round(gap_size, 1)
                })
                print(f"Cluster {c} ({', '.join(countries[:3])}...): Underserved in {genre} by {gap_size:.1f}%")
    
    conn.close()
    return matrix_pct, gaps

if __name__ == '__main__':
    matrix, gaps = run_analysis()