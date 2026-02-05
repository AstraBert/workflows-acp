import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from workflows_acp.tools.agentfs import load_all_files

from llamagram.constants import DEFAULT_TO_AVOID, DEFAULT_TO_AVOID_FILES
from llamagram.tools.llamacloud import (
    _download_file_to_agentfs,
    _read_file_from_agentfs,
    classify_file,
    extract_structured_data_from_file,
    parse_file_content,
)

from .conftest import CacheMock, LlamaCloudMock


@pytest.mark.asyncio
async def test_agentfs_utilities_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    (tmp_path / ".env.local").write_text("Bye world")
    (tmp_path / ".npmrc").write_text("secret token")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    content = await _read_file_from_agentfs("test.txt")
    assert content.decode("utf-8") == "Hello world"
    with pytest.raises(FileNotFoundError):
        await _read_file_from_agentfs(".env.local")
    with pytest.raises(FileNotFoundError):
        await _read_file_from_agentfs(".npmrc")


@pytest.mark.asyncio
async def test_agentfs_utilities_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    await _download_file_to_agentfs("test1.txt", "Bye Mars".encode("utf-8"))
    # file does not exist on real FS
    assert not (tmp_path / "test1.txt").is_file()
    content = await _read_file_from_agentfs("test1.txt")
    assert content.decode("utf-8") == "Bye Mars"
    # test you can overwrite
    await _download_file_to_agentfs("test.txt", "Greetings Moon".encode("utf-8"))
    # verify no changes on real FS
    assert (tmp_path / "test.txt").read_text() == "Hello world"
    content = await _read_file_from_agentfs("test.txt")
    assert content.decode("utf-8") == "Greetings Moon"


@pytest.mark.asyncio
async def test_parse_file_content_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    with patch(
        "llamagram.tools.llamacloud.get_client", new_callable=Mock
    ) as mock_get_client:
        with patch(
            "llamagram.tools.llamacloud.get_cache", new_callable=Mock
        ) as mock_get_cache:
            mock_llama_cloud = LlamaCloudMock()
            mock_get_client.return_value = mock_llama_cloud
            mock_get_cache.return_value = CacheMock()
            result = await parse_file_content("test.txt")
            assert result == mock_llama_cloud.parsing._default_text


@pytest.mark.asyncio
async def test_parse_file_content_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    with patch(
        "llamagram.tools.llamacloud.get_client", new_callable=Mock
    ) as mock_get_client:
        with patch(
            "llamagram.tools.llamacloud.get_cache", new_callable=Mock
        ) as mock_get_cache:
            mock_llama_cloud = LlamaCloudMock(should_fail=True)
            mock_get_client.return_value = mock_llama_cloud
            mock_get_cache.return_value = CacheMock()
            result = await parse_file_content("test.txt")
            assert (
                result
                == f"It was not possible to parse the content of test.txt: {mock_llama_cloud.parsing._default_error_message}"
            )


@pytest.mark.asyncio
async def test_extract_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    with patch(
        "llamagram.tools.llamacloud.get_client", new_callable=Mock
    ) as mock_get_client:
        mock_llama_cloud = LlamaCloudMock()
        mock_get_client.return_value = mock_llama_cloud
        result = await extract_structured_data_from_file("test.txt", {})
        assert result == json.dumps(mock_llama_cloud.extraction._default_data, indent=2)


@pytest.mark.asyncio
async def test_extract_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    with patch(
        "llamagram.tools.llamacloud.get_client", new_callable=Mock
    ) as mock_get_client:
        mock_llama_cloud = LlamaCloudMock(should_fail=True)
        mock_get_client.return_value = mock_llama_cloud
        result = await extract_structured_data_from_file("test.txt", {})
        assert result == "No extraction data were produced for test.txt"


@pytest.mark.asyncio
async def test_classify_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    with patch(
        "llamagram.tools.llamacloud.get_client", new_callable=Mock
    ) as mock_get_client:
        mock_llama_cloud = LlamaCloudMock()
        mock_get_client.return_value = mock_llama_cloud
        result = await classify_file("test.txt", [], [])
        assert (
            result
            == f"File test.txt was classified as {mock_llama_cloud.classifier._default_category} because of the following reasons: Lorem ipsum dolor"
        )


@pytest.mark.asyncio
async def test_classify_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("Hello world")
    await load_all_files(
        to_avoid_dirs=DEFAULT_TO_AVOID,
        to_avoid_files=DEFAULT_TO_AVOID_FILES,
    )
    with patch(
        "llamagram.tools.llamacloud.get_client", new_callable=Mock
    ) as mock_get_client:
        mock_llama_cloud = LlamaCloudMock(should_fail=True)
        mock_get_client.return_value = mock_llama_cloud
        result = await classify_file("test.txt", [], [])
        assert result == "No classification result was produced for test.txt"
