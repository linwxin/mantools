import os
import threading
import weakref

if not hasattr(os, "register_at_fork"):

    def create_logger_lock():
        return threading.Lock()

    def create_handler_lock():
        return threading.Lock()

else:

    logger_locks = weakref.WeakSet()
    handler_locks = weakref.WeakSet()

    def acquire_locks():
        for lock in logger_locks:
            lock.acquire()

        for lock in handler_locks:
            lock.acquire()

    def release_locks():
        for lock in logger_locks:
            lock.release()

        for lock in handler_locks:
            lock.release()

    os.register_at_fork(
        before=acquire_locks,
        after_in_parent=release_locks,
        after_in_child=release_locks,
    )

    def create_logger_lock():
        lock = threading.Lock()
        logger_locks.add(lock)
        return lock

    def create_handler_lock():
        lock = threading.Lock()
        handler_locks.add(lock)
        return lock
