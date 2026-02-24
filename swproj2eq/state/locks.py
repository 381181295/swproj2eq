"""Process lock for state-changing commands."""

from contextlib import contextmanager
import fcntl

from swproj2eq.state.paths import ensure_dirs, lock_file


@contextmanager
def state_lock():
    ensure_dirs()
    lf = lock_file()
    with lf.open("w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
