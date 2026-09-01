# test_bronze_quality.py - Data quality tests for Bronze layer
"""
Tests for the Bronze layer of the E-Commerce Analytics Platform.
Validates that raw data was loaded correctly with audit columns and no NULL primary keys.
"""

import pytest
from conftest import (
    bronze_table, full_table_name, count_rows, count_nulls,
    count_duplicates, table_exists, BRONZE_TABLES
)

# ============================================
# TABLE EXISTENCE TESTS
# ============================================

class TestBronzeTableExistence:
    """Verify all 9 Bronze tables exist in Unity Catalog."""

    @pytest.mark.parametrize("table_name", BRONZE_TABLES)
    def test_table_exists(self, table_name):
        """Each Bronze table should exist in the catalog."""
        assert table_exists(full_table_name(table_name)), \
            f"Table {table_name} does not exist"

    @pytest.mark.parametrize("table_name", BRONZE_TABLES)
    def test_table_has_rows(self, table_name):
        """Each Bronze table should have at least 1 row."""
        count = count_rows(full_table_name(table_name))
        assert count > 0, f"Table {table_name} has 0 rows"

# ============================================
# PRIMARY KEY TESTS
# ============================================

class TestBronzePrimaryKeys:
    """Verify primary keys are NOT NULL in Bronze tables."""

    def test_orders_no_null_order_id(self):
        """bronze_orders.order_id should never be NULL."""
        nulls = count_nulls(bronze_table('orders'), 'order_id')
        assert nulls == 0, f"Found {nulls} NULL order_id values"

    def test_customers_no_null_customer_id(self):
        """bronze_customers.customer_id should never be NULL."""
        nulls = count_nulls(bronze_table('customers'), 'customer_id')
        assert nulls == 0, f"Found {nulls} NULL customer_id values"

    def test_products_no_null_product_id(self):
        """bronze_products.product_id should never be NULL."""
        nulls = count_nulls(bronze_table('products'), 'product_id')
        assert nulls == 0, f"Found {nulls} NULL product_id values"

    def test_sellers_no_null_seller_id(self):
        """bronze_sellers.seller_id should never be NULL."""
        nulls = count_nulls(bronze_table('sellers'), 'seller_id')
        assert nulls == 0, f"Found {nulls} NULL seller_id values"

# ============================================
# AUDIT COLUMN TESTS
# ============================================

class TestBronzeAuditColumns:
    """Verify audit columns exist in all Bronze tables."""

    AUDIT_COLUMNS = ['_ingest_timestamp', '_source_file']

    @pytest.mark.parametrize("table_name", BRONZE_TABLES)
    @pytest.mark.parametrize("column", ['_ingest_timestamp', '_source_file'])
    def test_audit_column_exists(self, table_name, column):
        """Each Bronze table should have audit columns for data lineage."""
        cols = spark.sql(f"DESCRIBE {full_table_name(table_name)}").collect()
        col_names = [r['col_name'] for r in cols if not r['col_name'].startswith('#')]
        assert column in col_names, \
            f"Table {table_name} is missing audit column: {column}"

# ============================================
# ROW COUNT TESTS (Expected Values)
# ============================================

class TestBronzeRowCounts:
    """Verify Bronze table row counts match expected values from Kaggle dataset."""

    EXPECTED_COUNTS = {
        'bronze_orders': 99441,
        'bronze_order_items': 112650,
        'bronze_order_payments': 103886,
        'bronze_order_reviews': 104162,
        'bronze_customers': 99441,
        'bronze_sellers': 3095,
        'bronze_products': 32951,
        'bronze_geolocation': 1000163,
        'bronze_category_translation': 71,
    }

    @pytest.mark.parametrize("table_name,expected", list(EXPECTED_COUNTS.items()))
    def test_row_count(self, table_name, expected):
        """Each Bronze table should have the expected number of rows."""
        actual = count_rows(full_table_name(table_name))
        assert actual == expected, \
            f"{table_name}: expected {expected:,} rows, got {actual:,}"

# ============================================
# DATA TYPE TESTS
# ============================================

class TestBronzeDataTypes:
    """Verify key columns have correct data types."""

    def test_orders_timestamp_type(self):
        """bronze_orders.order_purchase_timestamp should be TIMESTAMP."""
        schema = spark.sql(f"DESCRIBE {bronze_table('orders')}").collect()
        col_type = {r['col_name']: r['data_type'] for r in schema if not r['col_name'].startswith('#')}
        assert 'timestamp' in col_type.get('order_purchase_timestamp', '').lower(), \
            f"order_purchase_timestamp type is {col_type.get('order_purchase_timestamp')}, expected TIMESTAMP"

    def test_order_items_price_type(self):
        """bronze_order_items.price should be DOUBLE."""
        schema = spark.sql(f"DESCRIBE {bronze_table('order_items')}").collect()
        col_type = {r['col_name']: r['data_type'] for r in schema if not r['col_name'].startswith('#')}
        assert 'double' in col_type.get('price', '').lower(), \
            f"price type is {col_type.get('price')}, expected DOUBLE"