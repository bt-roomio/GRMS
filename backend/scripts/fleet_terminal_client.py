#!/usr/bin/env python3
"""
Interactive terminal client for a fleet node — the reference implementation of
the wire protocol the frontend must speak.

    python scripts/fleet_terminal_client.py <node_id> --token <jwt>
    python scripts/fleet_terminal_client.py <node_id> --email you@example.com --password ...

Protocol, exactly as the consumer expects it:
  * binary frames  -> raw PTY bytes, both directions, no base64
  * text frames    -> JSON control only: {"type": "resize", "cols": N, "rows": N}
                      and, inbound, {"type": "error"|"exit", ...}

Ctrl-] quits the client without touching the remote shell.
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import termios
import tty

import requests
import websockets

QUIT = b"\x1d"  # Ctrl-]

HANDSHAKE_REJECTED = tuple(
    exc
    for exc in (
        getattr(websockets.exceptions, "InvalidStatusCode", None),
        getattr(websockets.exceptions, "InvalidStatus", None),
    )
    if exc is not None
)

CLOSE_REASONS = {
    4403: "Not allowed — you lack fleet.terminal_fleetnode, or you are not logged in.",
    4404: "No such node for your tenant.",
    4503: "The node could not be reached over the mesh.",
    4526: "SSH host key mismatch — refused. The VM's identity changed.",
    4500: "Server error opening the shell. Check the Django log.",
}


def login(api, email, password):
    response = requests.post(
        f"{api}/api/v1/users/access-token/", json={"email": email, "password": password}, timeout=15
    )
    response.raise_for_status()
    body = response.json()
    for key in ("access", "access_token", "token"):
        if body.get(key):
            return body[key]
    raise SystemExit(f"Could not find an access token in the login response: {list(body)}")


async def pump_stdout(ws):
    async for frame in ws:
        if isinstance(frame, bytes):
            sys.stdout.buffer.write(frame)
            sys.stdout.buffer.flush()
            continue

        message = json.loads(frame)
        if message.get("type") == "error":
            print(f"\r\n[server] {message.get('message')}\r", flush=True)
        elif message.get("type") == "exit":
            print(f"\r\n[shell exited: {message.get('status')}]\r", flush=True)
            return


async def pump_stdin(ws):
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)

    while True:
        data = await reader.read(1024)
        if not data or QUIT in data:
            return
        await ws.send(data)  # bytes -> binary frame


async def send_resize(ws):
    size = shutil.get_terminal_size((80, 24))
    await ws.send(json.dumps({"type": "resize", "cols": size.columns, "rows": size.lines}))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("node_id")
    parser.add_argument("--api", default=os.getenv("FLEET_API", "http://localhost:9000"))
    parser.add_argument("--token", default=os.getenv("FLEET_TOKEN"))
    parser.add_argument("--email")
    parser.add_argument("--password")
    # config/asgi.py wraps the router in AllowedHostsOriginValidator, which
    # rejects a handshake that carries no Origin at all. Browsers always send
    # one; a CLI client has to say it explicitly.
    parser.add_argument("--origin", default=None, help="defaults to --api")
    args = parser.parse_args()

    token = args.token
    if not token:
        if not (args.email and args.password):
            raise SystemExit("Pass --token, or --email and --password.")
        token = login(args.api, args.email, args.password)

    ws_url = args.api.replace("https://", "wss://").replace("http://", "ws://")
    url = f"{ws_url}/api/ws/v2/fleet/terminal/{args.node_id}/?token={token}"
    print(f"connecting to {url.split('?')[0]} ...")

    try:
        async with websockets.connect(url, max_size=None, origin=args.origin or args.api) as ws:
            print("connected. Ctrl-] to quit.\r")
            await send_resize(ws)

            stdin_fd = sys.stdin.fileno()
            saved = termios.tcgetattr(stdin_fd)
            try:
                tty.setraw(stdin_fd)
                done, pending = await asyncio.wait(
                    [asyncio.create_task(pump_stdout(ws)), asyncio.create_task(pump_stdin(ws))],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
            finally:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, saved)
    except HANDSHAKE_REJECTED as exc:
        # websockets 12 raises InvalidStatusCode; 13+ raises InvalidStatus.
        status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", "?")
        raise SystemExit(f"HTTP {status} — is the path right and the token valid?") from exc
    except websockets.exceptions.ConnectionClosed as exc:
        print(f"\nclosed: {exc.code} — {CLOSE_REASONS.get(exc.code, exc.reason or 'no reason given')}")


if __name__ == "__main__":
    asyncio.run(main())
