import subprocess as sp
import psutil
import tempfile
import os

from typing_extensions import TypedDict


class Process(TypedDict):
    """
    Represents the file paths for stdout and stderr of a process.
    """

    stdout_path: str
    stderr_path: str


class BashTracer:
    """
    Tracks background bash processes and their output files.
    """

    def __init__(self) -> None:
        """
        Initialize the BashTracer with an empty process dictionary.
        """
        self._processes: dict[int, Process] = {}

    def register_process(self, pid: int, stdout_path: str, stderr_path: str) -> None:
        """
        Register a process and its output file paths.

        Args:
            pid (int): Process ID.
            stdout_path (str): Path to the stdout file.
            stderr_path (str): Path to the stderr file.
        """
        self._processes[pid] = Process(stderr_path=stderr_path, stdout_path=stdout_path)

    def get_process(self, pid: int) -> str:
        """
        Retrieve and return the output of a completed process.

        Args:
            pid (int): Process ID.
        Returns:
            str: The formatted stdout and stderr output, or a not found message.
        """
        if pid not in self._processes:
            return f"Process {pid} not found in memory"

        try:
            process = psutil.Process(pid)
            process.wait()
        except psutil.NoSuchProcess:
            pass

        with open(self._processes[pid]["stdout_path"], "r") as f:
            stdout = f.read()
        with open(self._processes[pid]["stderr_path"], "r") as f:
            stderr = f.read()

        os.unlink(self._processes[pid]["stdout_path"])
        os.unlink(self._processes[pid]["stderr_path"])

        return f"Process {pid} produced the following stdout:\n\n```text\n{stdout}\n```\n\nAnd the following stderr:\n\n```text\n{stderr}\n```"


tracer = BashTracer()


def execute_command(command: str, args: list[str], wait: bool = True):
    """
    Execute a shell command, either synchronously or asynchronously.

    Args:
        command (str): The command to execute.
        args (list[str]): List of arguments for the command.
        wait (bool): If True, wait for the command to finish and return output. If False, run in background.
    Returns:
        str: The command output or process ID message.
    """
    if wait:
        output = sp.run([command, *args], capture_output=True)
        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        return f"Running command {command} with arguments: '{' '.join(args)}' produced the following stdout:\n\n```text\n{stdout}\n```\n\nAnd the following stderr:\n\n```text\n{stderr}\n```"
    else:
        stdout_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        stderr_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)

        process = sp.Popen([command, *args], stdout=stdout_file, stderr=stderr_file)

        stdout_file.close()
        stderr_file.close()

        tracer.register_process(process.pid, stdout_file.name, stderr_file.name)
        return f"Process ID: {process.pid} (use it to retrieve the result with the `bash_output` tool later)"


def bash_output(pid: int) -> str:
    """
    Retrieve the output of a background process by its PID.

    Args:
        pid (int): Process ID.
    Returns:
        str: The formatted stdout and stderr output.
    """
    return tracer.get_process(pid)
