#!/usr/bin/env python3
"""Read-only introspection for the congress-db Neon schema."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("docs/design/congress-db-introspection")
DEFAULT_SCHEMAS = ("public",)
dict_row = None
psycopg = None


def ensure_psycopg() -> None:
    global dict_row, psycopg
    if psycopg is not None and dict_row is not None:
        return
    try:
        import psycopg as imported_psycopg
        from psycopg.rows import dict_row as imported_dict_row
    except ImportError as exc:  # pragma: no cover - exercised by operator setup.
        raise SystemExit(
            "Missing dependency: install with `python3 -m pip install -r requirements-dev.txt`"
        ) from exc
    psycopg = imported_psycopg
    dict_row = imported_dict_row


@dataclass(frozen=True)
class Column:
    table_schema: str
    table_name: str
    column_name: str
    ordinal_position: int
    data_type: str
    udt_name: str
    is_nullable: bool
    column_default: str | None
    comment: str | None


@dataclass(frozen=True)
class ForeignKey:
    constraint_name: str
    table_schema: str
    table_name: str
    column_names: list[str]
    foreign_table_schema: str
    foreign_table_name: str
    foreign_column_names: list[str]


@dataclass(frozen=True)
class Index:
    table_schema: str
    table_name: str
    index_name: str
    index_definition: str


def json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def fetch_all(conn: "psycopg.Connection", query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    ensure_psycopg()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def assert_read_only(conn: "psycopg.Connection") -> dict[str, Any]:
    rows = fetch_all(
        conn,
        """
        SELECT
          current_user,
          session_user,
          current_setting('transaction_read_only') AS transaction_read_only,
          pg_is_in_recovery() AS server_in_recovery
        """,
    )
    identity = rows[0]
    user = str(identity["current_user"])
    if user in {"postgres", "neondb_owner"} or "owner" in user or "admin" in user:
        raise SystemExit(
            f"Refusing to introspect with non-read-only-looking role: {user}"
        )
    return identity


def introspect(
    conn: "psycopg.Connection",
    *,
    included_schemas: tuple[str, ...] = DEFAULT_SCHEMAS,
) -> dict[str, Any]:
    identity = assert_read_only(conn)
    schema_params = (list(included_schemas),)
    schemas = fetch_all(
        conn,
        """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name = ANY(%s)
        ORDER BY schema_name
        """,
        schema_params,
    )
    tables = fetch_all(
        conn,
        """
        SELECT
          n.nspname AS table_schema,
          c.relname AS table_name,
          CASE c.relkind
            WHEN 'r' THEN 'table'
            WHEN 'p' THEN 'partitioned_table'
            WHEN 'v' THEN 'view'
            WHEN 'm' THEN 'materialized_view'
            ELSE c.relkind::text
          END AS table_type,
          obj_description(c.oid, 'pg_class') AS comment
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = ANY(%s)
          AND c.relkind IN ('r', 'p', 'v', 'm')
        ORDER BY n.nspname, c.relname
        """,
        schema_params,
    )
    columns = [
        Column(
            table_schema=row["table_schema"],
            table_name=row["table_name"],
            column_name=row["column_name"],
            ordinal_position=row["ordinal_position"],
            data_type=row["data_type"],
            udt_name=row["udt_name"],
            is_nullable=row["is_nullable"] == "YES",
            column_default=row["column_default"],
            comment=row["comment"],
        )
        for row in fetch_all(
            conn,
            """
            SELECT
              c.table_schema,
              c.table_name,
              c.column_name,
              c.ordinal_position,
              c.data_type,
              c.udt_name,
              c.is_nullable,
              c.column_default,
              col_description(pc.oid, c.ordinal_position) AS comment
            FROM information_schema.columns c
            JOIN pg_namespace pn ON pn.nspname = c.table_schema
            JOIN pg_class pc ON pc.relnamespace = pn.oid AND pc.relname = c.table_name
            WHERE c.table_schema = ANY(%s)
            ORDER BY c.table_schema, c.table_name, c.ordinal_position
            """,
            schema_params,
        )
    ]
    foreign_keys = [
        ForeignKey(
            constraint_name=row["constraint_name"],
            table_schema=row["table_schema"],
            table_name=row["table_name"],
            column_names=row["column_names"],
            foreign_table_schema=row["foreign_table_schema"],
            foreign_table_name=row["foreign_table_name"],
            foreign_column_names=row["foreign_column_names"],
        )
        for row in fetch_all(
            conn,
            """
            SELECT
              con.conname AS constraint_name,
              src_ns.nspname AS table_schema,
              src.relname AS table_name,
              array_agg(src_att.attname ORDER BY ord.ordinality) AS column_names,
              dst_ns.nspname AS foreign_table_schema,
              dst.relname AS foreign_table_name,
              array_agg(dst_att.attname ORDER BY ord.ordinality) AS foreign_column_names
            FROM pg_constraint con
            JOIN pg_class src ON src.oid = con.conrelid
            JOIN pg_namespace src_ns ON src_ns.oid = src.relnamespace
            JOIN pg_class dst ON dst.oid = con.confrelid
            JOIN pg_namespace dst_ns ON dst_ns.oid = dst.relnamespace
            JOIN unnest(con.conkey) WITH ORDINALITY AS ord(attnum, ordinality) ON true
            JOIN pg_attribute src_att ON src_att.attrelid = src.oid AND src_att.attnum = ord.attnum
            JOIN pg_attribute dst_att ON dst_att.attrelid = dst.oid AND dst_att.attnum = con.confkey[ord.ordinality]
            WHERE con.contype = 'f'
              AND src_ns.nspname = ANY(%s)
              AND dst_ns.nspname = ANY(%s)
            GROUP BY con.conname, src_ns.nspname, src.relname, dst_ns.nspname, dst.relname
            ORDER BY src_ns.nspname, src.relname, con.conname
            """,
            (list(included_schemas), list(included_schemas)),
        )
    ]
    indexes = [
        Index(
            table_schema=row["table_schema"],
            table_name=row["table_name"],
            index_name=row["index_name"],
            index_definition=row["index_definition"],
        )
        for row in fetch_all(
            conn,
            """
            SELECT schemaname AS table_schema, tablename AS table_name,
                   indexname AS index_name, indexdef AS index_definition
            FROM pg_indexes
            WHERE schemaname = ANY(%s)
            ORDER BY schemaname, tablename, indexname
            """,
            schema_params,
        )
    ]
    bridge_columns = [
        asdict(column)
        for column in columns
        if column.column_name in {"prom_law_nm", "prom_no", "promulgation_dt"}
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "connection_identity": identity,
        "included_schemas": list(included_schemas),
        "schemas": schemas,
        "tables": tables,
        "columns": [asdict(column) for column in columns],
        "foreign_keys": [asdict(fk) for fk in foreign_keys],
        "indexes": [asdict(index) for index in indexes],
        "promulgation_bridge_columns": bridge_columns,
    }


def render_markdown(data: dict[str, Any]) -> str:
    table_counts: dict[str, int] = {}
    for table in data["tables"]:
        table_counts[table["table_schema"]] = table_counts.get(table["table_schema"], 0) + 1

    lines: list[str] = []
    lines.append("# congress-db Live Schema Introspection")
    lines.append("")
    lines.append(f"Generated at: `{data['generated_at']}`")
    lines.append("")
    lines.append("## Connection")
    lines.append("")
    identity = data["connection_identity"]
    lines.append(f"- Current user: `{identity['current_user']}`")
    lines.append(f"- Session user: `{identity['session_user']}`")
    lines.append(f"- Transaction read-only: `{identity['transaction_read_only']}`")
    lines.append(f"- Server in recovery: `{identity['server_in_recovery']}`")
    lines.append(f"- Included schemas: `{', '.join(data.get('included_schemas', []))}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Schemas: {len(data['schemas'])}")
    lines.append(f"- Tables/views/materialized views: {len(data['tables'])}")
    lines.append(f"- Columns: {len(data['columns'])}")
    lines.append(f"- Foreign keys: {len(data['foreign_keys'])}")
    lines.append(f"- Indexes: {len(data['indexes'])}")
    lines.append("")
    lines.append("## Tables By Schema")
    lines.append("")
    lines.append("| Schema | Relation Count |")
    lines.append("|---|---:|")
    for schema, count in sorted(table_counts.items()):
        lines.append(f"| `{schema}` | {count} |")
    lines.append("")
    lines.append("## Promulgation Bridge Columns")
    lines.append("")
    if data["promulgation_bridge_columns"]:
        lines.append("| Table | Column | Type | Nullable | Comment |")
        lines.append("|---|---|---|---|---|")
        for column in data["promulgation_bridge_columns"]:
            table = f"{column['table_schema']}.{column['table_name']}"
            comment = (column.get("comment") or "").replace("|", "\\|")
            lines.append(
                f"| `{table}` | `{column['column_name']}` | `{column['data_type']}` | {column['is_nullable']} | {comment} |"
            )
    else:
        lines.append("No `prom_law_nm`, `prom_no`, or `promulgation_dt` columns were found.")
    lines.append("")
    lines.append("## Relations")
    lines.append("")
    lines.append("| Type | Name | Columns / Detail |")
    lines.append("|---|---|---|")
    for table in data["tables"]:
        name = f"{table['table_schema']}.{table['table_name']}"
        comment = (table.get("comment") or "").replace("|", "\\|")
        lines.append(f"| {table['table_type']} | `{name}` | {comment} |")
    lines.append("")
    lines.append("## Foreign Keys")
    lines.append("")
    if data["foreign_keys"]:
        lines.append("| Constraint | From | To |")
        lines.append("|---|---|---|")
        for fk in data["foreign_keys"]:
            src = f"{fk['table_schema']}.{fk['table_name']}({', '.join(fk['column_names'])})"
            dst = f"{fk['foreign_table_schema']}.{fk['foreign_table_name']}({', '.join(fk['foreign_column_names'])})"
            lines.append(f"| `{fk['constraint_name']}` | `{src}` | `{dst}` |")
    else:
        lines.append("No foreign keys found.")
    lines.append("")
    return "\n".join(lines)


def load_env_local(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path(".env.local"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--schema",
        action="append",
        default=None,
        help="Schema to introspect. Defaults to public; pass more than once to include multiple schemas.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_local(args.env_file)
    dsn = os.environ.get("CONGRESS_DB_READONLY_URL")
    if not dsn:
        raise SystemExit(
            "Missing CONGRESS_DB_READONLY_URL. Add the congress_ro Neon connection string to .env.local."
        )

    ensure_psycopg()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    included_schemas = tuple(args.schema or DEFAULT_SCHEMAS)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SET default_transaction_read_only = on")
        data = introspect(conn, included_schemas=included_schemas)

    (args.output_dir / "schema.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8",
    )
    (args.output_dir / "README.md").write_text(render_markdown(data), encoding="utf-8")
    print(f"Wrote {args.output_dir / 'README.md'}")
    print(f"Wrote {args.output_dir / 'schema.json'}")


if __name__ == "__main__":
    main()
