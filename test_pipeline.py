# Test each pipeline step independently
import netflix_pipeline_dag as pipeline

print("Step 1: Loading raw data...")
pipeline.load_raw_data()

print("\nStep 2: Transforming data...")
pipeline.transform_data()

print("\nStep 3: Creating analytics views...")
pipeline.create_analytics_views()

print("\nStep 4: Validating pipeline...")
pipeline.validate_pipeline()

print("\nPipeline test complete!")