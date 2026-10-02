from dataclasses import dataclass

@dataclass
class OperationResult:
    success: bool
    rows_processed: int = 0
    message: str = ""

@dataclass
class FileLoadResult(OperationResult):
    files_processed: int = 0