# トレード解析ツール 設計ドキュメント

## 概要

特定口座損益明細CSVをMySQLに蓄積し、Grafanaダッシュボードで解析する個人向けトレード分析ツール。

## 決定事項

| 項目 | 決定内容 |
|---|---|
| DB | MySQL 8.0 |
| ダッシュボード | Grafana latest（ダークテーマ） |
| CSVアップロード | FastAPI（ブラウザからアップロード） |
| インフラ | Docker Compose（自宅PC） |
| アクセス方法 | 同一WiFi内からブラウザ（スマホ・PC対応） |
| 外出先アクセス | 将来的にVPN対応（現時点は対象外） |
| 空売り扱い | 現物売・信用返済売・信用返済買 すべて同等に損益計上 |

## URL

| サービス | URL |
|---|---|
| Grafanaダッシュボード | http://localhost:3000 |
| CSVアップロード画面 | http://localhost:8000 |
| MySQL | localhost:3307 |

## システム構成

```
[SBI証券CSV] --ブラウザ--> [FastAPI :8000] --> [MySQL :3306]
                                                      |
                                                   Grafana :3000
                                                      |
                                       スマホ/PC ブラウザ (http://192.168.x.x:3000)
```

## Docker Compose 構成

```yaml
services:
  mysql:   image: mysql:8.0       port: 3307
  api:     build: api/Dockerfile  port: 8000
  grafana: image: grafana:latest  port: 3000
  renderer: image: grafana-image-renderer  port: 8081
```

## データソース

- SBI証券 特定口座損益明細CSV
- エンコーディング: Shift-JIS
- 追加方式: ブラウザから http://localhost:8000 でアップロード（差分追加・重複スキップ）

### CSVカラム構成（21行目以降がデータ）

| # | カラム名 | 例 | 備考 |
|---|---------|-----|------|
| 1 | 銘柄コード | 8306 | 空白パディングあり → trim |
| 2 | 銘柄名 | 三菱UFJフィナンシャル・グループ | |
| 3 | 譲渡益取消区分 | (空白) | |
| 4 | 約定日 | 2026/01/07 | DATE型 |
| 5 | 数量 | 100株 | "株"除去して INT |
| 6 | 取引種別 | 現物売 / 信用返済売 / 信用返済買 | |
| 7 | 受渡日 | 2026/01/09 | DATE型 |
| 8 | 売却/決済金額 | 262130 | BIGINT |
| 9 | 費用 | 150 / -- | "--"は0扱い |
| 10 | 取得/新規年月日 | 2026/01/07 | DATE型、信用は建玉の受渡日 |
| 11 | 取得/新規金額 | 254100 | BIGINT |
| 12 | 損益金額/徴収額 | +8030 / -690 | INT 符号付き |
| 13 | 地方税 | (任意) | NULL許容 |

## DBスキーマ

### trades テーブル

```sql
CREATE TABLE trades (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code      VARCHAR(10)     NOT NULL,
    stock_name      VARCHAR(100)    NOT NULL,
    cancel_flag     CHAR(1)         DEFAULT ' ',
    trade_date      DATE            NOT NULL,
    quantity        INT             NOT NULL,
    trade_type      VARCHAR(20)     NOT NULL,
    settlement_date DATE            NOT NULL,
    sell_amount     BIGINT          NOT NULL,
    fee             INT             NOT NULL DEFAULT 0,
    acquire_date    DATE            NOT NULL,
    acquire_amount  BIGINT          NOT NULL,
    pnl             INT             NOT NULL,
    local_tax       INT             DEFAULT NULL,
    imported_at     DATETIME        NOT NULL,
    source_file     VARCHAR(255)    NOT NULL,
    UNIQUE KEY uq_trade (stock_code, trade_date, trade_type, sell_amount, acquire_date, acquire_amount)
);
```

### trades_view ビュー

```sql
CREATE VIEW trades_view AS
SELECT *,
    CASE
        WHEN trade_type = '現物売' AND trade_date = acquire_date THEN 'day'
        WHEN trade_type != '現物売' AND settlement_date = acquire_date THEN 'day'
        ELSE 'swing'
    END AS trade_category,
    CASE WHEN pnl > 0 THEN 'win' ELSE 'loss' END AS win_loss
FROM trades;
```

**デイ/スイング判定ロジック:**
- 現物売: `trade_date = acquire_date` → デイ
- 信用取引: `settlement_date = acquire_date` → デイ（acquire_dateは建玉受渡日のため）

### import_logs テーブル

```sql
CREATE TABLE import_logs (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_file     VARCHAR(255)    NOT NULL,
    imported_at     DATETIME        NOT NULL,
    record_count    INT             NOT NULL,
    total_pnl       INT             NOT NULL,
    status          VARCHAR(20)     NOT NULL
);
```

## 重複防止

- `import_logs` に記録済みファイル名があればスキップ
- UNIQUE KEY で同一レコードの重複挿入を防止（INSERT IGNORE）

## Grafanaダッシュボード構成

### フィルタ変数（全パネル共通）
- **期間**: 開始日〜終了日（日付ピッカー）
- **銘柄**: 銘柄コード+銘柄名のドロップダウン（複数選択可）
- **デイ/スイング**: All / day / swing

### 期間分析セクション（日付フィルターあり）
- サマリー stat × 6: 総損益 / トレード数 / 勝率 / PF / 平均利益 / 平均損失
- 累積損益カーブ（timeseries、スムーズライン）
- 日別損益（barchart、全幅）
- 銘柄別損益 TOP15（横棒）
- 取引種別内訳（ドーナツ円グラフ）

### 全期間サマリーセクション（日付フィルターなし）
- 損益分布ヒストグラム
- 月別損益棒グラフ
- 年別損益棒グラフ
- トレード明細テーブル（最新500件、日付フィルターあり）

### ダッシュボードリンク
- CSVアップロード画面へのリンク（http://localhost:8000）

## TODO

- [ ] **スマホからのアクセス確認** — PCのローカルIP（192.168.x.x）でGrafana(:3000)とアップロード画面(:8000)にアクセスできるか確認。Windowsファイアウォールでポート開放が必要な場合あり
- [ ] **APIアクセス** — FastAPIのエンドポイントをスマホ等から直接叩けるか確認（現状は `/` と `/upload` のみ）

## Grafana Image Renderer

パネル右上「...」→「More」→「Download image」でPNG出力可能。
renderer コンテナ（port 8081）がGrafanaと連携して動作。
