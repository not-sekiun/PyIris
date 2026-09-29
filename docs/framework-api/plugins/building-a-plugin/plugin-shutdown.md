# Plugin Shutdown

`stop()` transitions a running plugin to `STOPPING` and awaits `on_stopped()`.
Only after the hook succeeds does the framework set `stop_event` and transition to
`STOPPED`. The running loop may still be waiting on the event while the hook runs.
Use `on_stopped()` for cleanup such as flushing buffers or writing state. Do not wait
for the main loop or other work that needs `stop_event` to be set: that would deadlock
the stop operation.

```python
async def on_stopped(self) -> None:
    self.logger.info(
        "Agent Report Plugin stopped after {} report(s) emitted.",
        self.environment.total_reports_emitted,
    )
```

Raise `PluginStopError` to refuse the stop. The framework restores `RUNNING` and
leaves `stop_event` unset, so check whether stopping is possible before releasing
resources the plugin needs to keep running:

```python
async def on_stopped(self) -> None:
    try:
        self._flush_pending_data()
    except IOError as exc:
        raise PluginStopError(
            message=f"Failed to flush data on stop: {exc}",
        ) from exc
```

## on_completed

`on_completed()` fires when `on_running()` returns normally without `stop()` having been
called. This is the "ran to completion" path, as opposed to the "was stopped externally"
path. Most persistent background plugins never hit `on_completed()` because their loop
runs until `stop()` is called. A plugin like `auto_updater`, which performs a single
check and exits, uses `on_completed()` to handle the post-run cleanup.

For a plugin whose loop is guarded by `stop_event`, leave `on_completed()` as a no-op:

```python
async def on_completed(self) -> None:
    pass
```

Continue to [Plugin Error Handling](plugin-error-handling.md) to handle runtime and
fatal
errors.
