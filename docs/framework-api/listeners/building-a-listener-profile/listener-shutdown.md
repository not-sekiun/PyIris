# Listener Shutdown

`stop()` transitions a running listener to `STOPPING` and awaits `on_stopped()`.
Only after the hook succeeds does the framework set `stop_event` and transition to
`STOPPED`. The running loop may still be waiting on the event while the hook runs.
Use `on_stopped()` to release resources, but do not wait for the main loop or other
work that needs `stop_event` to be set: that would deadlock the stop operation.

Raising `ListenerStopError` refuses the stop: the framework restores `RUNNING` and
leaves the event unset. Check whether stopping is possible before releasing resources
that the listener needs to keep running.

```python
    async def on_stopped(self) -> None:
        if hasattr(self.environment, "server"):
            self.environment.server.close()
            await self.environment.server.wait_closed()
            self.logger.info("TCP JSON Listener stopped.")
```

## on_cancelled

`on_cancelled()` runs when the listener is cancelled rather than stopped normally. It
should release the same resources as `on_stopped()`, but it may run before `on_running()`
finished initialising, so guard attribute access with `hasattr`:

```python
    async def on_cancelled(self) -> None:
        # stop() may have been called before on_running() stored the server
        if hasattr(self.environment, "server"):
            self.environment.server.close()
```

That guard is the practical reason runtime state lives on `self.environment` rather than
directly on `self`: a cancellation mid-startup can reach the shutdown hooks before the
server object exists, and the `hasattr` check keeps that case simple.

Continue to [Listener Error Handling](listener-error-handling.md) for runtime and fatal
errors.
