#!/usr/bin/env python3
"""
特定口座損益明細CSV → MySQL インポートスクリプト
使い方: docker compose run --rm importer
"""

import csv
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path

import mysql.connector

# --- DB接続設定（.envから取得）---
DB_CONFIG = {
    "host": "mysql",
    "port": 3306,
    "database": os.environ["MYSQL_DATABASE"],
    "user": os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "charset": "utf8mb4",
}

CSV_DIR = Path("/app/csv")


def parse_int(value: str) -> int:
    """"+8030", "-690", "--" などを整数に変換"""
    v = str(value).strip()
    if v == "--" or v == "":
        return 0
    return int(v.replace(",", "").replace("+", ""))


def parse_date(value: str) -> date:
    """2026/01/07 → date オブジェクト"""
    return datetime.strptime(value.strip(), "%Y/%m/%d").date()


def parse_quantity(value: str) -> int:
    """100株 → 100"""
    return int(re.sub(r"[^\d]", "", value))


def parse_csv(filepath: Path) -> tuple[int, list[dict]]:
    """
    CSVを読み込んでメタデータと明細レコードのリストを返す。
    Returns: (total_pnl, records)
    """
    with open(filepath, encoding="shift_jis", errors="replace") as f:
        lines = f.readlines()

    # 損益金額合計を取得（"損益金額合計" の次の行）
    total_pnl = 0
    for i, line in enumerate(lines):
        if "損益金額合計" in line and i + 1 < len(lines):
            val = lines[i + 1].strip()
            if val != "--" and val != "":
                total_pnl = int(val.replace(",", ""))
            break

    # データ行を探す（ヘッダー行 "銘柄コード," を含む行の次から）
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith("銘柄コード"):
            data_start = i + 1
            break

    if data_start is None:
        raise ValueError(f"データ行が見つかりません: {filepath}")

    records = []
    reader = csv.reader(lines[data_start:])
    for row in reader:
        # 空行・カラム数不足はスキップ
        if len(row) < 12:
            continue

        try:
            record = {
                "stock_code":      row[0].strip(),
                "stock_name":      row[1].strip(),
                "cancel_flag":     row[2].strip() or " ",
                "trade_date":      parse_date(row[3]),
                "quantity":        parse_quantity(row[4]),
                "trade_type":      row[5].strip(),
                "settlement_date": parse_date(row[6]),
                "sell_amount":     parse_int(row[7]),
                "fee":             parse_int(row[8]),
                "acquire_date":    parse_date(row[9]),
                "acquire_amount":  parse_int(row[10]),
                "pnl":             parse_int(row[11]),
                "local_tax":       parse_int(row[12]) if len(row) > 12 else None,
            }
            records.append(record)
        except Exception as e:
            print(f"  [WARN] 行スキップ ({e}): {row}")

    return total_pnl, records


def is_already_imported(cursor, filename: str) -> bool:
    cursor.execute(
        "SELECT id FROM import_logs WHERE source_file = %s AND status = 'success'",
        (filename,)
    )
    return cursor.fetchone() is not None


def import_records(cursor, records: list[dict], filename: str) -> int:
    sql = """
        INSERT IGNORE INTO trades
            (stock_code, stock_name, cancel_flag, trade_date, quantity, trade_type,
             settlement_date, sell_amount, fee, acquire_date, acquire_amount,
             pnl, local_tax, imported_at, source_file)
        VALUES
            (%(stock_code)s, %(stock_name)s, %(cancel_flag)s, %(trade_date)s,
             %(quantity)s, %(trade_type)s, %(settlement_date)s, %(sell_amount)s,
             %(fee)s, %(acquire_date)s, %(acquire_amount)s, %(pnl)s,
             %(local_tax)s, %(imported_at)s, %(source_file)s)
    """
    now = datetime.now()
    for record in records:
        record["imported_at"] = now
        record["source_file"] = filename

    cursor.executemany(sql, records)
    return cursor.rowcount


def log_import(cursor, filename: str, record_count: int, total_pnl: int, status: str):
    cursor.execute(
        """INSERT INTO import_logs (source_file, imported_at, record_count, total_pnl, status)
           VALUES (%s, %s, %s, %s, %s)""",
        (filename, datetime.now(), record_count, total_pnl, status)
    )


def main():
    csv_files = sorted(CSV_DIR.glob("*.csv"))
    if not csv_files:
        print(f"CSVファイルが見つかりません: {CSV_DIR}")
        sys.exit(0)

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    total_imported = 0

    for filepath in csv_files:
        filename = filepath.name
        print(f"\n[{filename}] 処理開始")

        if is_already_imported(cursor, filename):
            print(f"  → スキップ（インポート済み）")
            continue

        try:
            total_pnl, records = parse_csv(filepath)
            print(f"  → {len(records)} 件を読み込み / 損益合計: {total_pnl:+,}")

            inserted = import_records(cursor, records, filename)
            log_import(cursor, filename, inserted, total_pnl, "success")
            conn.commit()

            print(f"  → {inserted} 件をDBに挿入（重複除外済み）")
            total_imported += inserted

        except Exception as e:
            conn.rollback()
            log_import(cursor, filename, 0, 0, "error")
            conn.commit()
            print(f"  [ERROR] {e}")

    cursor.close()
    conn.close()
    print(f"\n完了: 合計 {total_imported} 件を追加しました")


if __name__ == "__main__":
    main()
