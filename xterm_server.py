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
flags.DEFINE_integer("log_level", logging.INFO, "");

logger = logging.getLogger(__name__)

async def read_shell(proc: PtyProcess, resp: web.WebSocketResponse):
    while True:
        text = proc.read()
        logging.debug("[O] %s", text)
        await resp.send_str(text)

def read_shell_in_thread(proc: PtyProcess, resp: web.WebSocketResponse):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(read_shell(proc, resp))

async def ws_handler(req: web.Request) -> web.Response:
    resp = web.WebSocketResponse()
    await resp.prepare(req)

    shell = os.environ.get("SHELL", "/bin/bash")
    proc = PtyProcessUnicode.spawn([shell])

    thread = threading.Thread(target=read_shell_in_thread, args=(proc, resp), daemon=True)
    thread.start()

    async for msg in resp:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == "close":
                logging.warning("Closing PTY...")
                proc.close()
                await resp.close()
            else:
                logging.debug("[I] %s", msg.data)
                proc.write(msg.data)
        elif msg.type == aiohttp.WSMsgType.BINARY:
            cmd = json.loads(msg.data)
            logging.info("Received command %s", cmd)
            cmd_name = cmd["command"]
            if cmd_name == "resize":
                proc.setwinsize(cmd["rows"], cmd["cols"])
            else:
                logging.warning("Unknown command %s", cmd_name)
        elif msg.type == aiohttp.WSMsgType.ERROR:
            proc.close()
            logging.warning("Websocket connection closed with exception %s", resp.exception())

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
