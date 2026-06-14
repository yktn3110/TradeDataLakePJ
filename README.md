# TradeDataLakePJ

SBI証券の特定口座損益CSVをMySQLに取り込み、Grafanaで可視化するツール。

## 構成

| サービス | イメージ | ポート |
|---|---|---|
| MySQL 8.0 | mysql:8.0 | 3307 |
| FastAPI | (独自ビルド) | 8000 |
| Grafana | grafana/grafana:latest | 3000 |
| Image Renderer | grafana/grafana-image-renderer | 8081 |

## テーブル構成

### `trades` — SBI証券CSV取込データ（メイン）

SBI証券の特定口座損益CSVをインポートしたトレード明細。

- `trade_date`: 約定日
- `trade_type`: 取引種別（現物売 / 信用返済売 / 信用返済買 など）
- `sell_amount`: 売却/決済金額（**手数料控除後の実額**）
- `fee`: 手数料（`sell_amount` に既に反映済み。参照用）
- `pnl`: 損益 = `sell_amount` - `acquire_amount`（手数料込み）

`trades_view` でデイトレ/スイング判定を付与して参照。

### `daytrades` — デイトレ分析データ

デイトレツール（Excel）からインポートした約定記録。entry/exit の価格・時刻を保持。

- `side`: LONG / SHORT
- `entry_price` / `exit_price`: 約定価格（**手数料を含まない生の価格**）
- `pnl`: `(exit - entry) × quantity`（手数料未控除）

### `import_logs` — CSV取込履歴

## データ入力フロー

```
SBI証券CSV → FastAPI (/upload) → trades
デイトレExcel → FastAPI (/daytrade/upload) → daytrades
```

## daytrades と trades の関係

2テーブルは**独立して管理**する。

`daytrades` は時刻・価格の詳細分析用、`trades` はSBI公式記録に基づく損益集計用。
Grafanaでの可視化も各テーブルを独立したデータソースとして扱う。

**転記を行わない理由:** `daytrades` の pnl は手数料未控除（約定価格×株数）だが、
`trades` の pnl はSBI側で手数料が sell_amount に反映された実損益であり、
両者を自動同期すると1件あたり数百〜数千円のズレが生じる。

## 起動方法

### 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) がインストール済みで起動していること

### 初回セットアップ

```bash
# リポジトリをクローン後、プロジェクトディレクトリへ移動
cd TradeDataLakePJ

# .env ファイルを作成（すでにある場合はスキップ）
# MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD を設定
cp .env.example .env   # Linux/Mac
copy .env.example .env  # Windows
```

### 起動（通常）

```bash
docker compose up -d
```

Windows の場合は `start.bat` をダブルクリックするだけでも起動できます。

### 停止

```bash
docker compose down
```

### アクセス先

| サービス | URL | 備考 |
|---|---|---|
| Grafana | http://localhost:3000 | ユーザー: admin / パスワード: admin |
| API Docs | http://localhost:8000/docs | FastAPI Swagger UI |
| API | http://localhost:8000 | CSVアップロード等 |

### データ投入

Grafana の「CSVアップロード」リンクから:

- **SBI証券 特定口座損益CSV** → `/upload` で `trades` テーブルに取込
- **デイトレExcelエクスポートxlsx** → `/upload/daytrade` で `daytrades` テーブルに取込

### ログ確認

```bash
docker compose logs -f        # 全サービス
docker compose logs -f api    # APIのみ
docker compose logs -f grafana  # Grafanaのみ
```
