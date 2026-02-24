"""Shell command wrappers."""

from dataclasses import dataclass
import shutil
import subprocess


@dataclass
class CmdResult:
    code: int
    stdout: str
    stderr: str


def command_exists(name):
    return shutil.which(name) is not None


def run_command(args, timeout=20):
    try:
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CmdResult(code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    except FileNotFoundError:
        return CmdResult(code=127, stdout="", stderr=f"command not found: {args[0]}")


def run_user_systemctl(args, timeout=20):
    return run_command(["systemctl", "--user", *args], timeout=timeout)


def run_pw_cli(args, timeout=20):
    return run_command(["pw-cli", *args], timeout=timeout)
