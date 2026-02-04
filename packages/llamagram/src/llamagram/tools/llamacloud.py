import functools
import json
import mimetypes
import os
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from llama_cloud import AsyncLlamaCloud
from llama_cloud.types.classifier.classifier_rule_param import ClassifierRuleParam
from llama_cloud.types.extraction import ExtractConfigParam
from workflows_acp.models import Tool
from workflows_acp.tools.agentfs import _is_accessible_path, configure_agentfs
from workflows_acp.tools.definitions import AGENTFS_TOOLS


@functools.lru_cache(maxsize=1)
def get_client() -> AsyncLlamaCloud:
    load_dotenv()
    return AsyncLlamaCloud(api_key=os.getenv("LLAMA_CLOUD_API_KEY"))


async def _read_file_from_agentfs(file_path: str) -> bytes:
    """
    Read and return the contents of a file.

    Args:
        file_path (str): Path to the file.
    Returns:
        str: File contents or an error message if the file does not exist.
    """
    file_path = str(Path(file_path).resolve())
    agentfs = await configure_agentfs()
    if not await _is_accessible_path(agentfs, file_path, "file"):
        raise FileNotFoundError(f"no such file or directory: {file_path}")
    content = await agentfs.fs.read_file(file_path, encoding=None)
    return content if isinstance(content, bytes) else content.encode("utf-8")


async def _upload_file(
    file_path: str,
    purpose: Literal["parse", "classify", "extract", "sheet", "split", "agent_app"],
) -> str:
    data_type, _ = mimetypes.guess_type(file_path)
    file_content = await _read_file_from_agentfs(file_path)
    file_to_upload = (
        file_path,
        file_content,
        data_type,
    )
    client = get_client()
    file_obj = await client.files.create(
        file=file_to_upload,
        purpose=purpose,
    )
    return file_obj.id


async def parse_file_content(file_path: str) -> str:
    try:
        file_id = await _upload_file(file_path, "parse")
    except FileNotFoundError:
        return f"No such file: {file_path}"
    client = get_client()
    result = await client.parsing.parse(
        tier="fast", version="latest", file_id=file_id, expand=["text"]
    )
    if result.job.status in ("FAILED", "CANCELLED") or result.text is None:
        return f"It was not possible to parse the content of {file_path}: {result.job.error_message}"
    return "\n\n".join([page.text for page in result.text.pages])


async def extract_structured_data_from_file(
    file_path: str,
    json_schema: Annotated[
        dict[str, Any],
        "Valid JSON schema that represents the structure with which the data in the file should be represented. Eversy field of the JSOn schema should be nullable and required",
    ],
) -> str:
    try:
        file_id = await _upload_file(file_path, "extract")
    except FileNotFoundError:
        return f"No such file: {file_path}"
    client = get_client()
    result = await client.extraction.extract(
        data_schema=json_schema,
        file_id=file_id,
        config=ExtractConfigParam(extraction_mode="FAST"),
    )
    if result.data is None:
        return f"No extraction data were produced for {file_path}"
    return json.dumps(result.data)


async def classify_file(
    file_path: str,
    categories: Annotated[
        list[str], "List of categories that the file can be classified as"
    ],
    descriptions: Annotated[
        list[str],
        "List of description for each category (should appear in the same order)",
    ],
) -> str:
    classify_rules = [
        ClassifierRuleParam(type=categories[i], description=descriptions[i])
        for i in range(len(descriptions))
    ]
    try:
        file_id = await _upload_file(file_path, "classify")
    except FileNotFoundError:
        return f"No such file: {file_path}"
    client = get_client()
    result = await client.classifier.classify(
        file_ids=[file_id],
        rules=classify_rules,
    )
    class_result = result.items[0].result
    if class_result is None:
        return f"No classification result was produced for {file_path}"
    return f"File {file_path} was classified as {class_result.type or 'unclassified'} because of the following reasons: {class_result.reasoning}"


parse_file_content_tool = Tool(
    name="parse_file_content",
    description="Parse an unstructured file (PDF, presentation, Word document) and get its content as plain text.",
    fn=parse_file_content,
)

extract_structured_data_from_file_tool = Tool(
    name="extract_structured_data_from_file",
    description="Extract structured data (following a given JSON schema) from an unstructured file.",
    fn=extract_structured_data_from_file,
)

classify_file_tool = Tool(
    name="classify_file",
    description="Classify an unstructured file, provided a list of categories and their associated descriptions",
    fn=classify_file,
)

TOOLS = AGENTFS_TOOLS + [
    parse_file_content_tool,
    extract_structured_data_from_file_tool,
    classify_file_tool,
]
