-- 004: קטלוג מוצרים ומסמכים (docs/07 §7.4)
-- הרצה: python -m scripts.migrate מתוך backend, אחרי 003.

CREATE TABLE rm_products (
    product_id         UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    type               NVARCHAR(30)     NOT NULL,
    name               NVARCHAR(120)    NOT NULL,
    institution_id     UNIQUEIDENTIFIER NOT NULL,
    institution_name   NVARCHAR(200)    NOT NULL,
    track              NVARCHAR(120)    NOT NULL,
    symbol             NVARCHAR(20)     NULL,
    fee_deposit        DECIMAL(18, 2)   NOT NULL,
    fee_assets         DECIMAL(18, 2)   NOT NULL,
    return_1y          DECIMAL(18, 2)   NOT NULL,
    return_3y          DECIMAL(18, 2)   NOT NULL,
    return_5y          DECIMAL(18, 2)   NOT NULL,
    std_dev            DECIMAL(18, 2)   NOT NULL,
    risk_level         SMALLINT         NOT NULL,
    liquidity          NVARCHAR(30)     NOT NULL,
    liquidity_terms    NVARCHAR(500)    NOT NULL,
    tax_notes          NVARCHAR(500)    NOT NULL,
    min_deposit        DECIMAL(18, 2)   NOT NULL,
    description        NVARCHAR(MAX)    NOT NULL,
    is_active          BIT              NOT NULL,
    search_text        NVARCHAR(MAX)    NOT NULL,
    updated_at         DATETIME2(3)     NOT NULL
);
CREATE INDEX IX_rm_products_institution ON rm_products(institution_id);

CREATE TABLE rm_product_documents (
    document_id    UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    product_id     UNIQUEIDENTIFIER NOT NULL,
    file_name      NVARCHAR(200)    NOT NULL,
    stored_name    NVARCHAR(80)     NOT NULL,
    doc_type       NVARCHAR(40)     NOT NULL,
    storage_path   NVARCHAR(80)     NOT NULL,
    sha256         NVARCHAR(64)     NOT NULL,
    size_bytes     INT              NOT NULL,
    index_status   NVARCHAR(20)     NOT NULL,
    chunks_count   INT              NULL,
    uploaded_at    DATETIME2(3)     NOT NULL
);
CREATE INDEX IX_rm_product_documents_product ON rm_product_documents(product_id);
