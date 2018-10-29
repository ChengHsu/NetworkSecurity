import asyncio


class Timer:
    def __init__(self, timeout, loop, callback, arg):
        self._timeout = timeout
        self._callback = callback
        self._callback_arg = arg
        self._loop = loop
        self._task = self._loop.call_later(timeout,self._callback,self._callback_arg)

    def cancel(self):
        self._task.cancel()


class PopTimer:
    def __init__(self, timeout,loop,callback):
        self._timeout = timeout
        self._callback = callback
        self._loop = loop
        self._task = self._loop.call_later(self._timeout, self._callback)

    def cancel(self):
        self._task.cancel()