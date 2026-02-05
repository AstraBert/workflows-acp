from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from llama_cloud.types.parsing_get_response import Text, TextPage
from workflows.events import Event
from workflows_acp.events import (
    OutputEvent,
    PromptEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
)


@dataclass
class Job:
    status: str = "COMPLETED"
    error_message: str | None = None


@dataclass
class ClassifyOutput:
    type: str
    reasoning: str = "Lorem ipsum dolor"


@dataclass
class ClassifyItem:
    result: ClassifyOutput | None


@dataclass
class ParsingResult:
    text: Text | None
    job: Job = field(default_factory=Job)


@dataclass
class ExtractResult:
    data: dict[str, Any] | None


@dataclass
class ClassifyResult:
    items: list[ClassifyItem]


@dataclass
class FileResult:
    id: str


@dataclass
class TelegramUserMock:
    username: str | None


@dataclass
class TelegramDocumentMock:
    file_name: str | None
    file_id: str


class ParsingMock:
    def __init__(self, should_fail: bool) -> None:
        self.should_fail = should_fail
        self._default_text = "Lorem ipsum dolor"
        self._default_error_message = "Could not complete job"

    async def parse(self, *args, **kwargs) -> ParsingResult:
        if self.should_fail:
            return ParsingResult(
                text=None,
                job=Job(status="FAILED", error_message=self._default_error_message),
            )
        return ParsingResult(
            text=Text(pages=[TextPage(text=self._default_text, page_number=0)])
        )


class ExtractionMock:
    def __init__(self, should_fail: bool) -> None:
        self.should_fail = should_fail
        self._default_data = {"content": "Lorem ipsum dolor"}

    async def extract(self, *args, **kwargs) -> ExtractResult:
        if self.should_fail:
            return ExtractResult(data=None)
        return ExtractResult(data=self._default_data)


class ClassifierMock:
    def __init__(self, should_fail: bool) -> None:
        self.should_fail = should_fail
        self._default_category = "categorized"

    async def classify(self, *args, **kwargs) -> ClassifyResult:
        if self.should_fail:
            return ClassifyResult(items=[ClassifyItem(result=None)])
        return ClassifyResult(
            items=[ClassifyItem(result=ClassifyOutput(type=self._default_category))]
        )


class FilesMock:
    def __init__(self) -> None:
        self._default_id = "file-id-test"

    async def create(self, *args, **kwargs) -> FileResult:
        return FileResult(id=self._default_id)


class LlamaCloudMock:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    @property
    def parsing(self) -> ParsingMock:
        return ParsingMock(self.should_fail)

    @property
    def extraction(self) -> ExtractionMock:
        return ExtractionMock(self.should_fail)

    @property
    def classifier(self) -> ClassifierMock:
        return ClassifierMock(self.should_fail)

    @property
    def files(self) -> FilesMock:
        return FilesMock()


class CacheMock:
    async def get(self, *args, **kwargs) -> None:
        return None

    async def set(self, *args, **kwargs) -> None:
        return None


class TelegramFileMock:
    async def download_as_bytearray(self, *args, **kwargs) -> bytearray:
        return bytearray("Hello world".encode("utf-8"))


class TelegramBotMock:
    def __init__(self, should_fail: bool):
        self.should_fail = should_fail

    async def get_file(self, *args, **kwargs) -> TelegramFileMock:
        if self.should_fail:
            raise FileNotFoundError("file not found")
        return TelegramFileMock()


class TelegramCallBackContextMock:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    @property
    def bot(self) -> TelegramBotMock:
        return TelegramBotMock(should_fail=self.should_fail)


class WorkflowHandlerMock:
    def __init__(self, *args, **kwargs) -> None:
        self._events: list[Event] = [
            ThinkingEvent(content="thought"),
            ToolCallEvent(tool_name="say_hello", tool_input={}),
            ToolResultEvent(tool_name="say_hello", result="hello"),
            PromptEvent(prompt="we are done"),
            OutputEvent(stop_reason="done", final_output="hello", error=None),
        ]
        self._output_event = OutputEvent(stop_reason="done", final_output="hello")
        self._log_file = "app.log"

    async def stream_events(self, *args, **kwargs) -> AsyncGenerator[Event, Any]:
        for event in self._events:
            with open(self._log_file, "a") as f:
                ev_type = event.__repr_name__().split(".")[-1]
                f.write(ev_type + "\n")
            yield event

    def __await__(self):
        async def _init():
            # Put any async initialization here
            return self._output_event

        return _init().__await__()


class AgentWorkflowMock:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def run(self, *args, **kwargs) -> WorkflowHandlerMock:
        return WorkflowHandlerMock()
