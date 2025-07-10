import enum


class PluslifeDeviceStatus(enum.Enum):
    READY = 0
    STARTED = 1
    ALREADY_RUNNING = 2
    NOT_READY = 3
    ABNORMAL = 4
    UNSUPPORTED_TEST = 5


class PluslifeTestState(enum.Enum):
    UNINITIALIZED = 0
    IDLE = 1
    TESTING = 2
    DONE = 3
    BLOCKED_ALREADY_TESTING = 4
    BLOCKED_NOT_READY = 5


class PluslifeDetectionResult(enum.Enum):
    NEGATIVE = 1
    POSITIVE = 2
    INVALID = 3


PluslifeTestType = enum.Enum("PluslifeTestType", {"Unknown": 0, "SARS-CoV-2": 1})


class PluslifeWebhookEvent(enum.Enum):
    TEST_STARTED = enum.auto()
    CONTINUE_TEST = enum.auto()
    TEST_FINISHED = enum.auto()
    NEW_DATA = enum.auto()
    DEVICE_READY = enum.auto()
    ALREADY_TESTING = enum.auto()
