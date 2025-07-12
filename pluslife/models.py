import datetime
import os

from .enums import PluslifeDetectionResult, PluslifeTestType, PluslifeWebhookEvent, PluslifeTestState


class PluslifeTemperatureSample:
    time: datetime.datetime
    temp: float

    def __init__(self, data: dict):
        self.time = (
            datetime.datetime.fromisoformat(data.get("time")) if type(data.get("time")) is str else data.get("time")
        )
        self.temp = data.get("temp")

    def __eq__(self, other):
        return self.time == other.time and self.temp == other.temp

    def to_json(self) -> dict:
        return {"time": self.time.isoformat(timespec="milliseconds").replace("+00:00", "Z"), "temp": self.temp}


class PluslifeSample:
    startingChannel: int
    samplingTime: int
    samplingTemperature: float
    firstChannelResult: int

    sampleType: PluslifeTestType = PluslifeTestType["SARS-CoV-2"]
    sampleStreamNumber: int = 0
    currentDataIndex: int = 0
    totalNumberOfSamples: int = 1
    numberOfChannels: int = 1

    def __init__(self, data: dict):
        for key, value in data.items():
            if key == "sampleType":
                value = PluslifeTestType(value)
            setattr(self, key, value)

    def __eq__(self, other):
        return self.to_json() == other.to_json()

    def to_json(self) -> dict:
        return_value = {}
        for key, value in self.__dict__.items():
            if type(value) is PluslifeTestType:
                value = value.value
            return_value[key] = value

        return return_value

    def to_minimal_json(self) -> dict:
        return {
            "time": self.samplingTime,
            "channel": self.startingChannel,
            "value": self.firstChannelResult,
            "temperature": self.samplingTemperature,
        }

    def to_csv_line(self):
        return ";".join(
            map(str, [self.samplingTime, self.startingChannel, self.firstChannelResult, self.samplingTemperature])
        )

    @staticmethod
    def from_csv_line(line) -> "PluslifeSample":
        data = line.split(";")
        return PluslifeSample(
            {
                "samplingTime": float(data[0]),
                "startingChannel": int(data[1]),
                "firstChannelResult": int(data[2]),
                "samplingTemperature": float(data[3]),
            }
        )

    def __str__(self):
        return (
            f"channel: {self.startingChannel} time: {self.samplingTime / 10:.0f}s"
            f" ({self.samplingTime / 600:.1f}min),"
            f"Temperature: {self.samplingTemperature / 100.0:.1f}°C,"
            f"Value: {self.firstChannelResult * 64}"
        )


class PluslifeResult:
    detectionType: PluslifeTestType
    detectionFlowNumber: int
    detectionResult: PluslifeDetectionResult
    numberOfChannels: int
    startingChannel: int
    channelResults: list[PluslifeDetectionResult]
    numberOfSubGroups: int
    subGroupResults: list[PluslifeDetectionResult]

    def __init__(self, data: dict):
        for key, value in data.items():
            if key == "detectionType":
                value = PluslifeTestType(value)
            if key == "detectionResult":
                value = PluslifeDetectionResult(value)
            if key == "channelResults":
                value = [PluslifeDetectionResult(r) for r in value]
            if key == "subGroupResults":
                value = [PluslifeDetectionResult(sr) for sr in value]
            setattr(self, key, value)

    def to_json(self) -> dict:
        return_value = {}
        for key, value in self.__dict__.items():
            if type(value) in [PluslifeTestType, PluslifeDetectionResult]:
                value = value.value
            if key in ["channelResults", "subGroupResults"]:
                value = [cr.value for cr in value]
            return_value[key] = value

        return return_value

    def get_human_readable_data(self) -> dict:
        return {
            "channels": {i: res.name for i, res in enumerate(self.channelResults)},
            "result": self.detectionResult.name,
        }


class PluslifeTestrun:
    CHANNELS = 7
    version: int
    id: str
    start: datetime.datetime
    testType: PluslifeTestType
    targetTemp: int
    comment: str
    temperatureSamples: list[PluslifeTemperatureSample] = []
    samples: list[PluslifeSample] = []
    testResult: PluslifeResult | None = None

    def __init__(self, data: dict, start: datetime.datetime = None, comment: str = ""):
        self.id = data.get("id", self.get_uuid())
        self.testType = PluslifeTestType[data.get("testType", "Unknown")]
        self.targetTemp = data.get("targetTemp", 63)
        self.version = data.get("version", 0)

        for temperature_sample in data.get("testData", {}).get("temperatureSamples", []):
            self.temperatureSamples.append(PluslifeTemperatureSample(temperature_sample))
        for sample in data.get("testData", {}).get("samples", []):
            self.samples.append(PluslifeSample(sample))

        result_data = data.get("testResult")
        if result_data:
            self.testResult = PluslifeResult(result_data)

        self.comment = comment
        if start:
            self.start = start
        elif self.temperatureSamples:
            self.start = min(self.temperatureSamples, key=lambda t: t.time).time
        else:
            self.start = datetime.datetime.now(tz=datetime.UTC)

    @staticmethod
    def get_uuid():
        random = bytearray(os.urandom(16))
        random[6] = (random[6] & 0x0F) | 0x40
        random[8] = (random[8] & 0x3F) | 0x80
        h = random.hex()
        return "-".join((h[0:8], h[8:12], h[12:16], h[16:20], h[20:32]))

    def to_json(self) -> dict:
        return {
            "version": self.version,
            "id": self.id,
            "testType": self.testType.name,
            "targetTemp": self.targetTemp,
            "testData": {
                "temperatureSamples": [ts.to_json() for ts in self.temperatureSamples],
                "samples": [s.to_json() for s in self.samples],
            },
            "testResult": self.testResult.to_json() if self.testResult else {},
        }

    def to_minimal_json(self) -> dict:
        return {
            "start": self.start.strftime("%s"),
            "type": self.testType.value,
            "samples": [s.to_minimal_json() for s in self.samples],
            "result": self.testResult.to_json(),
        }

    def is_finished(self) -> bool:
        return self.testResult is not None

    def has_all_data_for_current_time(self) -> bool:
        newest_sample = max(self.samples, key=lambda s: s.samplingTime)
        return len([s for s in self.samples if s.samplingTime == newest_sample.samplingTime]) == self.channel_count

    @property
    def channel_count(self) -> int:
        return max(self.samples, key=lambda s: s.startingChannel).startingChannel if self.samples else 0

    @property
    def latest_sampletime(self) -> int:
        return max(self.samples, key=lambda s: s.samplingTime).samplingTime if self.samples else 0

    def get_current_human_readable_state(self) -> str:
        channels = self.get_latest_points()
        if channels:
            current_test_time = max(channels.values(), key=lambda p: p[0])[0]
            fstring_concat_workaround = ", ".join([f"{i}:{channels.get(i, '___')[1]:>5}" for i in range(self.CHANNELS)])
            return f"{current_test_time/60:.1f}min: {fstring_concat_workaround}"
        else:
            return f"{datetime.datetime.now() - self.start}: Waiting for first Data..."

    def get_latest_points(self) -> dict[int : tuple[float, float]]:
        amount_of_channels = self.channel_count
        channels = {}
        for sample in reversed(self.samples):
            if sample.startingChannel not in channels:
                channels[sample.startingChannel] = (sample.samplingTime, sample.firstChannelResult)
            if len(channels) == amount_of_channels:
                break
        return channels


class PluslifeWebhook:
    version: int
    event: PluslifeWebhookEvent
    serial_number: int
    device: dict
    state: PluslifeTestState
    result: PluslifeResult | None
    temperatureSamples: list[PluslifeTemperatureSample] = []
    samples: list[PluslifeSample] = []
    data: dict

    def __init__(self, data: dict):
        self.data = data.copy()
        self.version = data.get("version")
        self.event = PluslifeWebhookEvent[data.get("event")]
        self.serial_number = data.get("device", {}).get("sn")
        self.state = PluslifeTestState[data.get("test", {}).get("state")]
        result_data = data.get("test", {}).get("result", {}).copy()
        if result_data:
            result_data["detectionResult"] = PluslifeDetectionResult[result_data["detectionResult"]].value
            result_data["channelResults"] = [PluslifeDetectionResult[c].value for c in result_data["channelResults"]]
            result_data["subGroupResults"] = [
                PluslifeDetectionResult[c.get("result")].value for c in result_data["subGroupResults"]
            ]
            self.result = PluslifeResult(result_data)
        self.temperatureSamples = [
            PluslifeTemperatureSample(t) for t in data.get("test", {}).get("data", {}).get("temperatureSamples", [])
        ]
        self.samples = [PluslifeSample(s) for s in data.get("test", {}).get("data", {}).get("samples", [])]

    def __str__(self):
        return f"SN {self.serial_number}: {self.event}"

    @property
    def latest_sampletime(self) -> int:
        return max(self.samples, key=lambda s: s.samplingTime).samplingTime if self.samples else 0
