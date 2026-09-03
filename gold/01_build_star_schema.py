# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# Databricks notebook source
# Gold Layer Star Schema (PLACEHOLDER)
# TODO: Implement Gold star schema

dbutils.widgets.text("catalog_name", "workspace")
dbutils.widgets.text("schema_name", "ecommerce_project")

catalog = dbutils.widgets.get("catalog_name")
schema = dbutils.widgets.get("schema_name")

print(f"⚠️  Gold Layer - Placeholder Notebook")
print(f"   Catalog: {catalog}")
print(f"   Schema: {schema}")
print(f"   TODO: Implement Gold star schema")