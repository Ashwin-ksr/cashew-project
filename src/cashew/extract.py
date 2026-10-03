import logging
import pandas as pd
from psycopg import Connection, sql
import sqlite3
from cashew.config import DATA_FOLDER_PATH, LOG_FORMAT
from cashew.database import pool
from cashew.models import OperationResult

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)

def get_new_db_files(conn: Connection) -> list[str]:
    """Return DB files in the landing folder that are not yet in the database."""

    with conn.cursor() as cur:
        # gets db files already loaded in database
        cur.execute(
            """
            SELECT "file_name" 
            FROM   "raw"."loaded_files"
            WHERE  "__is_active" = TRUE
            """
        )
        files: set[str] = {row[0] for row in cur.fetchall()}

    # gets db files present in landing zone
    landing_path = DATA_FOLDER_PATH / "landing"
    files_in_landing = {file.name for file in landing_path.iterdir() if file.is_file() and file.name.endswith(".sql")}
    
    new_files = list(files_in_landing - files)
    logger.info(
        "Found a total of %d file(s) of which %d file(s) are new",
        len(files_in_landing),
        len(new_files)
    )

    return new_files

def get_sqlite_tables_list(db_file_name: str) -> list[str]:
    """Return a list of table names in the given SQLite database file.

    Args:
        conn: psycopg connection to the PostgreSQL database.
        db_file_name: Name of the SQLite database file located in the
            landing data directory.

    Returns:
        A list containing the names of all tables in the SQLite database.

    Raises:
        sqlite3.Error: If an error occurs while connecting to or querying
            the SQLite database.
        KeyError: If the query result does not contain the expected
            ``name`` column.
    """
    db_path = DATA_FOLDER_PATH / "landing" / db_file_name
    conn = sqlite3.connect(db_path)

    try:
        tables_df = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """,
            con=conn,
        )
    finally:
        conn.close()

    tables: list[str] = tables_df["name"].to_list()

    logger.info(
        "Found a total of %d table(s) in db %s",
        len(tables),
        db_file_name,
    )

    return tables

def find_existing_tables(
    conn: Connection, 
    tables_list: list[str], 
    table_schema: str = "raw"
) -> list[tuple[str, bool]]:
    """
    Check which of the specified tables exist in the PostgreSQL raw schema.

    Queries the information schema for the provided table names and returns
    the existence status of each table.

    Args:
        conn: Active PostgreSQL database connection.
        tables_list: List of table names to check in the given schema.
        table_schema: Schema the functions needs to check for the tables 'raw' by default.

    Returns:
        A list of tuples containing each table name and a boolean indicating
        whether the table exists in the raw schema.

    Raises:
        Exception: If the database query fails.
    """

    try:
        with conn.cursor() as curr:
            query = """
                SELECT "table_name"
                FROM "information_schema"."tables"
                WHERE "table_schema" = %s
                    AND "table_name" = ANY(%s)
            """

            curr.execute(query,(table_schema, tables_list))

            existing_tables: set[str] = {
                row[0]
                for row in curr.fetchall()
            }

            table_list = [
                (table, table in existing_tables)
                for table in tables_list
            ]

            logger.info(
                "Found a total of %d table(s) already present in the %s schema",
                len(existing_tables),
                table_schema,
            )

            return table_list

    except Exception:
        logger.exception("Failed to check existing tables in %s schema", table_schema)
        raise

def copy_sqlite_table_to_raw(
    conn: Connection,
    db_file_name: str,
    table_name: str,
    is_table_present: bool,
) -> OperationResult:

    db_file_path = DATA_FOLDER_PATH / "landing" / db_file_name

    try:
        with sqlite3.connect(db_file_path) as sqlite_conn:
            with conn.cursor() as curr:
                sqlite_table_df = pd.read_sql_query(
                    f'SELECT * FROM "{table_name}"',
                    con=sqlite_conn,
                )
                columns: list[str] = sqlite_table_df.columns.to_list()

                if is_table_present:
                    # truncate the table if it is present to load all new data
                    truncate_table_query = sql.SQL("""
                        TRUNCATE TABLE "raw".{}
                    """).format(
                        sql.Identifier(table_name)
                    )

                    curr.execute(truncate_table_query)

                else:
                    # create a new table if it is not present
                    column_identifiers = sql.SQL(", ").join(
                        sql.SQL("{} TEXT").format(
                            sql.Identifier(column) 
                            for column in columns
                        )
                    )

                    create_table_query = sql.SQL(
                        """
                        CREATE TABLE "raw".{} (
                            {}
                        )
                        """
                    ).format(sql.Identifier(table_name), column_identifiers)

                    create_query_result = curr.execute(create_table_query)

            # copy the table from sqlite to pSQL as CSV
            column_identifiers = sql.SQL(", ").join(
                sql.Identifier(column)
                for column in columns
            )

            # Build copy query
            copy_query = sql.SQL("""
                COPY "raw".{} ({})
                FROM STDIN
                WITH (FORMAT CSV)
            """).format(sql.Identifier(table_name), column_identifiers)

            # Copy file into database
            with curr.copy(copy_query) as copy:
                copy.write(
                    sqlite_table_df[columns].to_csv(
                        index=False,
                        header=False,
                    )
                )
            
            return OperationResult(
                success=True,
                rows_processed=len(sqlite_table_df),
                message=f'Successfully copied table "{table_name}".',
            )

    except Exception as e:
        logger.exception(
            'Failed to copy SQLite table "%s" to raw schema',
            table_name,
        )

        return OperationResult(
            success=False,
            rows_processed=0,
            message=str(e),
        )

pool.close()