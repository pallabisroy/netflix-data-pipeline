from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime
from datetime import timedelta
import snowflake.connector

# Snowflake connection details
SSNOWFLAKE_CONFIG = {
    'user': 'YOUR_SNOWFLAKE_USERNAME',
    'password': 'YOUR_SNOWFLAKE_PASSWORD',
    'account': 'YOUR_SNOWFLAKE_ACCOUNT',
    'warehouse': 'NETFLIX_WH',
    'database': 'NETFLIX_DB'
}

def get_snowflake_connection():
    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)

def load_raw_data():
    """Load data from S3 into Snowflake RAW table"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute("USE SCHEMA RAW")
    cursor.execute("""
        COPY INTO RAW.NETFLIX_RAW
        FROM @RAW.S3_NETFLIX_STAGE
        FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1)
        ON_ERROR = 'CONTINUE'
    """)
    result = cursor.fetchone()
    print(f"Load result: {result}")
    cursor.close()
    conn.close()

def transform_data():
    """Transform raw data into clean analytics table"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE OR REPLACE TABLE ANALYTICS.NETFLIX_CLEAN AS
        SELECT
            show_id,
            type,
            title,
            COALESCE(director, 'Unknown') AS director,
            COALESCE("CAST", 'Unknown') AS cast_members,
            COALESCE(country, 'Unknown') AS country,
            TRY_TO_DATE(TRIM(date_added), 'MMMM DD, YYYY') AS date_added,
            YEAR(TRY_TO_DATE(TRIM(date_added), 'MMMM DD, YYYY')) AS year_added,
            MONTH(TRY_TO_DATE(TRIM(date_added), 'MMMM DD, YYYY')) AS month_added,
            release_year,
            COALESCE(rating, 'Not Rated') AS rating,
            duration,
            CASE
                WHEN type = 'Movie' THEN TRY_TO_NUMBER(REPLACE(duration, ' min', ''))
                ELSE TRY_TO_NUMBER(REPLACE(REPLACE(duration, ' Seasons', ''), ' Season', ''))
            END AS duration_num,
            listed_in,
            description
        FROM RAW.NETFLIX_RAW
    """)
    print("Transform complete")
    cursor.close()
    conn.close()

def create_analytics_views():
    """Create business-ready analytics views"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    views = [
        """CREATE OR REPLACE VIEW ANALYTICS.CONTENT_BY_YEAR AS
           SELECT year_added, type, COUNT(*) AS title_count
           FROM ANALYTICS.NETFLIX_CLEAN
           WHERE year_added IS NOT NULL
           GROUP BY year_added, type
           ORDER BY year_added""",
        
        """CREATE OR REPLACE VIEW ANALYTICS.TOP_COUNTRIES AS
           SELECT TRIM(value) AS country_name, COUNT(*) AS title_count
           FROM ANALYTICS.NETFLIX_CLEAN,
               LATERAL FLATTEN(input => SPLIT(country, ','))
           WHERE country != 'Unknown'
           GROUP BY country_name
           ORDER BY title_count DESC
           LIMIT 15""",
        
        """CREATE OR REPLACE VIEW ANALYTICS.TOP_GENRES AS
           SELECT TRIM(value) AS genre, COUNT(*) AS title_count
           FROM ANALYTICS.NETFLIX_CLEAN,
               LATERAL FLATTEN(input => SPLIT(listed_in, ','))
           GROUP BY genre
           ORDER BY title_count DESC
           LIMIT 15""",
        
        """CREATE OR REPLACE VIEW ANALYTICS.MONTHLY_ADDITIONS AS
           SELECT month_added, type, COUNT(*) AS title_count
           FROM ANALYTICS.NETFLIX_CLEAN
           WHERE month_added IS NOT NULL
           GROUP BY month_added, type
           ORDER BY month_added""",
        
        """CREATE OR REPLACE VIEW ANALYTICS.RATING_DISTRIBUTION AS
           SELECT rating, type, COUNT(*) AS title_count
           FROM ANALYTICS.NETFLIX_CLEAN
           GROUP BY rating, type
           ORDER BY title_count DESC"""
    ]
    
    for view_sql in views:
        cursor.execute(view_sql)
    
    print("All analytics views created")
    cursor.close()
    conn.close()

def validate_pipeline():
    """Validate data counts at each stage"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM RAW.NETFLIX_RAW")
    raw_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ANALYTICS.NETFLIX_CLEAN")
    clean_count = cursor.fetchone()[0]
    
    print(f"RAW table: {raw_count} rows")
    print(f"CLEAN table: {clean_count} rows")
    
    if raw_count == clean_count:
        print("VALIDATION PASSED: Row counts match")
    else:
        print(f"VALIDATION WARNING: Row count mismatch ({raw_count} vs {clean_count})")
    
    cursor.close()
    conn.close()

# DAG definition
default_args = {
    'owner': 'pallabi',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'netflix_data_pipeline',
    default_args=default_args,
    description='ETL pipeline: S3 -> Snowflake RAW -> Analytics',
    schedule='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['netflix', 'etl', 'snowflake']
)

# Task definitions
task_load = PythonOperator(
    task_id='load_raw_data',
    python_callable=load_raw_data,
    dag=dag
)

task_transform = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag
)

task_views = PythonOperator(
    task_id='create_analytics_views',
    python_callable=create_analytics_views,
    dag=dag
)

task_validate = PythonOperator(
    task_id='validate_pipeline',
    python_callable=validate_pipeline,
    dag=dag
)

# Pipeline order
task_load >> task_transform >> task_views >> task_validate