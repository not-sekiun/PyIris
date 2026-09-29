After connecting, the server waits for the client to send action commands. The server
only pushes data unprompted when a subscribed event fires. All messages over the
websocket are JSON strings.

## Message Flow

``` mermaid
sequenceDiagram
    participant C as Client
    participant WS as Websocket Server
    participant E as Events Service
    C->>+WS: Subscription action command (Subscribe to event A)
    WS-->>-C: Action command response
    E-->>WS: Event A occurs
    WS-->>C: Event A JSON data sent
    E-->>WS: Event A occurs
    C->>+WS: Subscription action command (Subscribe to event B)
    WS-->>C: Event A JSON data sent
    WS-->>-C: Action command response
    E-->>WS: Event B occurs
    WS-->>C: Event B JSON data sent
```

Key behaviors:

1. Events can arrive at any time in any order. Build your client to handle this.
2. Events and action responses share the connection. An event can arrive while you
   wait for a response, so dispatch messages by `type` instead of assuming the next
   message is the reply. Keep one action outstanding at a time: responses do not
   contain a request ID.
3. Each websocket connection is independent. The same client can open multiple
   connections, each with its own set of subscriptions. Tickets are single use, so each
   of those connections needs its own freshly issued ticket.
4. When a connection closes, all its subscriptions are automatically cleaned up.

## Action Command Format

```json title="Action command"
{
  "action": "ACTION_COMMAND_STRING",
  "events": ["EVENT_TYPE_1", "EVENT_TYPE_2"]
}
```

| Key      | Description                                                                                         |
|----------|-----------------------------------------------------------------------------------------------------|
| `action` | The action to perform. **Required**.                                                                |
| `events` | List of event type strings. Required for `subscribe`/`unsubscribe`, must be omitted for all others. |

!!! note
    When `events` is not required, **omit the field entirely** — do not pass an empty list.

| Action                    | Description                                          | `events` required? |
|---------------------------|------------------------------------------------------|--------------------|
| `subscribe`               | Subscribe this connection to one or more events.     | Yes                |
| `unsubscribe`             | Unsubscribe this connection from one or more events. | Yes                |
| `get_subscribed_events`   | Get all events this connection is subscribed to.     | No                 |
| `get_unsubscribed_events` | Get all events this connection is not subscribed to. | No                 |
| `get_all_events`          | Get all events the API supports.                     | No                 |

## Server Responses

Every action command receives exactly one response.
See [Server Messages](server-messages.md)
for the full schema. Check the `success` field to determine whether the command
succeeded.

**Success**

```json title="Success response"
{
  "type": "response",
  "success": true,
  "message": "Successfully subscribed to the provided events.",
  "data": null
}
```

**Error**

```json title="Error response"
{
  "type": "response",
  "success": false,
  "errors": [
    {
      "code": "INVALID_EVENT_TYPE_ERROR",
      "message": "Failed to subscribe to event. The provided event type 'BAD_EVENT' does not exist.",
      "detail": {"event": "BAD_EVENT"}
    }
  ]
}
```

`errors` may contain multiple objects if a batch command fails on more than one item.

## Error Codes

| Code                                | When it occurs                                                   |
|-------------------------------------|------------------------------------------------------------------|
| `INVALID_MESSAGE_FORMAT_ERROR`      | The action command JSON is malformed or missing required fields. |
| `INVALID_EVENT_TYPE_ERROR`          | An event string does not match any known event type.             |
| `ALREADY_SUBSCRIBED_TO_EVENT_ERROR` | `subscribe` was called for an event already subscribed to.       |
| `NOT_SUBSCRIBED_TO_EVENT_ERROR`     | `unsubscribe` was called for an event not subscribed to.         |

!!! warning
    `subscribe` and `unsubscribe` validate **all** events in the list before applying
    any changes. If any event fails validation the entire command is rejected, no
    subscriptions are changed.

## Available Events

Use the identifiers from the
[framework event catalog](../../framework-api/event-hooks/event-types.md), including
agent, listener, task, user-session and resource events. Event strings are uppercase
and case-sensitive. Query `get_all_events` for the identifiers supported by the
connected server.

## Subscribing to Events

Building on the script from [authentication](authentication.md#putting-it-all-together):

```py title="subscribe_to_events.py"
import asyncio
import json

import requests
import websockets

USERNAME = "admin"
PASSWORD = "admin"
AUTHORIZATION_URL = "http://localhost:9999/api/login"
TICKET_URL = "http://localhost:9999/api/ws/ticket"
EVENTS_API_URL = "ws://localhost:9999/api/ws/events"


def get_jwt(username: str, password: str, authorization_url: str) -> str:
    response = requests.post(
        authorization_url, data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def get_ticket(jwt: str, ticket_url: str) -> str:
    response = requests.post(ticket_url, headers={"Authorization": f"Bearer {jwt}"})
    response.raise_for_status()
    return response.json()["ticket"]


async def receive_response(ws, on_event) -> dict:
    while True:
        message = json.loads(await ws.recv())
        if message["type"] == "response":
            return message
        if message["type"] == "event":
            on_event(message)


def on_event(message: dict) -> None:
    print(f"Event received: {message}")


async def main() -> None:
    jwt = get_jwt(USERNAME, PASSWORD, AUTHORIZATION_URL)
    ticket = get_ticket(jwt, TICKET_URL)

    async with websockets.connect(f"{EVENTS_API_URL}?ticket={ticket}") as ws:
        await ws.send(json.dumps({
            "action": "subscribe",
            "events": ["START_SERVER", "STOP_SERVER"],
        }))
        response = await receive_response(ws, on_event)

        if not response["success"]:
            for error in response["errors"]:
                print(f"Error: {error['code']} - {error['message']}")
            return

        print("Subscribed. Waiting for events...")
        async for raw_message in ws:
            message = json.loads(raw_message)
            if message["type"] == "event":
                on_event(message)


if __name__ == "__main__":
    asyncio.run(main())
```

## Unsubscribing from Events

The snippets below reuse `receive_response` and `on_event` from the example above.
Run them from the connection's sole receive loop, before resuming event listening;
do not call `recv()` concurrently from another task.

```py title="unsubscribe_example.py"
await ws.send(json.dumps({
    "action": "unsubscribe",
    "events": ["START_SERVER"],
}))
response = await receive_response(ws, on_event)

if response["success"]:
    print("Unsubscribed successfully.")
else:
    for error in response["errors"]:
        print(f"Error: {error['code']} - {error['message']}")
```

## Querying Subscriptions

```py title="query_subscriptions.py"
async def query_events(ws, action: str) -> list[str]:
    await ws.send(json.dumps({"action": action}))
    response = await receive_response(ws, on_event)
    if not response["success"]:
        raise RuntimeError(response["errors"])
    return response["data"]


# All events the API supports
all_events = await query_events(ws, "get_all_events")
print("All events:", all_events)

# Events this connection is subscribed to
subscribed = await query_events(ws, "get_subscribed_events")
print("Subscribed:", subscribed)

# Events this connection is not subscribed to
not_subscribed = await query_events(ws, "get_unsubscribed_events")
print("Not subscribed:", not_subscribed)
```

## Responding to Events

Events arrive on the same websocket as action command responses, so your receive loop
must distinguish between them using the `type` field (`"event"` vs `"response"`). There
are two common approaches.

### Approach 1: One websocket per event type

Open a separate connection for each event. Every pushed event on that connection
has the subscribed type, so it needs only one event handler. Action responses still
arrive on the same connection and must be distinguished from events. Each connection
mints its own ticket: a ticket authenticates one handshake only.

```py title="one_ws_per_event.py"
import asyncio
import json

import requests
import websockets

USERNAME = "admin"
PASSWORD = "admin"
AUTHORIZATION_URL = "http://localhost:9999/api/login"
TICKET_URL = "http://localhost:9999/api/ws/ticket"
EVENTS_API_URL = "ws://localhost:9999/api/ws/events"


def get_jwt(username: str, password: str, authorization_url: str) -> str:
    return requests.post(
        authorization_url, data={"username": username, "password": password}
    ).json()["access_token"]


def get_ticket(jwt: str, ticket_url: str) -> str:
    response = requests.post(ticket_url, headers={"Authorization": f"Bearer {jwt}"})
    response.raise_for_status()
    return response.json()["ticket"]


async def listen_for_event(jwt: str, event_type: str) -> None:
    ticket = get_ticket(jwt, TICKET_URL)  # (1)

    async with websockets.connect(f"{EVENTS_API_URL}?ticket={ticket}") as ws:
        await ws.send(json.dumps({"action": "subscribe", "events": [event_type]}))
        async for raw_message in ws:
            message = json.loads(raw_message)
            if message["type"] == "response":
                if not message["success"]:
                    raise RuntimeError(message["errors"])
            elif message["type"] == "event":
                print(f"[{event_type}] {message}")


async def main() -> None:
    jwt = get_jwt(USERNAME, PASSWORD, AUTHORIZATION_URL)
    await asyncio.gather(
        listen_for_event(jwt, "START_SERVER"),
        listen_for_event(jwt, "STOP_SERVER"),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

1. Obtained inside `listen_for_event` rather than passed in, so each connection gets its
   own ticket. Sharing one ticket between the two connections would get the second one
   rejected.

### Approach 2: Single websocket with a dispatcher

Use one connection and route incoming events to handlers by event type. More efficient
when subscribing to many events.

```py title="event_dispatcher.py"
import asyncio
import json
from collections.abc import Callable

import requests
import websockets

USERNAME = "admin"
PASSWORD = "admin"
AUTHORIZATION_URL = "http://localhost:9999/api/login"
TICKET_URL = "http://localhost:9999/api/ws/ticket"
EVENTS_API_URL = "ws://localhost:9999/api/ws/events"

EventHandler = Callable[[dict], None]


def get_jwt(username: str, password: str, authorization_url: str) -> str:
    return requests.post(
        authorization_url, data={"username": username, "password": password}
    ).json()["access_token"]


def get_ticket(jwt: str, ticket_url: str) -> str:
    response = requests.post(ticket_url, headers={"Authorization": f"Bearer {jwt}"})
    response.raise_for_status()
    return response.json()["ticket"]


def on_start_server(event: dict) -> None:
    print("Server started:", event)


def on_stop_server(event: dict) -> None:
    print("Server stopped:", event)


async def listen(jwt: str, handlers: dict[str, EventHandler]) -> None:
    ticket = get_ticket(jwt, TICKET_URL)

    async with websockets.connect(f"{EVENTS_API_URL}?ticket={ticket}") as ws:
        await ws.send(json.dumps({
            "action": "subscribe",
            "events": list(handlers.keys()),
        }))
        async for raw_message in ws:
            message = json.loads(raw_message)
            if message["type"] == "response":
                if not message["success"]:
                    raise RuntimeError(message["errors"])
                continue
            if message["type"] != "event":
                continue
            event_type = message["event_type"]
            handler = handlers.get(event_type)
            if handler:
                handler(message)


async def main() -> None:
    jwt = get_jwt(USERNAME, PASSWORD, AUTHORIZATION_URL)
    await listen(jwt, {
        "START_SERVER": on_start_server,
        "STOP_SERVER": on_stop_server,
    })


if __name__ == "__main__":
    asyncio.run(main())
```

Approach 1 is simpler and appropriate for a small number of events. Approach 2 scales
better when subscribing to many events or when the overhead of multiple connections
matters.
