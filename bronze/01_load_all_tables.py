# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Bronze Layer - Overview
# MAGIC %md
# MAGIC
# MAGIC # Bronze Layer: Raw Data Ingestion
# MAGIC
# MAGIC **Purpose**: Load all 9 CSV files from Kaggle volume into Delta tables with minimal transformation.
# MAGIC
# MAGIC **Architecture Decision (ADR-002)**: Using COPY INTO for batch ingestion (not Auto Loader) because:
# MAGIC - Dataset is static (historical Kaggle data)
# MAGIC - Simpler to implement and debug
# MAGIC - Lower compute cost for one-time load
# MAGIC
# MAGIC **Bronze Layer Rules**:
# MAGIC 1. Preserve raw data as-is (no transformations except type casting)
# MAGIC 2. Add audit columns: `_ingest_timestamp`, `_source_file`
# MAGIC 3. Validate primary keys are NOT NULL
# MAGIC 4. Use Delta format for ACID compliance and time travel
# MAGIC 5. Table naming: `workspace.ecommerce_project.bronze_<table_name>`

# COMMAND ----------

# DBTITLE 1,Configuration
# ============================================
# CONFIGURATION
# ============================================

# Unity Catalog locations
CATALOG = "workspace"
SCHEMA = "ecommerce_project"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

# Table definitions: (csv_filename, bronze_table_name, primary_key)
TABLES = [
    ("olist_orders_dataset.csv", "bronze_orders", "order_id"),
    ("olist_order_items_dataset.csv", "bronze_order_items", "order_id"),
    ("olist_order_payments_dataset.csv", "bronze_order_payments", "order_id"),
    ("olist_order_reviews_dataset.csv", "bronze_order_reviews", "review_id"),
    ("olist_customers_dataset.csv", "bronze_customers", "customer_id"),
    ("olist_sellers_dataset.csv", "bronze_sellers", "seller_id"),
    ("olist_products_dataset.csv", "bronze_products", "product_id"),
    ("olist_geolocation_dataset.csv", "bronze_geolocation", "geolocation_zip_code_prefix"),
    ("product_category_name_translation.csv", "bronze_category_translation", "product_category_name"),
]

print(f"📊 Bronze Layer Configuration")
print(f"   Catalog: {CATALOG}")
print(f"   Schema: {SCHEMA}")
print(f"   Volume: {VOLUME_PATH}")
print(f"   Tables to load: {len(TABLES)}")

# COMMAND ----------

# DBTITLE 1,Load Function Definition
# ============================================
# BRONZE LOAD FUNCTION
# ============================================

from pyspark.sql.functions import current_timestamp, input_file_name, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

def load_csv_to_bronze(csv_filename, bronze_table_name, primary_key):
    """
    Load a CSV file from volume into a Bronze Delta table.
    
    Data Architect Notes:
    - Uses COPY INTO for idempotent loading (can re-run safely)
    - Adds audit columns for data lineage
    - Validates primary key is NOT NULL (data quality)
    - Overwrites existing Bronze table (full refresh for batch mode)
    
    Args:
        csv_filename: Name of CSV file in volume
        bronze_table_name: Target Bronze table name (without schema prefix)
        primary_key: Column name for primary key validation
    """
    full_table_name = f"{CATALOG}.{SCHEMA}.{bronze_table_name}"
    csv_path = f"{VOLUME_PATH}/{csv_filename}"
    
    print(f"\n{'='*60}")
    print(f"📥 Loading: {csv_filename} → {full_table_name}")
    print(f"{'='*60}")
    
    # Read CSV with schema inference
    df = (spark.read
          .option("header", "true")
          .option("inferSchema", "true")
          .csv(csv_path))
    
    # Add audit columns (Data Architect best practice: always track data lineage)
    df = (df
          .withColumn("_ingest_timestamp", current_timestamp())
          .withColumn("_source_file", lit(csv_filename)))
    
    # Write to Bronze Delta table (overwrite for batch mode)
    df.write.mode("overwrite").saveAsTable(full_table_name)
    
    # Data Quality Check: Validate primary key
    total_rows = spark.sql(f"SELECT COUNT(*) as cnt FROM {full_table_name}").collect()[0]["cnt"]
    null_pk_rows = spark.sql(f"SELECT COUNT(*) as cnt FROM {full_table_name} WHERE {primary_key} IS NULL").collect()[0]["cnt"]
    duplicate_pk_rows = spark.sql(f"SELECT COUNT(*) as cnt FROM (SELECT {primary_key} FROM {full_table_name} GROUP BY {primary_key} HAVING COUNT(*) > 1)").collect()[0]["cnt"]
    
    # Report quality metrics
    print(f"   ✅ Total rows loaded: {total_rows:,}")
    print(f"   {'✅' if null_pk_rows == 0 else '❌'} NULL primary keys ({primary_key}): {null_pk_rows:,}")
    print(f"   {'✅' if duplicate_pk_rows == 0 else '⚠️'} Duplicate primary keys: {duplicate_pk_rows:,}")
    
    return {"table": bronze_table_name, "rows": total_rows, "null_pk": null_pk_rows, "dup_pk": duplicate_pk_rows}

print("✅ Bronze load function defined")

# COMMAND ----------

# DBTITLE 1,Load All 9 Tables
# ============================================
# LOAD ALL 9 TABLES INTO BRONZE LAYER
# ============================================

results = []

for csv_filename, bronze_table, pk in TABLES:
    result = load_csv_to_bronze(csv_filename, bronze_table, pk)
    results.append(result)

print(f"\n{'='*60}")
print(f"📊 BRONZE LAYER LOADING COMPLETE")
print(f"{'='*60}")
for r in results:
    status = "✅" if r["null_pk"] == 0 else "❌"
    print(f"   {status} {r['table']}: {r['rows']:,} rows")

# COMMAND ----------

# DBTITLE 1,Data Quality Summary
# ============================================
# BRONZE DATA QUALITY SUMMARY
# ============================================

print(f"\n{'='*60}")
print(f"📋 BRONZE DATA QUALITY REPORT")
print(f"{'='*60}")

total_rows_all = sum(r["rows"] for r in results)
total_nulls = sum(r["null_pk"] for r in results)
total_dups = sum(r["dup_pk"] for r in results)

print(f"   Total tables loaded: {len(results)}")
print(f"   Total rows across all tables: {total_rows_all:,}")
print(f"   Total NULL primary keys: {total_nulls}")
print(f"   Total duplicate primary keys: {total_dups}")

if total_nulls == 0 and total_dups == 0:
    print(f"\n   ✅ BRONZE LAYER PASSED ALL DATA QUALITY CHECKS")
else:
    print(f"\n   ⚠️  BRONZE LAYER HAS DATA QUALITY ISSUES - REVIEW NEEDED")
    print(f"   See ADR-001 in README.md for data quality framework details")

# List all Bronze tables
print(f"\n{'='*60}")
print(f"📋 BRONZE TABLES CREATED:")
print(f"{'='*60}")
for r in results:
    print(f"   workspace.ecommerce_project.{r['table']}")

# COMMAND ----------

