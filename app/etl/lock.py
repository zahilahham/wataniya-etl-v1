import threading

_etl_lock = threading.Lock()


def try_acquire() -> bool:
    return _etl_lock.acquire(blocking=False)


def release() -> None:
    _etl_lock.release()
