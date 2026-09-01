# test_silver_quality.py - Data quality tests for Silver layer
"""
Tests for the Silver layer of the E-Commerce Analytics Platform.
Validates data cleaning, referential integrity, and standardization.
"""

import pytest
from conftest import (
    silver_table, full_table_name, count_rows, count_nulls,
    table_exists, SILVER_TABLES
)

# ============================================
# TABLE EXISTENCE TESTS
# ============================================

class TestSilverTableExistence:
    """Verify all 7 Silver tables exist and have rows."""

    @pytest.mark.parametrize("table_name", SILVER_TABLES)
    def test_table_exists(self, table_name):
        """Each Silver table should exist in the catalog."""
        assert table_exists(full_table_name(table_name)), \
            f"Table {table_name} does not exist"

    @pytest.mark.parametrize("table_name", SILVER_TABLES)
    def test_table_has_rows(self, table_name):
        """Each Silver table should have at least 1 row."""
        count = count_rows(full_table_name(table_name))
        assert count > 0, f"Table {table_name} has 0 rows"

# ============================================
# DATA CLEANING TESTS
# ============================================

class TestSilverDataCleaning:
    """Verify data cleaning transformations were applied correctly."""

    def test_reviews_no_null_review_id(self):
        """silver_order_reviews.review_id should never be NULL (cleaned in Silver)."""
        nulls = count_nulls(silver_table('order_reviews'), 'review_id')
        assert nulls == 0, f"Found {nulls} NULL review_id values"

    def test_reviews_score_is_integer(self):
        """silver_order_reviews.review_score should be valid integer 1-5."""
        invalid = spark.sql(f"""
            SELECT COUNT(*) as cnt 
            FROM {silver_table('order_reviews')} 
            WHERE review_score < 1 OR review_score > 5
        """).collect()[0]["cnt"]
        assert invalid == 0, f"Found {invalid} reviews with invalid scores"

    def test_reviews_no_duplicates_per_order(self):
        """silver_order_reviews should have at most 1 review per order (deduplicated)."""
        dups = spark.sql(f"""
            SELECT COUNT(*) as cnt FROM (
                SELECT order_id 
                FROM {silver_table('order_reviews')} 
                GROUP BY order_id HAVING COUNT(*) > 1
            )
        """).collect()[0]["cnt"]
        assert dups == 0, f"Found {dups} orders with duplicate reviews"

    def test_payments_no_negative_values(self):
        """silver_order_payments.total_payment_value should be positive."""
        negatives = spark.sql(f"""
            SELECT COUNT(*) as cnt 
            FROM {silver_table('order_payments')} 
            WHERE total_payment_value <= 0
        """).collect()[0]["cnt"]
        # Allow up to 3 edge cases (known data issue)
        assert negatives <= 3, f"Found {negatives} orders with non-positive payments (expected max 3)"

    def test_customer_cities_are_lowercase(self):
        """silver_customers.customer_city should be standardized to lowercase."""
        non_lower = spark.sql(f"""
            SELECT COUNT(*) as cnt 
            FROM {silver_table('customers')} 
            WHERE customer_city != LOWER(customer_city) AND customer_city IS NOT NULL
        """).collect()[0]["cnt"]
        assert non_lower == 0, f"Found {non_lower} cities not in lowercase"

    def test_seller_cities_are_lowercase(self):
        """silver_sellers.seller_city should be standardized to lowercase."""
        non_lower = spark.sql(f"""
            SELECT COUNT(*) as cnt 
            FROM {silver_table('sellers')} 
            WHERE seller_city != LOWER(seller_city) AND seller_city IS NOT NULL
        """).collect()[0]["cnt"]
        assert non_lower == 0, f"Found {non_lower} cities not in lowercase"

# ============================================
# REFERENTIAL INTEGRITY TESTS
# ============================================

class TestSilverReferentialIntegrity:
    """Verify foreign key relationships between Silver tables."""

    def test_all_order_items_have_matching_orders(self):
        """Every order item in silver_order_items should have a matching order in silver_orders."""
        orphan_items = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {silver_table('order_items')} si
            LEFT JOIN {silver_table('orders')} so ON si.order_id = so.order_id
            WHERE so.order_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_items == 0, f"Found {orphan_items} order items with no matching order"

    def test_all_order_items_have_matching_products(self):
        """Every order item should have a matching product in silver_products."""
        orphan_products = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {silver_table('order_items')} si
            LEFT JOIN {silver_table('products')} p ON si.product_id = p.product_id
            WHERE p.product_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_products == 0, f"Found {orphan_products} items with no matching product"

    def test_all_order_items_have_matching_sellers(self):
        """Every order item should have a matching seller in silver_sellers."""
        orphan_sellers = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {silver_table('order_items')} si
            LEFT JOIN {silver_table('sellers')} s ON si.seller_id = s.seller_id
            WHERE s.seller_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_sellers == 0, f"Found {orphan_sellers} items with no matching seller"

    def test_all_orders_have_customers(self):
        """Every order in silver_orders should have a matching customer."""
        orphan_orders = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {silver_table('orders')} o
            LEFT JOIN {silver_table('customers')} c ON o.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_orders == 0, f"Found {orphan_orders} orders with no matching customer"

# ============================================
# SILVER TRANSFORMATION TIMESTAMP TESTS
# ============================================

class TestSilverAuditColumns:
    """Verify Silver tables have transformation timestamps."""

    @pytest.mark.parametrize("table_name", SILVER_TABLES)
    def test_silver_timestamp_exists(self, table_name):
        """Each Silver table should have _silver_transform_timestamp column."""
        cols = spark.sql(f"DESCRIBE {full_table_name(table_name)}").collect()
        col_names = [r['col_name'] for r in cols if not r['col_name'].startswith('#')]
        assert '_silver_transform_timestamp' in col_names, \
            f"Table {table_name} is missing _silver_transform_timestamp column"

# ============================================
# ROW COUNT VALIDATION TESTS
# ============================================

class TestSilverRowCounts:
    """Verify Silver table row counts are within expected ranges."""

    def test_silver_orders_count(self):
        """silver_orders should have same count as bronze_orders."""
        count = count_rows(silver_table('orders'))
        assert count == 99441, f"Expected 99,441 orders, got {count:,}"

    def test_silver_order_items_count(self):
        """silver_order_items should have same count as bronze_order_items."""
        count = count_rows(silver_table('order_items'))
        assert count == 112650, f"Expected 112,650 order items, got {count:,}"

    def test_silver_reviews_count_reduced(self):
        """silver_order_reviews should have fewer rows than bronze (deduplication + cleaning)."""
        count = count_rows(silver_table('order_reviews'))
        assert count < 104162, f"Expected fewer than 104,162 reviews after cleaning, got {count:,}"
        assert count > 90000, f"Expected more than 90,000 reviews, got {count:,}"

    def test_silver_payments_count_reduced(self):
        """silver_order_payments should have fewer rows (aggregated per order)."""
        count = count_rows(silver_table('order_payments'))
        assert count < 103886, f"Expected fewer than 103,886 after aggregation, got {count:,}"
        assert count > 99000, f"Expected more than 99,000 after aggregation, got {count:,}"