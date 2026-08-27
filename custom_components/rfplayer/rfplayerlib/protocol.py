# Modified for the JAM'ALERT Community patch: reliable RFPlayer JAMMING diagnostics and state handling.
"""Async RfPlayer low-level protocol."""

import asyncio
from collections.abc import Callable
import json
import logging
from typing import Any, cast

_LOGGER = logging.getLogger(__name__)
END_OF_LINE = "\n\r"
PACKET_HEADER_LEN = 5
MINIMUM_SCRIPT = ["FORMAT JSON"]
RfPlayerEventData = dict[str, Any]

def _valid_packet(line: str): return len(line) >= PACKET_HEADER_LEN
def _command_error(line: str): return line.startswith(("error request number", "Syntax error:"))

class RfplayerProtocol(asyncio.Protocol):
    def __init__(self, loop: asyncio.AbstractEventLoop, event_callback: Callable[[RfPlayerEventData], None], disconnect_callback: Callable[[Exception | None], None], init_script: list[str] | None, verbose: bool) -> None:
        self.loop = loop
        self.transport: asyncio.WriteTransport | None = None
        self.event_callback = event_callback
        self.disconnect_callback = disconnect_callback
        complete_init_script = list(MINIMUM_SCRIPT)
        complete_init_script.extend(init_script or [])
        self.init_script = complete_init_script
        self._init_tasks: set[asyncio.Task] = set()
        self.verbose = verbose
        self.buffer = ""
        self.command_lock = asyncio.Lock()
        self.command_event = asyncio.Event()
        self.response_message = ""
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.WriteTransport, transport)
        _LOGGER.info("RFPLAYER CONNECTED - serial/tcp transport ready")
        for command in self.init_script:
            task = self.loop.create_task(self.send_raw_command(command))
            self._init_tasks.add(task)
            task.add_done_callback(self._init_tasks.discard)
    def data_received(self, data: bytes) -> None:
        try: decoded_data = data.decode()
        except UnicodeDecodeError:
            _LOGGER.warning("Failed to decode received data: %s", data.decode(errors="replace"))
        else:
            if self.verbose: _LOGGER.debug("RFPLAYER RX RAW: %s", decoded_data.rstrip())
            self.buffer += decoded_data
            self.handle_lines()
    def handle_lines(self) -> None:
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip("\0 \t\r")
            if _valid_packet(line):
                if self.verbose: _LOGGER.debug("RFPLAYER PACKET: %s", line)
                self.handle_raw_packet(line)
            elif line: _LOGGER.warning("dropping invalid data: %s", line)
    def handle_raw_packet(self, raw_packet: str) -> None:
        header, body = raw_packet[0:5], raw_packet[5:]
        if header == "ZIA--":
            self.response_message = body
            self.command_event.set()
        elif header == "ZIA33":
            try:
                event_data = cast(RfPlayerEventData, json.loads(body))
                frame = event_data.get("frame", {})
                frame_header = frame.get("header", {}) if isinstance(frame, dict) else {}
                protocol = str(frame_header.get("protocolMeaning", "UNKNOWN"))
                if protocol == "JAMMING": _LOGGER.warning("RFPLAYER JAMMING FRAME: %s", body)
                elif self.verbose: _LOGGER.debug("RFPLAYER EVENT protocol=%s data=%s", protocol, body)
                self.event_callback(event_data)
            except json.JSONDecodeError as e: _LOGGER.warning("Invalid JSON packet: %s", e)
            except Exception: _LOGGER.exception("RFPLAYER EVENT PARSE ERROR raw=%s", body)
        elif header in ["ZIA00", "ZIA11", "ZIA22", "ZIA44", "ZIA66"]:
            _LOGGER.warning("unsupported packet format: %s", header)
            _LOGGER.debug("packet body: %s", body)
        elif _command_error(raw_packet): _LOGGER.warning("Command error: %s", raw_packet)
        else: _LOGGER.warning("dropping invalid packet: %s", raw_packet)
    async def _do_send_raw_command(self, command: str) -> None:
        self.response_message = ""
        self.command_event.clear()
        data = bytes(f"ZIA++{command}{END_OF_LINE}", "utf-8")
        _LOGGER.debug("sending raw packet: %s", repr(data))
        if self.transport: self.transport.write(data)
        else: _LOGGER.warning("Command not sent: not connected")
    async def send_raw_command(self, command: str) -> None:
        async with self.command_lock: await self._do_send_raw_command(command)
    async def send_raw_request(self, request: str) -> str:
        async with self.command_lock:
            await self._do_send_raw_command(command=request)
            async with asyncio.timeout(60):
                await self.command_event.wait()
                return self.response_message[:]
    def connection_lost(self, exc: Exception | None) -> None:
        if exc: _LOGGER.warning("RFPLAYER DISCONNECTED: %s", exc)
        else: _LOGGER.info("RFPLAYER DISCONNECTED")
        self.disconnect_callback(exc)
