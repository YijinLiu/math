# Based on code from https://github.com/xtermjs/xterm.js/tree/master/demo

from absl import app
from absl import flags
import aiohttp
from aiohttp import web, WSCloseCode
import asyncio
import json
import logging
import os
from ptyprocess import PtyProcess, PtyProcessUnicode
import threading

FLAGS = flags.FLAGS
flags.DEFINE_string("host", "", "")
flags.DEFINE_integer("port", 8000, "")
flags.DEFINE_boolean("share_sess", True, "");
flags.DEFINE_integer("log_level", logging.INFO, "");

logger = logging.getLogger(__name__)

class WsPty:
    def __init__(self):
        shell = os.environ.get("SHELL", "/bin/bash")
        self._proc = PtyProcessUnicode.spawn([shell])
        self._ws_list = []
        self._thread = threading.Thread(target=self._read_in_thread, daemon=True)
        self._thread.start()

    async def add_ws(self, ws: web.WebSocketResponse):
        self._ws_list.append(ws)
        self.write("\n")

    async def _read_loop(self):
        while True:
            try:
                text = self._proc.read()
            except:
                break
            logging.debug("[O] %s", text)
            bad_ws_list = []
            for ws in self._ws_list:
                try:
                    await ws.send_str(text)
                except:
                    bad_ws_list.append(ws)
            for ws in bad_ws_list:
                self._ws_list.remove(ws)

    def _read_in_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._read_loop())

    def write(self, data):
        self._proc.write(data)

    def setwinsize(self, rows: int, cols: int):
        self._proc.setwinsize(rows, cols)

    def close(self):
        self._proc.close()
        self._thread.join()

shared_ws_pty = None

async def ws_handler(req: web.Request) -> web.Response:
    resp = web.WebSocketResponse()
    await resp.prepare(req)

    global shared_ws_pty
    ws_pty = None
    if not FLAGS.share_sess or not shared_ws_pty:
        ws_pty = WsPty()
        if FLAGS.share_sess:
            shared_ws_pty = ws_pty
    if FLAGS.share_sess:
        ws_pty = shared_ws_pty
    await ws_pty.add_ws(resp)

    async for msg in resp:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == "close":
                logging.warning("Closing PTY...")
                if not FLAGS.share_sess:
                    ws_pty.close()
                await resp.close()
            else:
                logging.debug("[I] %s", msg.data)
                ws_pty.write(msg.data)
        elif msg.type == aiohttp.WSMsgType.BINARY:
            cmd = json.loads(msg.data)
            logging.info("Received command %s", cmd)
            cmd_name = cmd["command"]
            if cmd_name == "resize":
                ws_pty.setwinsize(cmd["rows"], cmd["cols"])
            else:
                logging.warning("Unknown command %s", cmd_name)
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logging.warning("Websocket connection closed with exception %s", resp.exception())
            if not FLAGS.share_sess:
                ws_pty.close()

    return resp

async def start_server():
    webApp = web.Application()
    webApp.add_routes([
        web.static('/html', './html'),
        web.get('/ws', ws_handler),
    ])
    runner = web.AppRunner(webApp)
    await runner.setup()
    site = web.TCPSite(runner, FLAGS.host, FLAGS.port)
    logging.info("Running HTTP server @%s:%s ...", FLAGS.host, FLAGS.port)
    await site.start()

def main(argv):
    logger.setLevel(FLAGS.log_level)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server())
    loop.run_forever()

app.run(main)
