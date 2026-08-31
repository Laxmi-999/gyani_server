import enum

class OCRStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"  # Changed to lowercase to stay consistent
    FAILED = "failed"