import backend.server as server


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction=1):
        self._docs.sort(key=lambda d: (d.get(key) or ""), reverse=(direction == -1))
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self._docs)
        return self._docs[:length]


class _FakeCollection:
    """In-memory mini Mongo collection supporting the helpers under test."""

    def __init__(self, docs=None):
        self._docs = list(docs or [])

    def _match(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    async def find_one(self, query, projection=None):
        for d in self._docs:
            if self._match(d, query):
                out = dict(d)
                if projection and "_id" in projection:
                    out.pop("_id", None)
                return out
        return None

    def find(self, query, projection=None):
        docs = list(self._docs)
        if projection:
            docs = [
                {k: v for k, v in d.items() if k == "_id" or projection.get(k, 1)}
                for d in docs
            ]
        return _Cursor([d for d in docs if self._match(d, query)])

    async def insert_one(self, doc):
        self._docs.append(dict(doc))
        return type("_r", (), {"inserted_id": None})()


class _FakeDB:
    def __init__(self):
        self.users = _FakeCollection()
        self.user_sessions = _FakeCollection()
        self.user_settings = _FakeCollection()
        self.memories = _FakeCollection()
        self.conversations = _FakeCollection()
        self.messages = _FakeCollection()


class _FakeRequest:
    def __init__(self, origin=None, cookies=None, hostname="localhost", port=8000):
        self.headers = _FakeHeaders(origin)
        self.cookies = cookies or {}
        if origin is not None or hostname:
            self.url = _FakeURL(hostname, port)

    async def body(self):
        return b""


class _FakeHeaders:
    def __init__(self, origin):
        self._origin = origin

    def get(self, key, default=None):
        return self._origin if key.lower() == "origin" else default


class _FakeURL:
    def __init__(self, hostname, port):
        self.hostname = hostname
        self.port = port