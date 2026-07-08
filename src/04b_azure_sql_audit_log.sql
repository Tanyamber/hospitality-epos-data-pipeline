-- Run this in Azure SQL BEFORE setting up ADF pipeline.
-- Creates the audit log table and stored procedure that ADF calls after each run.

-- ── Audit log table ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dbo.pipeline_run_log (
    log_id          INT IDENTITY(1,1) PRIMARY KEY,
    pipeline_name   VARCHAR(100)   NOT NULL,
    run_timestamp   DATETIME2      NOT NULL DEFAULT GETUTCDATE(),
    rows_copied     INT            NULL,
    run_status      VARCHAR(20)    NOT NULL,
    notes           NVARCHAR(500)  NULL
);
GO

-- ── Stored procedure called by ADF after each pipeline run ────────────────────

CREATE OR ALTER PROCEDURE dbo.usp_log_pipeline_run
    @pipeline_name  VARCHAR(100),
    @rows_copied    INT           = NULL,
    @run_status     VARCHAR(20)   = 'SUCCESS',
    @notes          NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO dbo.pipeline_run_log
        (pipeline_name, rows_copied, run_status, notes)
    VALUES
        (@pipeline_name, @rows_copied, @run_status, @notes);

    -- Return the log entry just created
    SELECT TOP 1 *
    FROM dbo.pipeline_run_log
    ORDER BY log_id DESC;
END;
GO

-- ── Check pipeline history ────────────────────────────────────────────────────

-- Run this to see all pipeline executions:
-- SELECT * FROM dbo.pipeline_run_log ORDER BY run_timestamp DESC;
