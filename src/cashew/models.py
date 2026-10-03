from dataclasses import dataclass

@dataclass
class OperationResult:
    success: bool
    rows_processed: int = 0
    message: str = ""

@dataclass
class SQLiteLoadResult(OperationResult):
    tables_processed: int = 0