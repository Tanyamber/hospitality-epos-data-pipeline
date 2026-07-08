"""
Azure SQL Loader
Loads hospitality transaction data into Azure SQL Database.

Prerequisites:
    pip install pyodbc pandas sqlalchemy

Azure SQL free tier setup:
    1. portal.azure.com → Create a resource → SQL Database
    2. Choose "Free offer" (250GB, always free)
    3. Server: create new, note your server name
    4. Authentication: SQL authentication, set admin login/password
    5. Allow your IP in the firewall settings
    6. Update the connection string below
"""

import pandas as pd
from sqlalchemy import create_engine, text
import urllib
import configparser
import os

# ── READ CONFIG FROM YOUR SECURE INI FILE ────────────────────────────────────
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../config/config.ini'))

SERVER   = config['azure_sql']['server']
DATABASE = config['azure_sql']['database']
USERNAME = config['azure_sql']['username']
PASSWORD = config['azure_sql']['password']

# ─────────────────────────────────────────────────────────────────────────────

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID={USERNAME};PWD={PASSWORD};"
    f"Encrypt=yes;TrustServerCertificate=yes;"
    f"Login Timeout=60;"    
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# ── Create table ──────────────────────────────────────────────────────────────

CREATE_TABLE = """
IF NOT EXISTS (
    SELECT * FROM sysobjects WHERE name='transactions' AND xtype='U'
)
CREATE TABLE dbo.transactions (
    transaction_id    VARCHAR(12)    NOT NULL PRIMARY KEY,
    venue_id          VARCHAR(10)    NOT NULL,
    venue_name        NVARCHAR(100)  NOT NULL,
    venue_type        VARCHAR(20)    NOT NULL,
    city              VARCHAR(50)    NOT NULL,
    region            VARCHAR(50)    NOT NULL,
    transaction_date  DATE           NOT NULL,
    transaction_time  TIME           NOT NULL,
    transaction_ts    DATETIME2      NOT NULL,
    item_name         NVARCHAR(100)  NOT NULL,
    category          VARCHAR(30)    NOT NULL,
    quantity          TINYINT        NOT NULL,
    unit_price        DECIMAL(8,2)   NOT NULL,
    gross_amount      DECIMAL(8,2)   NOT NULL,
    discount_pct      TINYINT        NOT NULL DEFAULT 0,
    discount_amount   DECIMAL(8,2)   NOT NULL DEFAULT 0,
    net_amount        DECIMAL(8,2)   NOT NULL,
    payment_method    VARCHAR(20)    NOT NULL,
    is_weekend        BIT            NOT NULL,
    day_of_week       VARCHAR(10)    NOT NULL,
    month             VARCHAR(10)    NOT NULL,
    month_num         TINYINT        NOT NULL,
    loaded_at         DATETIME2      NOT NULL DEFAULT GETUTCDATE()
);
"""

# ── Create views ──────────────────────────────────────────────────────────────

CREATE_VIEWS = [
"""
CREATE OR ALTER VIEW dbo.vw_daily_revenue AS
SELECT
    transaction_date,
    venue_id,
    venue_name,
    venue_type,
    city,
    region,
    COUNT(*)                    AS transaction_count,
    SUM(quantity)               AS items_sold,
    SUM(gross_amount)           AS gross_revenue,
    SUM(discount_amount)        AS total_discounts,
    SUM(net_amount)             AS net_revenue,
    AVG(net_amount)             AS avg_transaction_value
FROM dbo.transactions
GROUP BY
    transaction_date, venue_id, venue_name,
    venue_type, city, region;
""",
"""
CREATE OR ALTER VIEW dbo.vw_category_performance AS
SELECT
    venue_type,
    category,
    item_name,
    COUNT(*)                    AS times_ordered,
    SUM(quantity)               AS total_quantity,
    SUM(net_amount)             AS total_revenue,
    AVG(unit_price)             AS avg_price,
    RANK() OVER (
        PARTITION BY venue_type
        ORDER BY SUM(net_amount) DESC
    )                           AS revenue_rank_in_venue_type
FROM dbo.transactions
GROUP BY venue_type, category, item_name;
""",
"""
CREATE OR ALTER VIEW dbo.vw_payment_split AS
SELECT
    payment_method,
    venue_type,
    COUNT(*)                            AS transaction_count,
    SUM(net_amount)                     AS total_revenue,
    ROUND(
        100.0 * COUNT(*) /
        SUM(COUNT(*)) OVER (PARTITION BY venue_type),
    1)                                  AS pct_of_venue_transactions
FROM dbo.transactions
GROUP BY payment_method, venue_type;
"""
]

# ── Stored procedures ─────────────────────────────────────────────────────────

STORED_PROCEDURES = [
"""
CREATE OR ALTER PROCEDURE dbo.usp_venue_summary
    @venue_id     VARCHAR(10) = NULL,
    @start_date   DATE        = NULL,
    @end_date     DATE        = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Default to last 30 days if no dates provided
    SET @start_date = ISNULL(@start_date, DATEADD(DAY, -30, GETUTCDATE()));
    SET @end_date   = ISNULL(@end_date,   CAST(GETUTCDATE() AS DATE));

    SELECT
        venue_id,
        venue_name,
        venue_type,
        city,
        COUNT(*)                AS total_transactions,
        SUM(quantity)           AS total_items_sold,
        SUM(net_amount)         AS total_net_revenue,
        AVG(net_amount)         AS avg_transaction_value,
        MAX(net_amount)         AS highest_transaction,
        MIN(transaction_date)   AS first_date,
        MAX(transaction_date)   AS last_date
    FROM dbo.transactions
    WHERE
        (@venue_id IS NULL OR venue_id = @venue_id)
        AND transaction_date BETWEEN @start_date AND @end_date
    GROUP BY venue_id, venue_name, venue_type, city
    ORDER BY total_net_revenue DESC;
END;
""",
"""
CREATE OR ALTER PROCEDURE dbo.usp_top_items
    @venue_type   VARCHAR(20) = NULL,
    @top_n        INT         = 10
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@top_n)
        venue_type,
        category,
        item_name,
        SUM(quantity)       AS total_sold,
        SUM(net_amount)     AS total_revenue,
        AVG(unit_price)     AS avg_unit_price,
        COUNT(DISTINCT
            transaction_date) AS days_sold
    FROM dbo.transactions
    WHERE (@venue_type IS NULL OR venue_type = @venue_type)
    GROUP BY venue_type, category, item_name
    ORDER BY total_revenue DESC;
END;
""",
"""
CREATE OR ALTER PROCEDURE dbo.usp_monthly_trend
    @year   INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SET @year = ISNULL(@year, YEAR(GETUTCDATE()));

    SELECT
        month_num,
        month,
        venue_type,
        COUNT(*)                AS transactions,
        SUM(net_amount)         AS net_revenue,
        SUM(discount_amount)    AS discounts_given,
        AVG(net_amount)         AS avg_basket,
        -- Month-over-month revenue change
        LAG(SUM(net_amount)) OVER (
            PARTITION BY venue_type
            ORDER BY month_num
        )                       AS prev_month_revenue,
        ROUND(
            100.0 * (SUM(net_amount) - LAG(SUM(net_amount)) OVER (
                PARTITION BY venue_type ORDER BY month_num
            )) /
            NULLIF(LAG(SUM(net_amount)) OVER (
                PARTITION BY venue_type ORDER BY month_num
            ), 0)
        , 1)                    AS mom_growth_pct
    FROM dbo.transactions
    WHERE YEAR(transaction_date) = @year
    GROUP BY month_num, month, venue_type
    ORDER BY venue_type, month_num;
END;
"""
]

# ── Run everything ────────────────────────────────────────────────────────────

def setup_database():
    with engine.connect() as conn:
        print("Creating table...")
        conn.execute(text(CREATE_TABLE))
        conn.commit()

        print("Creating views...")
        for view_sql in CREATE_VIEWS:
            conn.execute(text(view_sql))
        conn.commit()

        print("Creating stored procedures...")
        for sp_sql in STORED_PROCEDURES:
            conn.execute(text(sp_sql))
        conn.commit()

    print("Schema setup complete.")


def load_data():
    df = pd.read_csv("data/hospitality_transactions.csv", parse_dates=["transaction_ts"])
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.date
    df["is_weekend"] = df["is_weekend"].astype(int)

    # Drop derived columns SQLAlchemy will complain about
    load_cols = [
        "transaction_id","venue_id","venue_name","venue_type","city","region",
        "transaction_date","transaction_time","transaction_ts","item_name",
        "category","quantity","unit_price","gross_amount","discount_pct",
        "discount_amount","net_amount","payment_method","is_weekend",
        "day_of_week","month","month_num"
    ]
    df = df[load_cols]

    print(f"Loading {len(df):,} rows into Azure SQL...")
    df.to_sql("transactions", engine, schema="dbo",
              if_exists="append", index=False, chunksize=500)
    print("Load complete.")


if __name__ == "__main__":
    setup_database()
    load_data()
    print("\nAll done. Test with:")
    print("  EXEC dbo.usp_venue_summary")
    print("  EXEC dbo.usp_top_items @venue_type = 'Pub', @top_n = 5")
    print("  EXEC dbo.usp_monthly_trend @year = 2024")
