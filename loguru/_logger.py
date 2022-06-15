import builtins
import contextlib
import functools
import itertools
import logging
import re
import sys
import warnings
from collections import namedtuple
from inspect import isclass, iscoroutinefunction, isgeneratorfunction
from multiprocessing import current_process
from os.path import basename, splitext
from threading import current_thread

from . import _asyncio_loop, _colorama, _defaults, _filters
from ._better_exceptions import ExceptionFormatter
from ._colorizer import Colorizer
from ._contextvars import ContextVar
from ._datetime import aware_now
from ._error_interceptor import ErrorInterceptor
from ._file_sink import FileSink
from ._get_frame import get_frame
from ._handler import Handler
from ._locks_machinery import create_logger_lock
from ._recattrs import RecordException, RecordFile, RecordLevel, RecordProcess, RecordThread
from ._simple_sinks import AsyncSink, CallableSink, StandardSink, StreamSink

if sys.version_info >= (3, 6):
    from os import PathLike
else:
    from pathlib import PurePath as PathLike


Level = namedtuple("Level", ["name", "no", "color", "icon"])

start_time = aware_now()

context = ContextVar("loguru_context", default={})


class Core:
    def __init__(self):
        levels = [
            Level(
                "TRACE",
                _defaults.LOGURU_TRACE_NO,
                _defaults.LOGURU_TRACE_COLOR,
                _defaults.LOGURU_TRACE_ICON,
            ),
            Level(
                "DEBUG",
                _defaults.LOGURU_DEBUG_NO,
                _defaults.LOGURU_DEBUG_COLOR,
                _defaults.LOGURU_DEBUG_ICON,
            ),
            Level(
                "INFO",
                _defaults.LOGURU_INFO_NO,
                _defaults.LOGURU_INFO_COLOR,
                _defaults.LOGURU_INFO_ICON,
            ),
            Level(
                "SUCCESS",
                _defaults.LOGURU_SUCCESS_NO,
                _defaults.LOGURU_SUCCESS_COLOR,
                _defaults.LOGURU_SUCCESS_ICON,
            ),
            Level(
                "WARNING",
                _defaults.LOGURU_WARNING_NO,
                _defaults.LOGURU_WARNING_COLOR,
                _defaults.LOGURU_WARNING_ICON,
            ),
            Level(
                "ERROR",
                _defaults.LOGURU_ERROR_NO,
                _defaults.LOGURU_ERROR_COLOR,
                _defaults.LOGURU_ERROR_ICON,
            ),
            Level(
                "CRITICAL",
                _defaults.LOGURU_CRITICAL_NO,
                _defaults.LOGURU_CRITICAL_COLOR,
                _defaults.LOGURU_CRITICAL_ICON,
            ),
        ]
        self.levels = {level.name: level for level in levels}
        self.levels_ansi_codes = {
            name: Colorizer.ansify(level.color) for name, level in self.levels.items()
        }
        self.levels_ansi_codes[None] = ""

        self.handlers_count = itertools.count()
        self.handlers = {}

        self.extra = {}
        self.patcher = None

        self.min_level = float("inf")
        self.enabled = {}
        self.activation_list = []
        self.activation_none = True

        self.lock = create_logger_lock()

    def __getstate__(self):
        state = self.__dict__.copy()
        state["lock"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.lock = create_logger_lock()


class Logger:

    def __init__(self, core, exception, depth, record, lazy, colors, raw, capture, patcher, extra):
        self._core = core
        self._options = (exception, depth, record, lazy, colors, raw, capture, patcher, extra)

    def __repr__(self):
        return "<loguru.logger handlers=%r>" % list(self._core.handlers.values())

    def add(
        self,
        sink,
        *,
        level=_defaults.LOGURU_LEVEL,
        format=_defaults.LOGURU_FORMAT,
        filter=_defaults.LOGURU_FILTER,
        colorize=_defaults.LOGURU_COLORIZE,
        serialize=_defaults.LOGURU_SERIALIZE,
        backtrace=_defaults.LOGURU_BACKTRACE,
        diagnose=_defaults.LOGURU_DIAGNOSE,
        enqueue=_defaults.LOGURU_ENQUEUE,
        catch=_defaults.LOGURU_CATCH,
        **kwargs
    ):
        with self._core.lock:
            handler_id = next(self._core.handlers_count)

        error_interceptor = ErrorInterceptor(catch, handler_id)

        if colorize is None and serialize:
            colorize = False

        if isinstance(sink, (str, PathLike)):
            path = sink
            name = "'%s'" % path

            if colorize is None:
                colorize = False

            wrapped_sink = FileSink(path, **kwargs)
            kwargs = {}
            encoding = wrapped_sink.encoding
            terminator = "\n"
            exception_prefix = ""
        elif hasattr(sink, "write") and callable(sink.write):
            name = getattr(sink, "name", None) or repr(sink)

            if colorize is None:
                colorize = _colorama.should_colorize(sink)

            if colorize is True and _colorama.should_wrap(sink):
                stream = _colorama.wrap(sink)
            else:
                stream = sink

            wrapped_sink = StreamSink(stream)
            encoding = getattr(sink, "encoding", None)
            terminator = "\n"
            exception_prefix = ""
        elif isinstance(sink, logging.Handler):
            name = repr(sink)

            if colorize is None:
                colorize = False

            wrapped_sink = StandardSink(sink)
            encoding = getattr(sink, "encoding", None)
            terminator = ""
            exception_prefix = "\n"
        elif iscoroutinefunction(sink) or iscoroutinefunction(getattr(sink, "__call__", None)):
            name = getattr(sink, "__name__", None) or repr(sink)

            if colorize is None:
                colorize = False

            loop = kwargs.pop("loop", None)

            if enqueue and loop is None:
                try:
                    loop = _asyncio_loop.get_running_loop()
                except RuntimeError as e:
                    raise ValueError(
                        "An event loop is required to add a coroutine sink with `enqueue=True`, "
                        "but but none has been passed as argument and none is currently running."
                    ) from e

            coro = sink if iscoroutinefunction(sink) else sink.__call__
            wrapped_sink = AsyncSink(coro, loop, error_interceptor)
            encoding = "utf8"
            terminator = "\n"
            exception_prefix = ""
        elif callable(sink):
            name = getattr(sink, "__name__", None) or repr(sink)

            if colorize is None:
                colorize = False

            wrapped_sink = CallableSink(sink)
            encoding = "utf8"
            terminator = "\n"
            exception_prefix = ""
        else:
            raise TypeError("Cannot log to objects of type '%s'" % type(sink).__name__)

        if kwargs:
            raise TypeError("add() got an unexpected keyword argument '%s'" % next(iter(kwargs)))

        if filter is None:
            filter_func = None
        elif filter == "":
            filter_func = _filters.filter_none
        elif isinstance(filter, str):
            parent = filter + "."
            length = len(parent)
            filter_func = functools.partial(_filters.filter_by_name, parent=parent, length=length)
        elif isinstance(filter, dict):
            level_per_module = {}
            for module, level_ in filter.items():
                if module is not None and not isinstance(module, str):
                    raise TypeError(
                        "The filter dict contains an invalid module, "
                        "it should be a string (or None), not: '%s'" % type(module).__name__
                    )
                if level_ is False:
                    levelno_ = False
                elif level_ is True:
                    levelno_ = 0
                elif isinstance(level_, str):
                    try:
                        levelno_ = self.level(level_).no
                    except ValueError:
                        raise ValueError(
                            "The filter dict contains a module '%s' associated to a level name "
                            "which does not exist: '%s'" % (module, level_)
                        )
                elif isinstance(level_, int):
                    levelno_ = level_
                else:
                    raise TypeError(
                        "The filter dict contains a module '%s' associated to an invalid level, "
                        "it should be an integer, a string or a boolean, not: '%s'"
                        % (module, type(level_).__name__)
                    )
                if levelno_ < 0:
                    raise ValueError(
                        "The filter dict contains a module '%s' associated to an invalid level, "
                        "it should be a positive integer, not: '%d'" % (module, levelno_)
                    )
                level_per_module[module] = levelno_
            filter_func = functools.partial(
                _filters.filter_by_level, level_per_module=level_per_module
            )
        elif callable(filter):
            if filter == builtins.filter:
                raise ValueError(
                    "The built-in 'filter()' function cannot be used as a 'filter' parameter, "
                    "this is most likely a mistake (please double-check the arguments passed "
                    "to 'logger.add()')."
                )
            filter_func = filter
        else:
            raise TypeError(
                "Invalid filter, it should be a function, a string or a dict, not: '%s'"
                % type(filter).__name__
            )

        if isinstance(level, str):
            levelno = self.level(level).no
        elif isinstance(level, int):
            levelno = level
        else:
            raise TypeError(
                "Invalid level, it should be an integer or a string, not: '%s'"
                % type(level).__name__
            )

        if levelno < 0:
            raise ValueError(
                "Invalid level value, it should be a positive integer, not: %d" % levelno
            )

        if isinstance(format, str):
            try:
                formatter = Colorizer.prepare_format(format + terminator + "{exception}")
            except ValueError as e:
                raise ValueError(
                    "Invalid format, color markups could not be parsed correctly"
                ) from e
            is_formatter_dynamic = False
        elif callable(format):
            if format == builtins.format:
                raise ValueError(
                    "The built-in 'format()' function cannot be used as a 'format' parameter, "
                    "this is most likely a mistake (please double-check the arguments passed "
                    "to 'logger.add()')."
                )
            formatter = format
            is_formatter_dynamic = True
        else:
            raise TypeError(
                "Invalid format, it should be a string or a function, not: '%s'"
                % type(format).__name__
            )

        if not isinstance(encoding, str):
            encoding = "ascii"

        with self._core.lock:
            exception_formatter = ExceptionFormatter(
                colorize=colorize,
                encoding=encoding,
                diagnose=diagnose,
                backtrace=backtrace,
                hidden_frames_filename=self.catch.__code__.co_filename,
                prefix=exception_prefix,
            )

            handler = Handler(
                name=name,
                sink=wrapped_sink,
                levelno=levelno,
                formatter=formatter,
                is_formatter_dynamic=is_formatter_dynamic,
                filter_=filter_func,
                colorize=colorize,
                serialize=serialize,
                enqueue=enqueue,
                id_=handler_id,
                error_interceptor=error_interceptor,
                exception_formatter=exception_formatter,
                levels_ansi_codes=self._core.levels_ansi_codes,
            )

            handlers = self._core.handlers.copy()
            handlers[handler_id] = handler

            self._core.min_level = min(self._core.min_level, levelno)
            self._core.handlers = handlers

        return handler_id

    def remove(self, handler_id=None):
        if not (handler_id is None or isinstance(handler_id, int)):
            raise TypeError(
                "Invalid handler id, it should be an integer as returned "
                "by the 'add()' method (or None), not: '%s'" % type(handler_id).__name__
            )

        with self._core.lock:
            handlers = self._core.handlers.copy()

            if handler_id is not None and handler_id not in handlers:
                raise ValueError("There is no existing handler with id %d" % handler_id) from None

            if handler_id is None:
                handler_ids = list(handlers.keys())
            else:
                handler_ids = [handler_id]

            for handler_id in handler_ids:
                handler = handlers.pop(handler_id)

                # This needs to be done first in case "stop()" raises an exception
                levelnos = (h.levelno for h in handlers.values())
                self._core.min_level = min(levelnos, default=float("inf"))
                self._core.handlers = handlers

                handler.stop()

    def complete(self):

        with self._core.lock:
            handlers = self._core.handlers.copy()
            for handler in handlers.values():
                handler.complete_queue()

        class AwaitableCompleter:
            def __await__(self_):
                with self._core.lock:
                    handlers = self._core.handlers.copy()
                    for handler in handlers.values():
                        yield from handler.complete_async().__await__()

        return AwaitableCompleter()

    def catch(
        self,
        exception=Exception,
        *,
        level="ERROR",
        reraise=False,
        onerror=None,
        exclude=None,
        default=None,
        message="An error has been caught in function '{record[function]}', "
        "process '{record[process].name}' ({record[process].id}), "
        "thread '{record[thread].name}' ({record[thread].id}):"
    ):
        if callable(exception) and (
            not isclass(exception) or not issubclass(exception, BaseException)
        ):
            return self.catch()(exception)

        class Catcher:
            def __init__(self_, from_decorator):
                self_._from_decorator = from_decorator

            def __enter__(self_):
                return None

            def __exit__(self_, type_, value, traceback_):
                if type_ is None:
                    return

                if not issubclass(type_, exception):
                    return False

                if exclude is not None and issubclass(type_, exclude):
                    return False

                from_decorator = self_._from_decorator
                _, depth, _, *options = self._options

                if from_decorator:
                    depth += 1

                catch_options = [(type_, value, traceback_), depth, True] + options
                level_id, static_level_no = self._dynamic_level(level)
                self._log(level_id, static_level_no, from_decorator, catch_options, message, (), {})

                if onerror is not None:
                    onerror(value)

                return not reraise

            def __call__(_, function):
                catcher = Catcher(True)

                if iscoroutinefunction(function):

                    async def catch_wrapper(*args, **kwargs):
                        with catcher:
                            return await function(*args, **kwargs)
                        return default

                elif isgeneratorfunction(function):

                    def catch_wrapper(*args, **kwargs):
                        with catcher:
                            return (yield from function(*args, **kwargs))
                        return default

                else:

                    def catch_wrapper(*args, **kwargs):
                        with catcher:
                            return function(*args, **kwargs)
                        return default

                functools.update_wrapper(catch_wrapper, function)
                return catch_wrapper

        return Catcher(False)

    def opt(
        self,
        *,
        exception=None,
        record=False,
        lazy=False,
        colors=False,
        raw=False,
        capture=True,
        depth=0,
        ansi=False
    ):
        if ansi:
            colors = True
            warnings.warn(
                "The 'ansi' parameter is deprecated, please use 'colors' instead",
                DeprecationWarning,
            )

        args = self._options[-2:]
        return Logger(self._core, exception, depth, record, lazy, colors, raw, capture, *args)

    def bind(__self, **kwargs):
        *options, extra = __self._options
        return Logger(__self._core, *options, {**extra, **kwargs})

    @contextlib.contextmanager
    def contextualize(__self, **kwargs):
        with __self._core.lock:
            new_context = {**context.get(), **kwargs}
            token = context.set(new_context)

        try:
            yield
        finally:
            with __self._core.lock:
                context.reset(token)

    def patch(self, patcher):
        *options, _, extra = self._options
        return Logger(self._core, *options, patcher, extra)

    def level(self, name, no=None, color=None, icon=None):
        if not isinstance(name, str):
            raise TypeError(
                "Invalid level name, it should be a string, not: '%s'" % type(name).__name__
            )

        if no is color is icon is None:
            try:
                return self._core.levels[name]
            except KeyError:
                raise ValueError("Level '%s' does not exist" % name) from None

        if name not in self._core.levels:
            if no is None:
                raise ValueError(
                    "Level '%s' does not exist, you have to create it by specifying a level no"
                    % name
                )
            else:
                old_color, old_icon = "", " "
        elif no is not None:
            raise TypeError("Level '%s' already exists, you can't update its severity no" % name)
        else:
            _, no, old_color, old_icon = self.level(name)

        if color is None:
            color = old_color

        if icon is None:
            icon = old_icon

        if not isinstance(no, int):
            raise TypeError(
                "Invalid level no, it should be an integer, not: '%s'" % type(no).__name__
            )

        if no < 0:
            raise ValueError("Invalid level no, it should be a positive integer, not: %d" % no)

        ansi = Colorizer.ansify(color)
        level = Level(name, no, color, icon)

        with self._core.lock:
            self._core.levels[name] = level
            self._core.levels_ansi_codes[name] = ansi
            for handler in self._core.handlers.values():
                handler.update_format(name)

        return level

    def disable(self, name):
        self._change_activation(name, False)

    def enable(self, name):
        self._change_activation(name, True)

    def configure(self, *, handlers=None, levels=None, extra=None, patcher=None, activation=None):
        if handlers is not None:
            self.remove()
        else:
            handlers = []

        if levels is not None:
            for params in levels:
                self.level(**params)

        if patcher is not None:
            with self._core.lock:
                self._core.patcher = patcher

        if extra is not None:
            with self._core.lock:
                self._core.extra.clear()
                self._core.extra.update(extra)

        if activation is not None:
            for name, state in activation:
                if state:
                    self.enable(name)
                else:
                    self.disable(name)

        return [self.add(**params) for params in handlers]

    def _change_activation(self, name, status):
        if not (name is None or isinstance(name, str)):
            raise TypeError(
                "Invalid name, it should be a string (or None), not: '%s'" % type(name).__name__
            )

        with self._core.lock:
            enabled = self._core.enabled.copy()

            if name is None:
                for n in enabled:
                    if n is None:
                        enabled[n] = status
                self._core.activation_none = status
                self._core.enabled = enabled
                return

            if name != "":
                name += "."

            activation_list = [
                (n, s) for n, s in self._core.activation_list if n[: len(name)] != name
            ]

            parent_status = next((s for n, s in activation_list if name[: len(n)] == n), None)
            if parent_status != status and not (name == "" and status is True):
                activation_list.append((name, status))

                def modules_depth(x):
                    return x[0].count(".")

                activation_list.sort(key=modules_depth, reverse=True)

            for n in enabled:
                if n is not None and (n + ".")[: len(name)] == name:
                    enabled[n] = status

            self._core.activation_list = activation_list
            self._core.enabled = enabled

    @staticmethod
    def parse(file, pattern, *, cast={}, chunk=2 ** 16):
        if isinstance(file, (str, PathLike)):
            should_close = True
            fileobj = open(str(file))
        elif hasattr(file, "read") and callable(file.read):
            should_close = False
            fileobj = file
        else:
            raise TypeError(
                "Invalid file, it should be a string path or a file object, not: '%s'"
                % type(file).__name__
            )

        if isinstance(cast, dict):

            def cast_function(groups):
                for key, converter in cast.items():
                    if key in groups:
                        groups[key] = converter(groups[key])

        elif callable(cast):
            cast_function = cast
        else:
            raise TypeError(
                "Invalid cast, it should be a function or a dict, not: '%s'" % type(cast).__name__
            )

        try:
            regex = re.compile(pattern)
        except TypeError:
            raise TypeError(
                "Invalid pattern, it should be a string or a compiled regex, not: '%s'"
                % type(pattern).__name__
            ) from None

        matches = Logger._find_iter(fileobj, regex, chunk)

        for match in matches:
            groups = match.groupdict()
            cast_function(groups)
            yield groups

        if should_close:
            fileobj.close()

    @staticmethod
    def _find_iter(fileobj, regex, chunk):
        buffer = fileobj.read(0)

        while 1:
            text = fileobj.read(chunk)
            buffer += text
            matches = list(regex.finditer(buffer))

            if not text:
                yield from matches
                break

            if len(matches) > 1:
                end = matches[-2].end()
                buffer = buffer[end:]
                yield from matches[:-1]

    def _log(self, level_id, static_level_no, from_decorator, options, message, args, kwargs):
        core = self._core

        if not core.handlers:
            return

        (exception, depth, record, lazy, colors, raw, capture, patcher, extra) = options

        frame = get_frame(depth + 2)

        try:
            name = frame.f_globals["__name__"]
        except KeyError:
            name = None

        try:
            if not core.enabled[name]:
                return
        except KeyError:
            enabled = core.enabled
            if name is None:
                status = core.activation_none
                enabled[name] = status
                if not status:
                    return
            else:
                dotted_name = name + "."
                for dotted_module_name, status in core.activation_list:
                    if dotted_name[: len(dotted_module_name)] == dotted_module_name:
                        if status:
                            break
                        enabled[name] = False
                        return
                enabled[name] = True

        current_datetime = aware_now()

        if level_id is None:
            level_icon = " "
            level_no = static_level_no
            level_name = "Level %d" % level_no
        else:
            try:
                level_name, level_no, _, level_icon = core.levels[level_id]
            except KeyError:
                raise ValueError("Level '%s' does not exist" % level_id) from None

        if level_no < core.min_level:
            return

        code = frame.f_code
        file_path = code.co_filename
        file_name = basename(file_path)
        thread = current_thread()
        process = current_process()
        elapsed = current_datetime - start_time

        if exception:
            if isinstance(exception, BaseException):
                type_, value, traceback = (type(exception), exception, exception.__traceback__)
            elif isinstance(exception, tuple):
                type_, value, traceback = exception
            else:
                type_, value, traceback = sys.exc_info()
            exception = RecordException(type_, value, traceback)
        else:
            exception = None

        log_record = {
            "elapsed": elapsed,
            "exception": exception,
            "extra": {**core.extra, **context.get(), **extra},
            "file": RecordFile(file_name, file_path),
            "function": code.co_name,
            "level": RecordLevel(level_name, level_no, level_icon),
            "line": frame.f_lineno,
            "message": str(message),
            "module": splitext(file_name)[0],
            "name": name,
            "process": RecordProcess(process.ident, process.name),
            "thread": RecordThread(thread.ident, thread.name),
            "time": current_datetime,
        }

        if lazy:
            args = [arg() for arg in args]
            kwargs = {key: value() for key, value in kwargs.items()}

        if capture and kwargs:
            log_record["extra"].update(kwargs)

        if record:
            if "record" in kwargs:
                raise TypeError(
                    "The message can't be formatted: 'record' shall not be used as a keyword "
                    "argument while logger has been configured with '.opt(record=True)'"
                )
            kwargs.update(record=log_record)

        if colors:
            if args or kwargs:
                colored_message = Colorizer.prepare_message(message, args, kwargs)
            else:
                colored_message = Colorizer.prepare_simple_message(str(message))
            log_record["message"] = colored_message.stripped
        elif args or kwargs:
            colored_message = None
            log_record["message"] = message.format(*args, **kwargs)
        else:
            colored_message = None

        if core.patcher:
            core.patcher(log_record)

        if patcher:
            patcher(log_record)

        for handler in core.handlers.values():
            handler.emit(log_record, level_id, from_decorator, raw, colored_message)

    def trace(__self, __message, *args, **kwargs):
        __self._log("TRACE", None, False, __self._options, __message, args, kwargs)

    def debug(__self, __message, *args, **kwargs):
        __self._log("DEBUG", None, False, __self._options, __message, args, kwargs)

    def info(__self, __message, *args, **kwargs):
        __self._log("INFO", None, False, __self._options, __message, args, kwargs)

    def success(__self, __message, *args, **kwargs):
        __self._log("SUCCESS", None, False, __self._options, __message, args, kwargs)

    def warning(__self, __message, *args, **kwargs):
        __self._log("WARNING", None, False, __self._options, __message, args, kwargs)

    def error(__self, __message, *args, **kwargs):
        __self._log("ERROR", None, False, __self._options, __message, args, kwargs)

    def critical(__self, __message, *args, **kwargs):
        __self._log("CRITICAL", None, False, __self._options, __message, args, kwargs)

    def exception(__self, __message, *args, **kwargs):
        options = (True,) + __self._options[1:]
        __self._log("ERROR", None, False, options, __message, args, kwargs)

    def log(__self, __level, __message, *args, **kwargs):
        level_id, static_level_no = __self._dynamic_level(__level)
        __self._log(level_id, static_level_no, False, __self._options, __message, args, kwargs)

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def _dynamic_level(level):

        if isinstance(level, str):
            return (level, None)

        if isinstance(level, int):
            if level < 0:
                raise ValueError(
                    "Invalid level value, it should be a positive integer, not: %d" % level
                )
            return (None, level)

        raise TypeError(
            "Invalid level, it should be an integer or a string, not: '%s'" % type(level).__name__
        )

    def start(self, *args, **kwargs):
        warnings.warn(
            "The 'start()' method is deprecated, please use 'add()' instead", DeprecationWarning
        )
        return self.add(*args, **kwargs)

    def stop(self, *args, **kwargs):

        warnings.warn(
            "The 'stop()' method is deprecated, please use 'remove()' instead", DeprecationWarning
        )
        return self.remove(*args, **kwargs)
