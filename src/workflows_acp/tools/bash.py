import subprocess as sp
import psutil
import tempfile
import os

from typing_extensions import TypedDict


class Process(TypedDict):
    stdout_path: str
    stderr_path: str


class BashTracer:
    def __init__(self) -> None:
        self._processes: dict[int, Process] = {}

    def register_process(self, pid: int, stdout_path: str, stderr_path: str) -> None:
        self._processes[pid] = Process(stderr_path=stderr_path, stdout_path=stdout_path)

    def get_process(self, pid: int) -> str:
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
    return tracer.get_process(pid)
