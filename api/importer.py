"""
CSVパース & MySQL挿入ロジック
"""

import csv
import io
import os
import re
from dataclasses import dataclass
from datetime import datetime, date

import mysql.connector


def get_db_config() -> dict:
    return {
        "host": "mysql",
        "port": 3306,
        "database": os.environ["MYSQL_DATABASE"],
        "user": os.environ["MYSQL_USER"],
        "password": os.environ["MYSQL_PASSWORD"],
        "charset": "utf8mb4",
    }


@dataclass
class ImportResult:
    filename: str
    parsed: int
    inserted: int
    skipped: int
    total_pnl: int
    warnings: list[str]


def parse_int(value: str) -> int:
    v = str(value).strip()
    if v in ("--", ""):
        return 0
    return int(v.replace(",", "").replace("+", ""))


def parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y/%m/%d").date()


def parse_quantity(value: str) -> int:
    return int(re.sub(r"[^\d]", "", value))


def parse_csv(content: bytes) -> tuple[int, list[dict], list[str]]:
    """
    CSVバイト列を受け取り (total_pnl, records, warnings) を返す。
    """
    text = content.decode("shift_jis", errors="replace")
    lines = text.splitlines()

    # 損益金額合計を取得
    total_pnl = 0
    for i, line in enumerate(lines):
        if "損益金額合計" in line and i + 1 < len(lines):
            val = lines[i + 1].strip()
            if val not in ("--", ""):
                total_pnl = int(val.replace(",", ""))
            break

    # データ開始行を探す
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith("銘柄コード"):
            data_start = i + 1
            break

    if data_start is None:
        raise ValueError("CSVのフォーマットが正しくありません（銘柄コード行が見つかりません）")

    records = []
    warnings = []
    reader = csv.reader(lines[data_start:])

    for row in reader:
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
            warnings.append(f"スキップ: {row[1] if len(row) > 1 else row} ({e})")

    return total_pnl, records, warnings


def run_import(filename: str, content: bytes) -> ImportResult:
    total_pnl, records, warnings = parse_csv(content)

    conn = mysql.connector.connect(**get_db_config())
    cursor = conn.cursor()

    try:
        # 取込済みチェック
        cursor.execute(
            "SELECT id FROM import_logs WHERE source_file = %s AND status = 'success'",
            (filename,)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return ImportResult(
                filename=filename,
                parsed=len(records),
                inserted=0,
                skipped=len(records),
                total_pnl=total_pnl,
                warnings=["このファイルはすでにインポート済みです"],
            )

        # 挿入
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
        for r in records:
            r["imported_at"] = now
            r["source_file"] = filename

        cursor.executemany(sql, records)
        inserted = cursor.rowcount

        cursor.execute(
            "INSERT INTO import_logs (source_file, imported_at, record_count, total_pnl, status) VALUES (%s, %s, %s, %s, 'success')",
            (filename, now, inserted, total_pnl)
        )
        conn.commit()

    except Exception:
        conn.rollback()
        cursor.execute(
            "INSERT INTO import_logs (source_file, imported_at, record_count, total_pnl, status) VALUES (%s, %s, 0, 0, 'error')",
            (filename, datetime.now())
        )
        conn.commit()
        raise
    finally:
        cursor.close()
        conn.close()

    return ImportResult(
        filename=filename,
        parsed=len(records),
        inserted=inserted,
        skipped=len(records) - inserted,
        total_pnl=total_pnl,
        warnings=warnings,
    )
