/* Support Hub 1.2.0 - shared default contracts, SQL Server, safe to rerun. */
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH('dbo.contracts', 'is_shared_default') IS NULL
        ALTER TABLE dbo.contracts ADD is_shared_default BIT NOT NULL
            CONSTRAINT df_contracts_is_shared_default DEFAULT (0);

    IF OBJECT_ID('dbo.contract_client_links', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.contract_client_links (
            id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT pk_contract_client_links PRIMARY KEY,
            contract_id BIGINT NOT NULL,
            client_id BIGINT NOT NULL,
            CONSTRAINT fk_contract_client_links_contract FOREIGN KEY (contract_id)
                REFERENCES dbo.contracts(id) ON DELETE CASCADE,
            CONSTRAINT fk_contract_client_links_client FOREIGN KEY (client_id)
                REFERENCES dbo.clients(id) ON DELETE CASCADE,
            CONSTRAINT uq_contract_client_link UNIQUE (contract_id, client_id)
        );
    END;

    INSERT INTO dbo.contract_client_links (contract_id, client_id)
    SELECT c.id, c.client_id
    FROM dbo.contracts c
    WHERE NOT EXISTS (
        SELECT 1 FROM dbo.contract_client_links l
        WHERE l.contract_id = c.id AND l.client_id = c.client_id
    );

    COMMIT TRANSACTION;
    PRINT 'Support Hub 1.2.0 database upgrade completed successfully.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

