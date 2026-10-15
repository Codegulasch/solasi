"""Winziger MQTT-Broker für Tests (QoS 0): merkt sich Veröffentlichungen und kann Nachrichten senden."""
import asyncio


def _len(r):
    mult, n = 1, 0
    while True:
        b = r[0]
        r = r[1:]
        n += (b & 0x7F) * mult
        mult *= 128
        if not b & 0x80:
            return n, r


class FakeBroker:
    def __init__(self, user="", password=""):
        self.user, self.password = user, password
        self.published = []        # (topic, payload, retain)
        self.retained = {}
        self.subs = []
        self.connects = []
        self.writers = []
        self.server = None
        self.port = None
        self.pings = 0

    async def start(self):
        self.server = await asyncio.start_server(self._client, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self):
        for w in self.writers:
            w.close()
        self.server.close()
        await self.server.wait_closed()

    def drop(self):
        for w in self.writers:
            w.close()

    async def send(self, topic, payload):
        t = topic.encode()
        body = len(t).to_bytes(2, "big") + t + payload.encode()
        for w in self.writers:
            w.write(bytes([0x30, len(body)]) + body if len(body) < 128 else bytes([0x30, (len(body) % 128) | 0x80, len(body) // 128]) + body)
            await w.drain()

    @staticmethod
    def _s(b):
        n = int.from_bytes(b[:2], "big")
        return b[2:2 + n].decode(), b[2 + n:]

    async def _client(self, r, w):
        self.writers.append(w)
        try:
            while True:
                first = (await r.readexactly(1))[0]
                mult, length = 1, 0
                while True:
                    b = (await r.readexactly(1))[0]
                    length += (b & 0x7F) * mult
                    mult *= 128
                    if not b & 0x80:
                        break
                data = await r.readexactly(length) if length else b""
                kind = first >> 4
                if kind == 1:
                    _, rest = self._s(data)
                    flags = rest[1]
                    rest = rest[4:]
                    cid, rest = self._s(rest)
                    will = None
                    if flags & 0x04:
                        wt, rest = self._s(rest)
                        wm, rest = self._s(rest)
                        will = (wt, wm)
                    user = pw = ""
                    if flags & 0x80:
                        user, rest = self._s(rest)
                    if flags & 0x40:
                        pw, rest = self._s(rest)
                    ok = (user == self.user and pw == self.password)
                    self.connects.append({"id": cid, "user": user, "password": pw, "will": will, "ok": ok})
                    w.write(bytes([0x20, 2, 0, 0 if ok else 4]))
                    await w.drain()
                    if not ok:
                        return
                elif kind == 3:
                    topic, payload = self._s(data)
                    self.published.append((topic, payload.decode(), bool(first & 1)))
                    self.retained[topic] = payload.decode()
                elif kind == 8:
                    pid = data[:2]
                    topic, _ = self._s(data[2:])
                    self.subs.append(topic)
                    w.write(bytes([0x90, 3]) + pid + b"\x00")
                    await w.drain()
                elif kind == 12:
                    self.pings += 1
                    w.write(b"\xd0\x00")
                    await w.drain()
                elif kind == 14:
                    return
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
