import pytest

from qltoq3 import ziputil


class _DummyZipFile:
    def __init__(self, failures_before_success: int, error: OSError) -> None:
        self.failures_before_success = failures_before_success
        self.error = error
        self.calls = 0

    def write(self, path: str, arcname: str) -> None:
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise self.error


def _busy_oserror() -> OSError:
    err = OSError("file is busy")
    err.winerror = 32
    return err


def test_file_busy_identifies_known_busy_errors() -> None:
    assert ziputil.file_busy(PermissionError("denied")) is True
    assert ziputil.file_busy(_busy_oserror()) is True

    errno_13 = OSError("permission denied")
    errno_13.errno = 13
    assert ziputil.file_busy(errno_13) is (ziputil.os.name == "nt")


@pytest.mark.parametrize("non_busy", [RuntimeError("x"), OSError("generic")])
def test_file_busy_returns_false_for_other_errors(non_busy: BaseException) -> None:
    assert ziputil.file_busy(non_busy) is False


def test_zip_write_retry_retries_busy_error_and_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy = _DummyZipFile(failures_before_success=3, error=_busy_oserror())
    monkeypatch.setattr(ziputil.time, "sleep", lambda _: None)

    ziputil.zip_write_retry(dummy, "source.pk3", "inside/source.pk3")

    assert dummy.calls == 4


def test_zip_write_retry_raises_non_busy_error_without_retry() -> None:
    err = OSError("fatal")
    err.errno = 5
    dummy = _DummyZipFile(failures_before_success=1, error=err)

    with pytest.raises(OSError, match="fatal"):
        ziputil.zip_write_retry(dummy, "source.pk3", "inside/source.pk3")

    assert dummy.calls == 1
