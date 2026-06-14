CREATE DATABASE IF NOT EXISTS tradedb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tradedb;

CREATE TABLE IF NOT EXISTS trades (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code      VARCHAR(10)     NOT NULL COMMENT '銘柄コード',
    stock_name      VARCHAR(100)    NOT NULL COMMENT '銘柄名',
    cancel_flag     CHAR(1)         DEFAULT ' ' COMMENT '譲渡益取消区分',
    trade_date      DATE            NOT NULL COMMENT '約定日',
    quantity        INT             NOT NULL COMMENT '数量',
    trade_type      VARCHAR(20)     NOT NULL COMMENT '取引種別',
    settlement_date DATE            NOT NULL COMMENT '受渡日',
    sell_amount     BIGINT          NOT NULL COMMENT '売却/決済金額',
    fee             INT             NOT NULL DEFAULT 0 COMMENT '費用',
    acquire_date    DATE            NOT NULL COMMENT '取得/新規年月日',
    acquire_amount  BIGINT          NOT NULL COMMENT '取得/新規金額',
    pnl             INT             NOT NULL COMMENT '損益金額',
    local_tax       INT             DEFAULT NULL COMMENT '地方税',
    imported_at     DATETIME        NOT NULL COMMENT '取込日時',
    source_file     VARCHAR(255)    NOT NULL COMMENT '元CSVファイル名',
    UNIQUE KEY uq_trade (stock_code, trade_date, trade_type, sell_amount, acquire_date, acquire_amount)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='トレード明細';

CREATE OR REPLACE VIEW trades_view AS
SELECT
    *,
    CASE
        WHEN trade_type = '現物売' AND trade_date = acquire_date THEN 'day'
        WHEN trade_type != '現物売' AND settlement_date = acquire_date THEN 'day'
        ELSE 'swing'
    END AS trade_category,
    CASE WHEN pnl > 0 THEN 'win' ELSE 'loss' END AS win_loss
FROM trades;

CREATE TABLE IF NOT EXISTS daytrades (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    trade_date   DATE           NOT NULL COMMENT 'エントリー日',
    entry_at     DATETIME       NOT NULL COMMENT 'エントリー日時',
    exit_at      DATETIME       NOT NULL COMMENT 'エグジット日時',
    duration_sec INT            COMMENT '保有秒数',
    stock_code   VARCHAR(10)    NOT NULL COMMENT '銘柄コード',
    stock_name   VARCHAR(100)   COMMENT '銘柄名',
    side         VARCHAR(10)    NOT NULL COMMENT 'LONG / SHORT',
    quantity     INT            NOT NULL COMMENT '株数',
    entry_price  DECIMAL(12,2)  COMMENT 'エントリー価格',
    exit_price   DECIMAL(12,2)  COMMENT 'エグジット価格',
    pnl          DECIMAL(12,2)  COMMENT '損益',
    source_file  VARCHAR(255)   COMMENT '元ファイル名',
    imported_at  DATETIME       NOT NULL COMMENT '取込日時',
    UNIQUE KEY uq_daytrade (entry_at, exit_at, stock_code, side, quantity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='デイトレ明細';

CREATE TABLE IF NOT EXISTS import_logs (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_file     VARCHAR(255)    NOT NULL COMMENT '取込ファイル名',
    imported_at     DATETIME        NOT NULL COMMENT '取込日時',
    record_count    INT             NOT NULL COMMENT '取込件数',
    total_pnl       INT             NOT NULL COMMENT 'CSV記載の損益合計',
    status          VARCHAR(20)     NOT NULL COMMENT 'success / error'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='取込履歴';
