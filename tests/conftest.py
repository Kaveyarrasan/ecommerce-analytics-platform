# conftest.py - Shared pytest fixtures and configuration
"""
Shared fixtures and configuration for E-Commerce Analytics Platform tests.
This file is automatically loaded by pytest before running any test.
"""

import pytest
from pyspark.sql import SparkSession

# Get the existing SparkSession (available in Databricks notebook context)
spark = SparkSession.builder.getOrCreate()

# ============================================
# CONSTANTS
# ============================================

CATALOG = "workspace"
SCHEMA = "ecommerce_project"

# Bronze table names
BRONZE_TABLES = [
    "bronze_orders",
    "bronze_order_items",
    "bronze_order_payments",
    "bronze_order_reviews",
    "bronze_customers",
    "bronze_sellers",
    "bronze_products",
    "bronze_geolocation",
    "bronze_category_translation",
]

# Silver table names
SILVER_TABLES = [
    "silver_orders",
    "silver_order_items",
    "silver_order_payments",
    "silver_order_reviews",
    "silver_customers",
    "silver_products",
    "silver_sellers",
]

# Gold table names
GOLD_TABLES = [
    "gold_dim_date",
    "gold_dim_customers",
    "gold_dim_products",
    "gold_dim_sellers",
    "gold_fact_orders",
]

# ============================================
# HELPER FUNCTIONS
# ============================================

def full_table_name(table_name: str) -> str:
    """Return the fully qualified table name."""
    return f"{CATALOG}.{SCHEMA}.{table_name}"

def bronze_table(name: str) -> str:
    """Return fully qualified Bronze table name."""
    return f"{CATALOG}.{SCHEMA}.bronze_{name}"

def silver_table(name: str) -> str:
    """Return fully qualified Silver table name."""
    return f"{CATALOG}.{SCHEMA}.silver_{name}"

def gold_table(name: str) -> str:
    """Return fully qualified Gold table name."""
    return f"{CATALOG}.{SCHEMA}.gold_{name}"

def count_rows(table_name: str) -> int:
    """Return row count for a fully qualified table."""
    return spark.sql(f"SELECT COUNT(*) as cnt FROM {table_name}").collect()[0]["cnt"]

def count_nulls(table_name: str, column: str) -> int:
    """Return count of NULL values in a specific column."""
    return spark.sql(f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {column} IS NULL").collect()[0]["cnt"]

def count_duplicates(table_name: str, column: str) -> int:
    """Return count of duplicate values for a specific column."""
    return spark.sql(f"""
        SELECT COUNT(*) as cnt FROM (
            SELECT {column} FROM {table_name} 
            GROUP BY {column} HAVING COUNT(*) > 1
        )
    """).collect()[0]["cnt"]

def table_exists(table_name: str) -> bool:
    """Check if a table exists in Unity Catalog."""
    try:
        spark.sql(f"DESCRIBE TABLE {table_name}")
        return True
    except Exception:
        return False

# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def catalog():
    """Return the catalog name."""
    return CATALOG

@pytest.fixture
def schema():
    """Return the schema name."""
    return SCHEMA