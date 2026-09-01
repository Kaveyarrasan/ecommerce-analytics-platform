# test_gold_metrics.py - Business metric and star schema tests for Gold layer
"""
Tests for the Gold layer of the E-Commerce Analytics Platform.
Validates star schema integrity, business metric calculations, and data quality.
"""

import pytest
from conftest import (
    gold_table, full_table_name, count_rows, count_nulls,
    table_exists, GOLD_TABLES
)

# ============================================
# STAR SCHEMA INTEGRITY TESTS
# ============================================

class TestStarSchemaIntegrity:
    """Verify the star schema structure and foreign key relationships."""

    @pytest.mark.parametrize("table_name", GOLD_TABLES)
    def test_gold_table_exists(self, table_name):
        """Each Gold table should exist in the catalog."""
        assert table_exists(full_table_name(table_name)), \
            f"Table {table_name} does not exist"

    @pytest.mark.parametrize("table_name", GOLD_TABLES)
    def test_gold_table_has_rows(self, table_name):
        """Each Gold table should have at least 1 row."""
        count = count_rows(full_table_name(table_name))
        assert count > 0, f"Table {table_name} has 0 rows"

    def test_fact_orders_grain(self):
        """gold_fact_orders should have one row per order item (112,650 rows)."""
        count = count_rows(gold_table('fact_orders'))
        assert count == 112650, f"Expected 112,650 fact rows, got {count:,}"

    def test_fact_has_date_fk(self):
        """Every fact row should have a date_id that exists in dim_date."""
        orphan_dates = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {gold_table('fact_orders')} f
            LEFT JOIN {gold_table('dim_date')} d ON f.date_id = d.date_id
            WHERE d.date_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_dates == 0, f"Found {orphan_dates} fact rows with no matching date"

    def test_fact_has_customer_fk(self):
        """Every fact row should have a customer_id that exists in dim_customers."""
        orphan_customers = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {gold_table('fact_orders')} f
            LEFT JOIN {gold_table('dim_customers')} c ON f.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_customers == 0, f"Found {orphan_customers} fact rows with no matching customer"

    def test_fact_has_product_fk(self):
        """Every fact row should have a product_id that exists in dim_products."""
        orphan_products = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {gold_table('fact_orders')} f
            LEFT JOIN {gold_table('dim_products')} p ON f.product_id = p.product_id
            WHERE p.product_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_products == 0, f"Found {orphan_products} fact rows with no matching product"

    def test_fact_has_seller_fk(self):
        """Every fact row should have a seller_id that exists in dim_sellers."""
        orphan_sellers = spark.sql(f"""
            SELECT COUNT(*) as cnt
            FROM {gold_table('fact_orders')} f
            LEFT JOIN {gold_table('dim_sellers')} s ON f.seller_id = s.seller_id
            WHERE s.seller_id IS NULL
        """).collect()[0]["cnt"]
        assert orphan_sellers == 0, f"Found {orphan_sellers} fact rows with no matching seller"

# ============================================
# BUSINESS METRIC TESTS
# ============================================

class TestBusinessMetrics:
    """Verify calculated business metrics are valid."""

    def test_total_revenue_positive(self):
        """Total revenue should be greater than R$ 10 million."""
        revenue = spark.sql(f"""
            SELECT SUM(total_item_value) as revenue
            FROM {gold_table('fact_orders')}
        """).collect()[0]["revenue"]
        assert revenue > 10000000, f"Total revenue R$ {revenue:,.2f} is below expected R$ 10M"
        assert revenue < 20000000, f"Total revenue R$ {revenue:,.2f} seems too high"

    def test_average_order_value_positive(self):
        """Average order value should be between R$ 100 and R$ 300."""
        aov = spark.sql(f"""
            SELECT AVG(order_total) as avg_val
            FROM (
                SELECT order_id, SUM(total_item_value) as order_total
                FROM {gold_table('fact_orders')}
                GROUP BY order_id
            )
        """).collect()[0]["avg_val"]
        assert 100 < aov < 300, f"Average order value R$ {aov:,.2f} is outside expected range"

    def test_review_score_in_valid_range(self):
        """Average review score should be between 1 and 5."""
        avg_score = spark.sql(f"""
            SELECT AVG(review_score) as avg_score
            FROM {gold_table('fact_orders')}
            WHERE review_score IS NOT NULL
        """).collect()[0]["avg_score"]
        assert 1.0 <= avg_score <= 5.0, \
            f"Average review score {avg_score:.2f} is outside valid range [1, 5]"

    def test_delivery_days_positive(self):
        """Average delivery time should be positive and reasonable (< 60 days)."""
        avg_delivery = spark.sql(f"""
            SELECT AVG(delivery_days) as avg_days
            FROM {gold_table('fact_orders')}
            WHERE delivery_days IS NOT NULL AND delivery_days > 0
        """).collect()[0]["avg_days"]
        assert 0 < avg_delivery < 60, \
            f"Average delivery time {avg_delivery:.1f} days is outside expected range"

    def test_delivered_orders_ratio(self):
        """More than 90% of orders should be delivered."""
        total = count_rows(gold_table('fact_orders'))
        delivered = spark.sql(f"""
            SELECT COUNT(*) as cnt 
            FROM {gold_table('fact_orders')} 
            WHERE is_delivered = true
        """).collect()[0]["cnt"]
        delivery_rate = delivered / total
        assert delivery_rate > 0.90, \
            f"Delivery rate {delivery_rate:.1%} is below expected 90%"

# ============================================
# DATA QUALITY TESTS
# ============================================

class TestGoldDataQuality:
    """Verify data quality in the Gold layer."""

    def test_no_null_order_id_in_fact(self):
        """gold_fact_orders.order_id should never be NULL."""
        nulls = count_nulls(gold_table('fact_orders'), 'order_id')
        assert nulls == 0, f"Found {nulls} NULL order_id values in fact table"

    def test_no_null_price_in_fact(self):
        """gold_fact_orders.price should never be NULL."""
        nulls = count_nulls(gold_table('fact_orders'), 'price')
        assert nulls == 0, f"Found {nulls} NULL price values in fact table"

    def test_no_null_total_item_value(self):
        """gold_fact_orders.total_item_value should never be NULL."""
        nulls = count_nulls(gold_table('fact_orders'), 'total_item_value')
        assert nulls == 0, f"Found {nulls} NULL total_item_value in fact table"

    def test_price_is_positive(self):
        """All prices in fact table should be positive."""
        negative_prices = spark.sql(f"""
            SELECT COUNT(*) as cnt 
            FROM {gold_table('fact_orders')} 
            WHERE price <= 0
        """).collect()[0]["cnt"]
        assert negative_prices == 0, f"Found {negative_prices} rows with non-positive price"

    def test_dim_date_has_valid_range(self):
        """dim_date should span from 2016 to 2018 (Kaggle dataset period)."""
        min_date = spark.sql(f"""
            SELECT MIN(year) as min_y FROM {gold_table('dim_date')}
        """).collect()[0]["min_y"]
        max_date = spark.sql(f"""
            SELECT MAX(year) as max_y FROM {gold_table('dim_date')}
        """).collect()[0]["max_y"]
        assert min_date <= 2016, f"Earliest year {min_date} is later than expected"
        assert max_date >= 2018, f"Latest year {max_date} is earlier than expected"

    def test_dim_products_has_categories(self):
        """dim_products should have non-null English category names for most products."""
        null_categories = count_nulls(gold_table('dim_products'), 'product_category_name_english')
        total_products = count_rows(gold_table('dim_products'))
        null_rate = null_categories / total_products
        assert null_rate < 0.05, \
            f"{null_rate:.1%} products have NULL category (expected < 5%)"

# ============================================
# DIMENSION CARDINALITY TESTS
# ============================================

class TestDimensionCardinality:
    """Verify dimension table cardinality matches expectations."""

    def test_dim_customers_count(self):
        """dim_customers should have 99,441 rows (same as source)."""
        count = count_rows(gold_table('dim_customers'))
        assert count == 99441, f"Expected 99,441 customers, got {count:,}"

    def test_dim_products_count(self):
        """dim_products should have 32,951 rows (same as source)."""
        count = count_rows(gold_table('dim_products'))
        assert count == 32951, f"Expected 32,951 products, got {count:,}"

    def test_dim_sellers_count(self):
        """dim_sellers should have 3,095 rows (same as source)."""
        count = count_rows(gold_table('dim_sellers'))
        assert count == 3095, f"Expected 3,095 sellers, got {count:,}"

    def test_dim_date_count(self):
        """dim_date should have between 500 and 1000 unique dates."""
        count = count_rows(gold_table('dim_date'))
        assert 500 < count < 1000, f"Expected 500-1000 dates, got {count:,}"