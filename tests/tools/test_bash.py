import re

from workflows_acp.tools.bash import execute_command, bash_output


def test_bash_tools() -> None:
    result = execute_command(command="echo", args=["'hello world'"])
    assert (
        result
        == "Running command echo with arguments: ''hello world'' produced the following stdout:\n\n```text\n'hello world'\n\n```\n\nAnd the following stderr:\n\n```text\n\n```"
    )
    result = execute_command(command="echo", args=["'hello world'"], wait=False)
    assert result.startswith("Process ID: ") and result.endswith(
        "(use it to retrieve the result with the `bash_output` tool later)"
    )
    pid: str | int = re.findall(
        r"^Process ID: (\d+) \(use it to retrieve the result with the `bash_output` tool later\)$",
        result,
    )[0]
    pid = int(pid)
    output = bash_output(pid)
    assert (
        output
        == f"Process {pid} produced the following stdout:\n\n```text\n'hello world'\n\n```\n\nAnd the following stderr:\n\n```text\n\n```"
    )
