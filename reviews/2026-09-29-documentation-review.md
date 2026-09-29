# Documentation review before merging code review fixes

Reviewed 2026-09-29 against `fix/code-review-fixes` at
`4768f7638ffa4cfb0b8fb271ace397f3750603b7`.

**Remediation status:** D1-D11 and the additional websocket documentation gaps
were corrected on the same branch on 2026-09-29. Findings and line references
below describe the original reviewed revision. The correction summary is at the end.

## Scope and baseline

- Compared the locally available `origin/dev` at
  `c9c4d43614c7033536fa4f7f8721bae1be03b156` with the branch head. No remote
  refresh was performed. Local `dev` is a different revision,
  `1e7c8fad14b1f069b4780fa553095e492c94c7db`, so it was not treated as the
  authoritative remote merge target.
- Reviewed the branch's documentation-facing changes, framework author guides,
  lifecycle and event-hook contracts, relevant client/server usage and websocket
  guides, generated-reference entry points and their relevant source docstrings,
  README and site configuration.
- Only `docs/server-usage/logging.md` changes in the documentation tree across
  the merge range. Most findings below are existing inconsistencies that would
  remain after the merge. D1 directly concerns the new template-binding behavior.
- This was a static review. No tests, lint, documentation build, application
  imports, network requests, or example execution were performed. Source under
  `consortium/components/`, `scripts/`, `data/`, and `test_agents/` was not inspected;
  claims about those bundled implementations and shipped configuration files
  remain outside the verified scope. Reading `docs/` was authorized by this task.
- The initial review made no source or documentation changes. The subsequent
  authorized remediation is recorded below.

## Findings

Eight P2 findings can mislead consumers into broken behavior or configuration.
Three P3 findings are localized reference or navigation errors.

### D1 [P2] Describe template binding as per-instance creation state

**Documentation:**
`docs/framework-api/listeners/building-a-listener-profile/listener-template.md:28`,
`docs/framework-api/listeners/building-a-listener-profile/listener-conventions.md:28`,
`docs/framework-api/listeners/building-a-listener-profile/listener-conventions.md:38`,
`docs/framework-api/agents/building-an-agent-profile/agent-template.md:32`, and
`docs/framework-api/agents/building-an-agent-profile/agent-generator.md:188`.

The guides still say the loader assigns `creating_listener_template` and
`creating_agent_template` to component classes, and describe `listener_type` as a
class attribute. Commit `515320ca` deliberately replaced that model: templates
bind each created instance, and type properties resolve through that instance's
creating template. Reading the class no longer gives a reliable template/type for
an arbitrary instance, especially when multiple templates share one implementation.

**Evidence:** `consortium/framework/listeners/base_listener_template.py:300` and
`:311`, `consortium/framework/listeners/base_listener.py:201`,
`consortium/framework/agents/base_agent_template.py:275` and `:281`, and
`consortium/framework/agents/base_agent_generator.py:567`.

The generated listener reference also inherits the constructor wording at
`consortium/framework/listeners/base_listener.py:108` that direct construction is
supported, with templates merely recommended. A directly constructed listener is
unbound: `listener_type` and serialization depend on `creating_listener_template`.
The factory sets that binding after the listener constructor returns. This
limitation now needs to be explicit in the reference.

**Correction:** describe the factories as establishing per-instance bindings;
read template/type metadata from the created instance. Document the current
unbound-construction limitation pending the framework triage's Q4 decision. Do
not promise the binding is available inside a listener's constructor.

**Relation to merge:** directly stale relative to `515320ca`.

### D2 [P2] Replace removed Payload APIs in working examples

**Documentation:**
`docs/framework-api/agents/building-an-agent-profile/agent-capabilities.md:86`
and `:163`,
`docs/framework-api/agents/building-an-agent-profile/complete-agent-profile.md:60`,
and `docs/framework-api/agents/common-agent-capability-patterns.md:143`.

Examples access `msg.payload.data` or `response.payload.data`. The capability
guide also instructs readers to call `await payload.load()`. Neither API exists
on the current `Payload`, so copying these examples raises `AttributeError` as
soon as a payload is processed. The prose's distinction between in-memory and
streamed payload access is obsolete too.

**Evidence:** `consortium/framework/agents/agent_message_models.py:29` describes
the current interface; `:287` implements `await payload.read()`, and `:304`
implements async iteration. `size` is available without loading the bytes.

**Correction:** use `await payload.read()` when bytes are needed, async iteration
when processing chunks, and `payload.size` when only counting bytes. Update all
three pages together, including the prose and complete example.

**Relation to merge:** pre-existing; unchanged in the merge range.

### D3 [P2] Correct the shutdown hook and stop-event ordering

**Documentation:**
`docs/framework-api/listeners/building-a-listener-profile/listener-shutdown.md:3`
and `docs/framework-api/plugins/building-a-plugin/plugin-shutdown.md:3`.

Both pages state that `stop_event` is set before `on_stopped()` runs and that the
main loop has already unblocked. The lifecycle does the reverse: it transitions
to STOPPING, awaits `on_stopped()`, and only sets the event after the hook accepts
the stop. A `ComponentStopError` restores RUNNING without setting it. An author
who waits inside `on_stopped()` for a loop parked on that event can deadlock the
stop operation.

**Evidence:**
`consortium/framework/_core/components/component_life_cycle.py:179` awaits the
hook; `:180` handles refusal; `:206` sets the event on success.

**Correction:** explain that `on_stopped()` executes while the running loop may
still be waiting on `stop_event`. It must not wait for work whose completion
depends on that event being set. Explain refusal separately from successful stop.

**Relation to merge:** pre-existing; the lifecycle implementation is unchanged
in this merge range.

### D4 [P2] Remove the blanket instruction to call services without await

**Documentation:**
`docs/framework-api/plugins/building-a-plugin/plugin-running-loop.md:55` and
`docs/framework-api/event-hooks/building-an-event-hook/event-hook-conventions.md:40`.

These pages say all service calls are synchronous and should not be awaited.
That is true of the illustrated getters but false for lifecycle operations,
event dispatch, component loading and several storage APIs. Following the rule
for one of those methods merely creates a coroutine; the requested operation
never runs.

**Evidence:**
`consortium/server/services/listeners_service.py:387` declares async listener
start, `consortium/server/services/events_service.py:182` declares async event
dispatch, and `consortium/server/services/plugins_service.py:276` declares async
plugin loading.

**Correction:** qualify the synchronous examples as getters and tell authors to
follow each method's signature, awaiting async methods. Include one async example.

**Relation to merge:** pre-existing; accepting synchronous event handlers in
`75ada98c` does not make service methods synchronous.

### D5 [P2] Remove obsolete permissions from the configuration catalog

**Documentation:** `docs/server-usage/roles-and-permissions.md:118`.

The supposedly complete catalog lists `READ_ALL_AGENT_TASKS_BY_AGENT_ID` and
`READ_AGENT_TASK_BY_AGENT_ID_AND_TASK_ID`. Neither is a current `UserPermissions`
member. Adding them to a role based on this page causes the authorization
configuration loader to reject the file, which prevents normal server startup.

**Evidence:** `consortium/server/objects/user_account_objects.py` contains the
current enum; `consortium/server/services/authorization_service.py:82` and `:112`
validate each configured value. The current task routes use
`READ_ALL_AGENT_TASKS` and `READ_AGENT_TASK_BY_TASK_ID` at
`consortium/server/api/tasks_api.py:59` and `:83`.

**Correction:** remove the obsolete entries and explain agent filtering under
the current task-list permission.

**Relation to merge:** pre-existing; unchanged in the merge range.

### D6 [P2] Remove the websocket next-message-is-response guarantee

**Documentation:**
`docs/server-api/events-websockets-api/sending-action-commands.md:27` and its
unsubscribe/query examples.

The guide guarantees the first message after an action command is its response.
On a connection with existing subscriptions, a pushed event may already be queued
or arrive while the server receives and handles the command. The examples then
index `success` or `data` on that event as though it were a command reply, causing
errors or treating an event payload as a query result.

**Evidence:**
`consortium/server/services/events_websocket_service.py:134` independently sends
events. Action handlers send responses separately (for example `:228` and
`:304`); there is no connection-wide mechanism that enforces the documented
client-observed ordering. Subscription registration also precedes its response.

**Correction:** receive and dispatch by `type`, continuing to process events
while waiting for a `response`. Keep only one action outstanding if relying on
the current response format, which has no request correlation ID.

**Relation to merge:** pre-existing; unchanged by the branch's action validation
and event-handler fixes.

### D7 [P2] Do not promise framework reporting for detached task exceptions

**Documentation:**
`docs/framework-api/event-hooks/building-an-event-hook/event-hook-triggering.md:104`.

After showing `asyncio.create_task(...)`, the guide tells readers to raise
`EventHookTriggerError` inside that background task's exception handler to report
the failure through the framework. That exception remains on the detached task;
its type does not reconnect it to the events service. It can become an
unretrieved task exception instead of the promised structured hook failure.

**Evidence:** `consortium/server/services/events_service.py:233` gathers only
the registered handler invocations. Its subsequent remapping examines those
results, not independently created tasks.

**Correction:** await work within `on_triggered()` to use framework failure
propagation. If deliberately detaching work, explicitly own the task and handle
or report its exception through a chosen reporting path.

**Relation to merge:** pre-existing; the new sync-handler wrapper does not change
detached task ownership.

### D8 [P2] State the actual launch-message snapshot timing

**Documentation:**
`docs/framework-api/agents/building-an-agent-profile/agent-capabilities.md:190`
and the generated reference from
`consortium/framework/agents/base_agent_capability.py:141`.

The guide calls `self.task_launch_message` the message sent to the agent; the
source docstring additionally says it is set after `on_launch()` completes.
The implementation deep-copies the incoming message before calling that hook.
If the hook mutates or replaces the message, code reading the attribute sees
the original snapshot rather than the actual transmitted values.

**Evidence:** `consortium/framework/agents/base_agent_capability.py:364` captures
the snapshot, `:371` invokes `on_launch()`, and `:404` dispatches its returned
message.

**Correction:** document the current pre-hook snapshot, or resolve the existing
Q4 contract decision before changing the implementation and both documentation
locations together. The current wording should not assert post-hook semantics.

**Relation to merge:** pre-existing and already identified as a contract decision
in the framework triage; it remains visible in the user-facing documentation.

### D9 [P3] Correct the option value shapes in the summary table

**Documentation:**
`docs/framework-api/listeners/building-a-listener-profile/listener-template.md:79`.

`ChoiceValueOption` is described as accepting only strings, although it accepts
primitive strings, integers, floats and booleans. `ToggleableChoicesValueOption`
is described as a subset of choices without stating that its value must be a
`dict[str, bool]`; passing a list or set of selected choices fails validation.

**Evidence:** `consortium/framework/options/choice_value_option.py:120` and
`consortium/framework/options/toggleable_choices_value_option.py:96`.

**Correction:** show the actual types and a toggle example such as
`{"feature_a": true, "feature_b": false}`. The dictionary option's scalar-only
table entry already agrees with Q1's validation change.

**Relation to merge:** pre-existing; worth correcting alongside the option fixes.

### D10 [P3] Include the server subcommand in the debugging command

**Documentation:**
`docs/server-api/events-websockets-api/authentication.md:189`.

The troubleshooting command is `uv run python consortium.py -d`. The debug flag
belongs to the `server` and `client` subparsers, so this command does not start
the server.

**Evidence:** `consortium.py:25` creates the server subparser and `:61` registers
its debug option.

**Correction:** use `uv run consortium.py server -d`.

**Relation to merge:** pre-existing.

### D11 [P3] Point the documentation site's repository link at Consortium

**Documentation configuration:** `zensical.toml:13`.

The site identifies the repository as `not-sekiun/Consortium`, but `repo_url`
still points at `not-sekiun/PyIris`. Repository navigation generated from this
setting points at a different repository name. Whether that old URL redirects
was not checked.

**Correction:** align `repo_url` with the Consortium repository URL already used
throughout the README and site settings.

**Relation to merge:** pre-existing.

## Additional documentation gaps

The websocket server-message guide documents only `{"type": "event"}` and says
other envelope fields depend on the event. The implementation always adds
`event_type`, `message` and `data` from `Event.to_json()`
(`consortium/framework/event_hooks/_event.py:30`). Document this shared envelope
even while event-specific data schemas are evolving. The action guide's event
catalog lists only START_SERVER and STOP_SERVER; linking the broader framework
event catalog and recommending `get_all_events` would avoid maintaining a
second incomplete list.

## Changes already reflected correctly

- The logging page includes `log_secrets`, its false default, explicit-log-site
  scope and the separate always-hidden password representations. The startup
  loader now passes the option through.
- Listener and plugin `on_running()` source docstrings now describe one
  invocation that owns the running loop; the narrative loop examples already
  use that pattern.
- The dictionary option table already promises scalar values. Q1 restores that
  contract rather than requiring the guide to promise nested values.
- The repository service reference is generated from source; its revised public
  docstrings describe missing-file reconciliation and rollback limitations.
- No narrative claim retaining the removed 1,000-terminal-task cap was found.
- Websocket action docs already say batches validate before applying changes and
  that actions without an `events` argument must omit the field.

## Remediation completed

- D1: changed the guides and generated constructor reference to describe instance
  bindings, factory construction and the listener constructor's unbound state.
- D2: replaced removed payload APIs with `read()` or `size`, and handled absent
  payloads in chunk examples.
- D3-D4: corrected stop-event ordering and refusal behavior, and distinguished
  synchronous getters from service methods that must be awaited.
- D5: removed the two obsolete permission names and explained task filtering.
- D6: changed the diagram, ordering contract and all affected websocket examples
  to handle events while awaiting responses and reject failed actions.
- D7: corrected detached-task failure guidance.
- D8: documented the current pre-hook snapshot in both the guide and source
  docstring. Runtime snapshot semantics were not changed.
- D9-D11: corrected option shapes, the debug command and the site repository URL.
- Added the common websocket event envelope and linked the framework event
  catalog in place of the incomplete two-event list.

Validation was a source comparison and diff review, including `git diff --check`
and a search for the removed claims. No tests, lint, documentation build or
application execution were run. The two Python edits change public docstrings only.
