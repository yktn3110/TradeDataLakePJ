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
詳細は `feature/daytrade-sync` ブランチの検討履歴を参照。

## 起動方法

```bash
cp .env.example .env  # 環境変数を設定
docker compose up -d
```

Grafana: http://localhost:3000 (admin/admin)
API docs: http://localhost:8000/docs
