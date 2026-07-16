# 📊 Hospitality EPOS Data Platform
### End-to-End Modern Data Stack | Azure SQL • Azure Data Factory • Snowflake • dbt Cloud • Power BI

This project simulates the enterprise analytics infrastructure an EPOS (Electronic Point of Sale) provider would build to give hospitality operators actionable, real-time visibility into revenue patterns, menu performance, and guest retention lifecycles.

<p align="center">

[![Azure SQL](https://img.shields.io/badge/Azure_SQL-0078D4?style=for-the-badge&logo=microsoftazuresql&logoColor=white)](https://azure.microsoft.com/)
[![Azure ADF](https://img.shields.io/badge/Azure_Data_Factory-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white)](https://www.snowflake.com/)
[![dbt](https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![Power BI](https://img.shields.io/badge/Power_BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)

</p>

---

## 🎨 Interactive Product Showcase

### 🎥 Live Dashboard Demo
The executive suite features dynamic cross-filtering and an intuitive canvas reset action, backed by a live database engine:

![Platform Walkthrough](images/dashboard_demo.gif)

### 📸 Executive Dashboard Pages
| Page 1: Executive Venue Performance | Page 2: Guest Retention & Value Forecast |
|:---:|:---:|
| ![Executive Venue Performance](images/venue_performance.png) | ![Guest Retention and Analysis](images/retention_analysis.png) |

---

## 🏗️ Platform Architecture & Lineage

### ⚡ Technical Solution Diagram
This architectural blueprint maps the end-to-end data flow from local generation and cloud warehouse landing, through the three-tier dbt transformation engine, to our live analytical serving layer:

```mermaid
flowchart LR
    %% Define Styles
    classDef storage fill:#f9f9f9,stroke:#333,stroke-width:1px,stroke-dasharray: 3 3,color:#333;
    classDef raw fill:#29B5E8,stroke:#1a82a8,stroke-width:2px,color:#fff;
    classDef dbt fill:#FF694B,stroke:#cd492d,stroke-width:2px,color:#fff;
    classDef ephemeral fill:#f1f1f1,stroke:#bcbcbc,stroke-width:1px,stroke-dasharray: 5 5,color:#555;
    classDef analytics fill:#0075A2,stroke:#005170,stroke-width:2px,color:#fff;
    classDef bi fill:#F2C811,stroke:#cba102,stroke-width:2px,color:#222;

    %% Column 1: Ingestion
    subgraph Ingestion ["1. INGESTION & STORAGE"]
        direction TB
        A[Local CSV Generator<br/><b>Python</b>]:::storage
        B[(Azure SQL Database<br/><b>dbo.transactions</b>)]:::storage
        C[(Snowflake RAW<br/><b>RAW.TRANSACTIONS</b>)]:::raw
        
        A -->|pyodbc Load| B
        B -->|Azure Data Factory| C
    end

    %% Column 2: dbt Pipeline
    subgraph pipeline ["2. dbt TRANSFORMATION"]
        direction TB
        D[stg_transactions<br/><b>View</b>]:::dbt
        E[int_customer_visit_history<br/><b>Ephemeral CTE</b>]:::ephemeral
        
        D -->|dbt ref| E
    end

    %% Column 3: Serving & BI
    subgraph Serving ["3. SERVING & BI LAYER"]
        direction TB
        F1[(Snowflake Analytics<br/><b>fct_venue_performance_showcase</b><br/><i>Table</i>)]:::analytics
        F2[(Snowflake Analytics<br/><b>fct_customer_retention_forecast</b><br/><i>Table</i>)]:::analytics
        G[[Power BI Desktop<br/><b>2-Page Exec Dashboard</b>]]:::bi
        
        F1 & F2 <===>|Live DirectQuery| G
    end

    C -.->|dbt Source| D
    D -->|dbt ref| F1
    E -->|dbt ref| F2
```

### 🧪 dbt Model Lineage Graph
The Directed Acyclic Graph (DAG) below illustrates the modular relationship and dependency flow across the staging, intermediate, and serving layers:

 ![dbt Lineage Graph](images/dbt_lineage.png)

### 📈 Snowflake Schema Diagram
This structural breakdown of our Snowflake instance displays the physical segregation of our raw ingestion layer and our optimized serving schemas:

 ![Snowflake Schema](images/snowflake_schema.png)

---

## 📖 Project Overview

This project demonstrates the design and implementation of an **enterprise-grade analytics platform** for hospitality and restaurant EPOS (Electronic Point of Sale) transaction records using a modern cloud data stack.

The platform ingests raw transactional data from source systems, processes it through a modular dbt pipeline using **dbt Cloud**, stores the curated data inside **Snowflake**, and exposes business-intelligence-ready data marts to interactive **Power BI Desktop** executive dashboards via live **DirectQuery** connections.

> [!TIP]
> ### Curious how this project was actually built?
> Explore the **Engineering Journal** to follow the complete development journey—from the first Snowflake connection and dbt modeling decisions to debugging production issues, Power BI optimization, Git workflow, and final deployment.
> 
> 📔 [Hospitality Platform Engineering Journal](engineering_journal.md)

---

## 🚀 Quick Start & Deployment

### 1. Prerequisites
* A **Snowflake** account with `SYSADMIN` privileges.
* A **dbt Cloud** developer account connected to your data warehouse.
* **Power BI Desktop** installed locally.

### 2. Warehouse Ingestion
Run your initial structural setup scripts to land data inside `HOSPITALITY_DW.RAW.TRANSACTIONS`.

### 3. Pipeline Execution
Navigate to your dbt Cloud terminal and initialize the dependencies and transformation layers:
```bash
dbt deps
dbt seed
dbt run
```

## 3. BI Visual Initialization

Open the localized `.pbix` file template inside your repository, specify
your Snowflake server account credentials when prompted, and opt for
**DirectQuery** to enable live database cross-filtering.

------------------------------------------------------------------------

# 📂 Data Warehouse Architecture

The project follows a layered data warehouse architecture that separates
ingestion, transformation, and presentation responsibilities.

## 🔹 Raw Layer

**Schema:** `HOSPITALITY_DW.RAW`

-   Stores the immutable, historical ingestion table (`TRANSACTIONS`)
    landed from source datasets.
-   Preserves raw record integrity without modifying physical rows.

------------------------------------------------------------------------

## 🔹 Staging Layer

**Materialization:** `view`\
**Location:** `models/staging/`

-   Enforces structural cast types (such as forcing string
    representations into clean numerics).
-   Standardizes field names and shapes to fit enterprise guidelines.

------------------------------------------------------------------------

## 🔹 Intermediate Layer

**Materialization:** `ephemeral`  
**Location:** `models/intermediate/`

Implements core customer identity tracking, chronological visit tracking, and lifecycle sequencing.

Advanced SQL window functions track chronological behaviors per guest using the unique `customer_id` pool:

```sql
row_number() over (
    partition by customer_id
    order by transaction_ts
) as customer_visit_number,

lag(transaction_ts) over (
    partition by customer_id
    order by transaction_ts
) as previous_visit_ts
```

------------------------------------------------------------------------

## 🔹 Analytics Layer (Data Marts)

**Schema:** `HOSPITALITY_DW.ANALYTICS`\
**Materialization:** `table`

### 📈 `fct_customer_retention_forecast`

Tailored for marketing directors and growth strategists to analyze
customer loyalty life cycles, repeat booking rates, and project future
revenue gains.

### 📊 `fct_venue_performance_showcase`

Built for executive operational dashboards to visualize macro
transactional performance across physical locations, categories, and
venue types.

------------------------------------------------------------------------

## ⚠️ Data Modeling & Design Considerations

### Customer Retention Surrogate Key Refactoring
During initial testing, customer retention metrics displayed an artificial **99.94% customer loyalty rate**. 

A critical code review revealed the cause: the customer surrogate key was generated using transaction characteristics: `md5(payment_method || city || venue_type)`. Since this mapped *transaction segment patterns* rather than *actual individuals*, thousands of unique guests were calculated as the same customer returning.

To align the platform with production-grade engineering standards:
1. **Refactored Ingestion:** Upgraded the Python generator (`01_generate_data.py`) to create a pool of 2,000 unique customer IDs (`customer_id`) mapped via weighted distributions to simulate realistic visit habits.
2. **Updated Transformations:** Rebuilt `int_customer_visit_history.sql` to sequence visits by `customer_id` and widened the metric boundaries to standard business segments (30/90/180 days).
3. **Outcome:** The retention dashboard refreshed to present a highly realistic, actionable customer lifecycle story.

> **Security & Governance Note:** To prioritize local development access, pipeline operations run using the `SYSADMIN` role[cite: 1]. In an enterprise production deployment, execution would run under a dedicated service account role restricted strictly to the raw and analytics schemas.

------------------------------------------------------------------------

# 🚀 Engineering Highlights & Wins

-   **⚙️ Custom dbt Schema Override Macro:** Overrode dbt's native
    runtime environment mapping with a custom `generate_schema_name.sql`
    macro to cleanly strip target prefixes, dropping staging models into
    `RAW` and finalized serving tables directly into `ANALYTICS`.
-   **🔒 Snowflake Least-Privilege Role Security:** Configured robust
    Role-Based Access Controls (RBAC), transferring table ownership
    structures safely from administrative tiers down to production
    execution roles.
-   **⚡ DirectQuery Optimization:** Configured Power BI with a live
    DirectQuery connector to push heavy data warehouse aggregates onto
    Snowflake clusters, removing local client processing bottlenecks.

------------------------------------------------------------------------

# 🛠️ Technology Stack

  Category                Technology
  ----------------------- ------------------------------
  Ingestion Storage       Azure SQL Database
  Data Orchestration      Azure Data Factory (ADF)
  Cloud Storage           Azure Blob Storage
  Data Warehouse          Snowflake
  Compute Warehouse       COMPUTE_WH (`SYSADMIN` Role)
  Transformation Engine   dbt Cloud
  Analytics Language      SQL (Snowflake Dialect)
  BI Platform             Power BI Desktop
  Connection Protocol     DirectQuery
  Version Control         Git, GitHub Desktop & GitHub

------------------------------------------------------------------------

# 📁 Repository Structure

``` text
hospitality-epos-data-pipeline/
│
├── models/
│   ├── staging/
│   │   ├── src_hospitality.yml
│   │   └── stg_transactions.sql
│   ├── intermediate/
│   │   └── int_customer_visit_history.sql
│   └── marts/
│       ├── fct_customer_retention_forecast.sql
│       └── fct_venue_performance_showcase.sql
├── macros/
│   └── generate_schema_name.sql
├── images/
│   ├── venue_performance.png
│   ├── retention_analysis.png
│   ├── dbt_lineage.png
│   └── snowflake_schema.png
├── docs/
├── engineering_journal.md
└── README.md
```

------------------------------------------------------------------------

# 🎯 Skills Demonstrated

-   Modern Data Stack Architectures (Snowflake + dbt Cloud + Power BI)
-   Dimensional Modeling & ELT Designs (Staging, Ephemeral, Mart layers)
-   Customer Identity Modelling & Surrogate Key Design (Partition sequencing, behavioral analysis thresholds)
-   Cloud Security and RBAC (Privilege transfers, Sysadmin environments,
    least-privilege schemas)
-   DirectQuery Dashboard Optimization (Slicers, Custom button actions,
    clear hierarchy UX)
-   Engineering Version Control (Git, branching, merging, GitHub Desktop
    flow)
