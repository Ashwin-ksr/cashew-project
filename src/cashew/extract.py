import os
import logging
import pandas as pd
from psycopg import sql
import re
from typing import List
from cashew.config import DATA_FOLDER_PATH, LOG_FORMAT
from cashew.database import pool
from cashew.models import FileLoadResult

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)

def get_new_files() -> List[str]:
    """Return CSV files in the landing folder that are not yet in the database."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            # gets csv files already loaded in database
            cur.execute(
                """
                SELECT DISTINCT 
                    "__file_name" 
                FROM 
                    "raw"."transactions"
                """
            )
            files: set[str] = {row[0] for row in cur.fetchall()}

    # gets csv files present in lading zone
    landing_path = DATA_FOLDER_PATH / "landing"
    files_in_landing = {file.name for file in landing_path.iterdir() if file.is_file() and file.name.endswith(".csv")}
    
    new_files = list(files_in_landing - files)
    logger.info(
        "Found a total of %d file(s) of which %d file(s) are new",
        len(files_in_landing),
        len(new_files)
    )

    return new_files

def load_transactions_into_db(files: List[str]) -> FileLoadResult:
    """
    Load transaction CSV files from the landing folder into the raw
    transactions table in PostgreSQL.

    Each CSV file is read into a pandas DataFrame, tagged with its source
    filename, and loaded into PostgreSQL using the COPY command for efficient
    bulk insertion.

    Args:
        files: List of CSV filenames located in the landing folder.

    Returns:
        FileLoadResult containing the load status, number of files processed,
        number of rows processed, and a descriptive message.

    Raises:
        No exceptions are raised directly. Any exception encountered during
        file reading or database loading is logged and returned as a failed
        FileLoadResult.
    """

    files_processed = 0
    rows_processed = 0

    try:
        with pool.connection() as conn:
            with conn.cursor() as curr:
                for file in files:
                    logger.info("Loading file: %s", file)

                    # Get absolute path of each file and load into DataFrame
                    file_path = DATA_FOLDER_PATH / "landing" / file
                    df = pd.read_csv(file_path)

                    logger.info("Read %d rows from %s", len(df), file)

                    # Add file name column to write to DB
                    df["__file_name"] = file

                    # Builds the list of column identifiers by convertning spaces into "_" from DataFrame column names
                    df.columns = df.columns.str.replace(r"\s+", "_", regex=True)
                    columns = df.columns.tolist()

                    column_identifiers = sql.SQL(", ").join(
                        sql.Identifier(column)
                        for column in columns
                    )

                    # Build COPY query
                    query = sql.SQL("""
                        COPY "raw"."transactions" ({})
                        FROM STDIN
                        WITH (FORMAT CSV)
                    """).format(column_identifiers)

                    # Copy file into database
                    with curr.copy(query) as copy:
                        copy.write(
                            df[columns].to_csv(
                                index=False,
                                header=False,
                            )
                        )

                    files_processed += 1
                    rows_processed += len(df)

                    logger.info(
                        "Successfully loaded %d rows from %s",
                        len(df),
                        file,
                    )

        return FileLoadResult(
            success=True,
            rows_processed=rows_processed,
            files_processed=files_processed,
            message="Transactions loaded successfully into Database successfully.",
        )

    except Exception as e:
        logger.exception("Failed to load transactions")

        return FileLoadResult(
            success=False,
            rows_processed=rows_processed,
            files_processed=files_processed,
            message=str(e),
        )

pool.close()