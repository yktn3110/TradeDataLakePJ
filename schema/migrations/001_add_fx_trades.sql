-- Migration 001: fx_tradesテーブル追加
-- 実行方法:
--   docker exec trade_mysql mysql -u tradeuser -ptradepass tradedb < mysql/migrations/001_add_fx_trades.sql

CREATE TABLE IF NOT EXISTS fx_trades (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    trade_date      DATE            NOT NULL COMMENT '約定日',
    entry_at        DATETIME        NOT NULL COMMENT 'エントリー日時',
    exit_at         DATETIME        NOT NULL COMMENT 'エグジット日時',
    duration_sec    INT             COMMENT '保有秒数',
    currency_pair   VARCHAR(10)     NOT NULL COMMENT '通貨ペア（例: USD/JPY）',
    side            VARCHAR(10)     NOT NULL COMMENT 'LONG / SHORT',
    lot_size        DECIMAL(12,2)   NOT NULL COMMENT 'ロット数',
    entry_price     DECIMAL(12,5)   NOT NULL COMMENT 'エントリー価格',
    exit_price      DECIMAL(12,5)   NOT NULL COMMENT 'エグジット価格',
    pnl_pips        DECIMAL(10,2)   COMMENT '損益（pips）',
    pnl_jpy         DECIMAL(12,2)   COMMENT '損益（円換算）',
    swap            DECIMAL(12,2)   DEFAULT 0 COMMENT 'スワップ',
    memo            TEXT            COMMENT 'メモ',
    source_file     VARCHAR(255)    COMMENT '元ファイル名',
    imported_at     DATETIME        NOT NULL COMMENT '取込日時',
    UNIQUE KEY uq_fxtrade (entry_at, exit_at, currency_pair, side, lot_size)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='FXトレード明細';
