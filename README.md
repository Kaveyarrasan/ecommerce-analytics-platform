# E-Commerce Analytics Platform

> **End-to-end data architecture project for practicing Senior Data Architect skills**
> Built on Databricks with Bronze → Silver → Gold medallion architecture

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      SOURCE DATA (Kaggle)                       │
│  9 CSV files: orders, items, payments, reviews, customers,     │
│  sellers, products, geolocation, category_translation          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ COPY INTO / Auto Loader
┌──────────────────────────────▼──────────────────────────────────┐
│                    BRONZE LAYER (Raw)                           │
│  Schema: workspace.ecommerce_project.bronze_*                  │
│  - Exact copy of source data                                   │
│  - Audit columns: _ingest_timestamp, _source_file             │
│  - Schema enforcement via Delta                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ Clean, deduplicate, validate
┌──────────────────────────────▼──────────────────────────────────┐
│                   SILVER LAYER (Cleansed)                       │
│  Schema: workspace.ecommerce_project.silver_*                  │
│  - Data quality checks (expectations)                          │
│  - Referential integrity enforced                              │
│  - Standardized formats and naming                             │
│  - SCD Type 1 (current state only)                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │ Aggregate, model for analytics
┌──────────────────────────────▼──────────────────────────────────┐
│                   GOLD LAYER (Business Metrics)                 │
│  Schema: workspace.ecommerce_project.gold_*                    │
│  - Star schema (fact + dimension tables)                      │
│  - Business metrics: daily sales, customer LTV, etc.           │
│  - Optimized for dashboards and reporting                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                  DELIVERY (Dashboards & APIs)                   │
│  - AI/BI Dashboards                                           │
│  - Cost monitoring via system tables                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture Decision Records (ADR)

### ADR-001: Medallion Architecture (Bronze → Silver → Gold)

**Context**: We need to process raw e-commerce data from 9 CSV files into business-ready analytics tables.

**Decision**: Use Databricks medallion architecture with three layers.

**Rationale**:
- Separation of concerns: raw → cleaned → business-ready
- Each layer has distinct quality requirements
- Enables incremental processing and reprocessing without re-ingesting raw data
- Industry-standard pattern for lakehouse architecture

**Trade-offs**:
- ✅ Pro: Clear data lineage, easier debugging
- ✅ Pro: Can reprocess any layer independently
- ❌ Con: More storage (3 copies of data)
- ❌ Con: More compute (3 passes)

---

### ADR-002: Batch Ingestion (COPY INTO) vs Streaming (Auto Loader)

**Context**: Bronze layer needs to load CSV files from volume.

**Decision**: Use COPY INTO for initial Bronze layer (batch).

**Rationale**:
- Dataset is static (Kaggle historical data, not real-time)
- Simpler to implement and debug
- Lower compute cost for one-time load
- Appropriate for learning and practice

**Trade-offs**:
- ✅ Pro: Simple, reliable, lower cost
- ✅ Pro: Easy to understand for learning
- ❌ Con: Not real-time (must re-run for new data)
- ❌ Con: Requires manual or scheduled execution

**Future Enhancement**: Convert to Auto Loader for streaming ingestion if new files arrive continuously.

---

### ADR-003: Star Schema for Gold Layer

**Context**: Gold layer needs dimensional model for analytics.

**Decision**: Use star schema with one fact table and multiple dimension tables.

**Data Model**:
```
                    ┌──────────────┐
                    │  dim_customers│
                    └──────┬───────┘
                           │
┌──────────────┐   ┌───────┴───────┐   ┌──────────────┐
│  dim_products│───│  fact_orders  │───│  dim_sellers  │
└──────────────┘   └───────┬───────┘   └──────────────┘
                           │
                    ┌──────┴───────┐
                    │   dim_date    │
                    └──────────────┘
```

**Rationale**:
- Star schema is simplest for analytics queries
- Faster join performance than snowflake
- Easy for business users to understand
- Industry standard for BI/reporting

**Fact Table**: `gold_fact_orders`
- Grain: One row per order item
- Measures: price, freight_value, payment_value, review_score
- Foreign keys: customer_id, product_id, seller_id, date_id

**Dimension Tables**:
- `gold_dim_customers`: customer_id, city, state, zip_code_prefix
- `gold_dim_products`: product_id, category_name, dimensions (length, height, width, weight)
- `gold_dim_sellers`: seller_id, city, state, zip_code_prefix
- `gold_dim_date`: date_id, day, month, year, quarter, day_of_week

---

### ADR-004: Orchestration - Lakeflow Jobs

**Context**: Need to orchestrate Bronze → Silver → Gold pipeline execution.

**Decision**: Use Lakeflow Jobs (not Pipelines) for this project.

**Rationale**:
- Batch processing (not streaming) aligns with Jobs
- Jobs can orchestrate multiple notebooks with dependencies
- More flexible for mixed task types (Python + SQL)
- Free Edition supports up to 5 concurrent tasks

**Trade-offs**:
- ✅ Pro: Flexible, supports multiple task types
- ✅ Pro: Good for batch processing
- ❌ Con: No automatic dependency detection (must define manually)
- ❌ Con: No built-in data quality expectations (must implement manually)

**Future Enhancement**: Consider Lakeflow Pipelines if converting to streaming or needing built-in expectations.

---

### ADR-005: DevOps - Git + DABs (CI/CD)

**Context**: Need version control and CI/CD for the project.

**Decision**: Use Databricks Git Folders + Declarative Automation Bundles (DABs).

**Rationale**:
- Git Folders: Native integration with GitHub for version control
- DABs: Databricks-native CI/CD (replaces Jenkins)
- pytest: Unit testing framework for data quality validation
- No Docker needed (serverless compute handles environment)

**Trade-offs**:
- ✅ Pro: Native Databricks integration
- ✅ Pro: No external CI/CD server needed
- ✅ Pro: YAML-based configuration (easy to maintain)
- ❌ Con: Learning curve for DABs syntax

---

## Data Quality Framework

### Bronze Layer - Validation Rules
| Table | Rule | Action |
|-------|------|--------|
| orders | order_id NOT NULL | Drop row |
| orders | order_status IN valid values | Drop row |
| customers | customer_id NOT NULL | Drop row |
| products | product_id NOT NULL | Drop row |

### Silver Layer - Quality Checks
| Check | Description | Test |
|-------|-------------|------|
| Completeness | All orders have items | COUNT(orphan_orders) = 0 |
| Uniqueness | No duplicate order_ids | COUNT(DISTINCT) = COUNT(*) |
| Referential | Every item has a product | LEFT JOIN check |
| Validity | Payment values > 0 | MIN(payment_value) > 0 |

---

## Project Structure

```
ecommerce-analytics-platform/
├── bronze/                    # Bronze layer notebooks
│   ├── 01_load_orders.py
│   ├── 02_load_order_items.py
│   └── ...
├── silver/                    # Silver layer notebooks
│   ├── 01_clean_orders.py
│   └── ...
├── gold/                      # Gold layer notebooks
│   ├── 01_fact_orders.py
│   └── ...
├── tests/                     # Unit tests (pytest)
│   ├── test_bronze_quality.py
│   └── ...
├── databricks.yml             # DAB CI/CD configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Unity Catalog Structure

```
workspace.ecommerce_project
├── raw_data/                  (Volume - stores Kaggle CSV files)
├── bronze_orders              (Table)
├── bronze_order_items         (Table)
├── bronze_order_payments      (Table)
├── bronze_order_reviews       (Table)
├── bronze_customers            (Table)
├── bronze_sellers             (Table)
├── bronze_products            (Table)
├── bronze_geolocation         (Table)
├── bronze_category_translation(Table)
├── silver_orders              (Table)
├── silver_order_items         (Table)
├── silver_customers           (Table)
├── gold_fact_orders           (Table)
├── gold_dim_customers         (Table)
├── gold_dim_products          (Table)
├── gold_dim_sellers           (Table)
└── gold_dim_date              (Table)
```

---

## Getting Started

1. Download dataset from Kaggle: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
2. Upload CSV files to volume: `/Volumes/workspace/ecommerce_project/raw_data/`
3. Run Bronze notebooks → Silver notebooks → Gold notebooks
4. Run tests: `pytest tests/ -v`
5. Deploy via DABs: `databricks bundle deploy --target dev`

---

## Key Metrics (Gold Layer)

| Metric | Description | Table |
|--------|-------------|-------|
| Daily Sales | Total revenue per day | gold_fact_orders |
| Customer LTV | Lifetime value per customer | gold_fact_orders + gold_dim_customers |
| Product Performance | Top selling products | gold_fact_orders + gold_dim_products |
| Order Fulfillment | Avg days from order to delivery | gold_fact_orders |
| Review Analysis | Average review score by category | gold_fact_orders + gold_dim_products |
