import enum

class TaskState(enum.Enum):
    queued = 1
    processing = 2
    failed = 3
    completed = 4

