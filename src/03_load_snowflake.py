"""
Snowflake Loader
Loads hospitality transaction data into Snowflake and creates
analytical views and a Snowflake Task (scheduled query).

Prerequisites:
    pip install snowflake-connector-python pandas

Snowflake free trial setup:
    1. snowflake.com → Start for free (30-day trial, no credit card)
    2. Note your: account identifier, username, password
    3. Update the connection details below
"""

import snowflake.connector
import pandas as pd

# ── UPDATE THESE with your Snowflake details ──────────────────────────────────
ACCOUNT   = "your-account-identifier"   # e.g. abc12345.eu-west-1
USER      = "your-username"
PASSWORD  = "your-password"
WAREHOUSE = "COMPUTE_WH"               # default warehouse on free trial
DATABASE  = "HOSPITALITY_DB"
SCHEMA    = "RAW"
# ─────────────────────────────────────────────────────────────────────────────

def get_connection():
    return snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD,
        warehouse=WAREHOUSE
    )


def setup_schema(cur):
    """Create database, schemas and raw table."""
    print("Setting up Snowflake schema...")

    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    cur.execute(f"USE DATABASE {DATABASE}")
    cur.execute("CREATE SCHEMA IF NOT EXISTS RAW")
    cur.execute("CREATE SCHEMA IF NOT EXISTS ANALYTICS")
    cur.execute("USE SCHEMA RAW")

    cur.execute("""
    CREATE OR REPLACE TABLE RAW.TRANSACTIONS (
        TRANSACTION_ID    VARCHAR(12)    NOT NULL PRIMARY KEY,
        CUSTOMER_ID       VARCHAR(20)    NOT NULL,
        VENUE_ID          VARCHAR(10)    NOT NULL,
        VENUE_NAME        VARCHAR(100)   NOT NULL,
        VENUE_TYPE        VARCHAR(20)    NOT NULL,
        CITY              VARCHAR(50)    NOT NULL,
        REGION            VARCHAR(50)    NOT NULL,
        TRANSACTION_DATE  DATE           NOT NULL,
        TRANSACTION_TIME  TIME           NOT NULL,
        TRANSACTION_TS    TIMESTAMP_NTZ  NOT NULL,
        ITEM_NAME         VARCHAR(100)   NOT NULL,
        CATEGORY          VARCHAR(30)    NOT NULL,
        QUANTITY          NUMBER(3,0)    NOT NULL,
        UNIT_PRICE        NUMBER(8,2)    NOT NULL,
        GROSS_AMOUNT      NUMBER(8,2)    NOT NULL,
        DISCOUNT_PCT      NUMBER(3,0)    NOT NULL DEFAULT 0,
        DISCOUNT_AMOUNT   NUMBER(8,2)    NOT NULL DEFAULT 0,
        NET_AMOUNT        NUMBER(8,2)    NOT NULL,
        PAYMENT_METHOD    VARCHAR(20)    NOT NULL,
        IS_WEEKEND        BOOLEAN        NOT NULL,
        DAY_OF_WEEK       VARCHAR(10)    NOT NULL,
        MONTH             VARCHAR(10)    NOT NULL,
        MONTH_NUM         NUMBER(2,0)    NOT NULL,
        LOADED_AT         TIMESTAMP_NTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP()
    )
    """)
    print("RAW.TRANSACTIONS table created.")


def load_data(cur):
    """Load CSV data into Snowflake using a named stage."""
    print("Loading data into Snowflake...")

    cur.execute("USE DATABASE HOSPITALITY_DB")
    cur.execute("USE SCHEMA RAW")

    # Create a named stage pointing to local file
    cur.execute("CREATE OR REPLACE STAGE hospitality_stage FILE_FORMAT = (TYPE = CSV FIELD_OPTIONALLY_ENCLOSED_BY = '\"' SKIP_HEADER = 1)")

    # Use Python connector to write directly (simpler than PUT for local dev)
    df = pd.read_csv("data/hospitality_transactions.csv")
    df["is_weekend"] = df["is_weekend"].astype(bool)

    load_cols = [
        "transaction_id","customer_id","venue_id","venue_name","venue_type","city","region",
        "transaction_date","transaction_time","transaction_ts","item_name",
        "category","quantity","unit_price","gross_amount","discount_pct",
        "discount_amount","net_amount","payment_method","is_weekend",
        "day_of_week","month","month_num"
    ]
    df = df[load_cols]

    from snowflake.connector.pandas_tools import write_pandas
    success, nchunks, nrows, _ = write_pandas(
        cur._connection, df, "TRANSACTIONS",
        database=DATABASE, schema="RAW", quote_identifiers=False
    )
    print(f"Loaded {nrows:,} rows in {nchunks} chunks. Success: {success}")


def create_analytics_views(cur):
    """Create analytical views in the ANALYTICS schema."""
    print("Creating analytics views...")

    cur.execute("USE DATABASE HOSPITALITY_DB")
    cur.execute("USE SCHEMA ANALYTICS")

    # View 1 — Daily revenue summary
    cur.execute("""
    CREATE OR REPLACE VIEW ANALYTICS.VW_DAILY_REVENUE AS
    SELECT
        TRANSACTION_DATE,
        VENUE_ID,
        VENUE_NAME,
        VENUE_TYPE,
        CITY,
        REGION,
        COUNT(*)                    AS TRANSACTION_COUNT,
        SUM(QUANTITY)               AS ITEMS_SOLD,
        SUM(GROSS_AMOUNT)           AS GROSS_REVENUE,
        SUM(DISCOUNT_AMOUNT)        AS TOTAL_DISCOUNTS,
        SUM(NET_AMOUNT)             AS NET_REVENUE,
        AVG(NET_AMOUNT)             AS AVG_TRANSACTION_VALUE,
        -- Weekend vs weekday split
        SUM(CASE WHEN IS_WEEKEND THEN NET_AMOUNT ELSE 0 END)  AS WEEKEND_REVENUE,
        SUM(CASE WHEN NOT IS_WEEKEND THEN NET_AMOUNT ELSE 0 END) AS WEEKDAY_REVENUE
    FROM RAW.TRANSACTIONS
    GROUP BY 1,2,3,4,5,6
    """)

    # View 2 — Top items with Snowflake QUALIFY (Snowflake-specific feature)
    cur.execute("""
    CREATE OR REPLACE VIEW ANALYTICS.VW_TOP_ITEMS AS
    SELECT
        VENUE_TYPE,
        CATEGORY,
        ITEM_NAME,
        COUNT(*)            AS TIMES_ORDERED,
        SUM(QUANTITY)       AS TOTAL_QUANTITY_SOLD,
        SUM(NET_AMOUNT)     AS TOTAL_REVENUE,
        AVG(UNIT_PRICE)     AS AVG_UNIT_PRICE,
        RANK() OVER (PARTITION BY VENUE_TYPE ORDER BY SUM(NET_AMOUNT) DESC) AS REVENUE_RANK
    FROM RAW.TRANSACTIONS
    GROUP BY VENUE_TYPE, CATEGORY, ITEM_NAME
    QUALIFY RANK() OVER (PARTITION BY VENUE_TYPE ORDER BY SUM(NET_AMOUNT) DESC) <= 10
    """)

    # View 3 — Monthly trend with MoM growth
    cur.execute("""
    CREATE OR REPLACE VIEW ANALYTICS.VW_MONTHLY_TREND AS
    SELECT
        MONTH_NUM,
        MONTH,
        VENUE_TYPE,
        COUNT(*)                AS TRANSACTIONS,
        SUM(NET_AMOUNT)         AS NET_REVENUE,
        SUM(DISCOUNT_AMOUNT)    AS DISCOUNTS_GIVEN,
        AVG(NET_AMOUNT)         AS AVG_BASKET,
        LAG(SUM(NET_AMOUNT)) OVER (
            PARTITION BY VENUE_TYPE ORDER BY MONTH_NUM
        )                       AS PREV_MONTH_REVENUE,
        ROUND(
            DIV0(
                SUM(NET_AMOUNT) - LAG(SUM(NET_AMOUNT)) OVER (PARTITION BY VENUE_TYPE ORDER BY MONTH_NUM),
                LAG(SUM(NET_AMOUNT)) OVER (PARTITION BY VENUE_TYPE ORDER BY MONTH_NUM)
            ) * 100, 1
        )                       AS MOM_GROWTH_PCT
    FROM RAW.TRANSACTIONS
    GROUP BY MONTH_NUM, MONTH, VENUE_TYPE
    ORDER BY VENUE_TYPE, MONTH_NUM
    """)

    print("Analytics views created.")


def create_snowflake_task(cur):
    """
    Create a Snowflake Task — Snowflake's built-in scheduler.
    This runs a data quality check every day at 6am UTC.
    Demonstrates Snowflake-native orchestration features.
    """
    print("Creating Snowflake Task...")

    cur.execute("USE DATABASE HOSPITALITY_DB")
    cur.execute("USE SCHEMA RAW")

    # Create a results table for the task to write into
    cur.execute("""
    CREATE TABLE IF NOT EXISTS RAW.DATA_QUALITY_LOG (
        CHECK_TIMESTAMP   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        total_rows        NUMBER,
        null_amounts      NUMBER,
        duplicate_ids     NUMBER,
        negative_amounts  NUMBER,
        check_status      VARCHAR(10)
    )
    """)

    # Create the scheduled task
    cur.execute("""
    CREATE OR REPLACE TASK RAW.DAILY_DATA_QUALITY_CHECK
        WAREHOUSE = COMPUTE_WH
        SCHEDULE  = 'USING CRON 0 6 * * * UTC'
    AS
    INSERT INTO RAW.DATA_QUALITY_LOG (
        total_rows, null_amounts, duplicate_ids, negative_amounts, check_status
    )
    SELECT
        COUNT(*)                                            AS total_rows,
        SUM(CASE WHEN NET_AMOUNT IS NULL THEN 1 ELSE 0 END) AS null_amounts,
        COUNT(*) - COUNT(DISTINCT TRANSACTION_ID)           AS duplicate_ids,
        SUM(CASE WHEN NET_AMOUNT < 0 THEN 1 ELSE 0 END)    AS negative_amounts,
        CASE
            WHEN SUM(CASE WHEN NET_AMOUNT IS NULL THEN 1 ELSE 0 END) = 0
             AND COUNT(*) - COUNT(DISTINCT TRANSACTION_ID) = 0
             AND SUM(CASE WHEN NET_AMOUNT < 0 THEN 1 ELSE 0 END) = 0
            THEN 'PASSED'
            ELSE 'FAILED'
        END                                                 AS check_status
    FROM RAW.TRANSACTIONS
    """)

    # Note: tasks start suspended on free trial — resume manually if needed
    # cur.execute("ALTER TASK RAW.DAILY_DATA_QUALITY_CHECK RESUME")
    print("Task created (suspended by default on free trial).")
    print("To activate: ALTER TASK RAW.DAILY_DATA_QUALITY_CHECK RESUME")


if __name__ == "__main__":
    conn = get_connection()
    cur  = conn.cursor()

    try:
        setup_schema(cur)
        load_data(cur)
        create_analytics_views(cur)
        create_snowflake_task(cur)
    finally:
        cur.close()
        conn.close()

    print("\nAll done. Test queries:")
    print("  SELECT * FROM HOSPITALITY_DB.ANALYTICS.VW_DAILY_REVENUE LIMIT 10;")
    print("  SELECT * FROM HOSPITALITY_DB.ANALYTICS.VW_TOP_ITEMS;")
    print("  SELECT * FROM HOSPITALITY_DB.ANALYTICS.VW_MONTHLY_TREND;")
