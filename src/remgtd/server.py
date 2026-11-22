"""Local server: polls Reminders through RemCTL and pushes state to the View over SSE.

Binds to 127.0.0.1 only. Requests must carry a localhost Host header (guards
against DNS rebinding), and /open needs a custom header, which cross-site pages
can't send without a CORS preflight that this server never answers.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import subprocess
from datetime import datetime
from importlib import resources
from typing import Any, AsyncIterator, Callable

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import guide, model, rules, snapshot, state
from .config import Config
from .remctl import Remctl, RemctlError

META = "__meta__"  # rotation step that refreshes lists and smart lists


class Poller:
    def __init__(
        self,
        cfg: Config,
        rc: Remctl,
        interval: float = 0.5,
        idle_interval: float = 30.0,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.cfg = cfg
        self.clock = clock
        self.rc = rc
        self.interval = interval
        self.idle_interval = idle_interval
        self.state: dict[str, Any] | None = None
        self.payload: str = ""
        self.version = 0
        self.clients: set[asyncio.Queue[str]] = set()
        self._wake = asyncio.Event()
        self._fingerprint = ""
        self._lists: list[dict[str, Any]] | None = None
        self._smart: list[dict[str, Any]] = []
        self._sections: dict[str, dict[int, str]] = {}
        self._step = 0
        self.links: dict[int, str] = {}

    # --- clients -------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=4)
        self.clients.add(queue)
        self._wake.set()
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self.clients.discard(queue)

    def _publish(self, new_state: dict[str, Any]) -> None:
        body = {k: v for k, v in new_state.items() if k != "generatedAt"}
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
        if fingerprint == self._fingerprint:
            return
        self._fingerprint = fingerprint
        self.state = new_state
        self.version += 1
        self.payload = json.dumps(new_state, ensure_ascii=False, default=str)
        for queue in list(self.clients):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()  # drop the stale update; the newest wins
            queue.put_nowait(self.payload)

    # --- reading -------------------------------------------------------------

    async def tick(self) -> None:
        call = asyncio.to_thread
        if self._lists is None:
            self._lists = await call(self.rc.lists)
            self._smart = await call(self.rc.smart_lists)
            for title in snapshot.sectioned_list_titles(self.cfg, self._lists):
                self._sections[title] = snapshot.sections_from_show(await call(self.rc.show, title))
        else:
            titles = snapshot.sectioned_list_titles(self.cfg, self._lists)
            rotation = [META, *titles]
            step = rotation[self._step % len(rotation)]
            self._step += 1
            if step == META:
                self._lists = await call(self.rc.lists)
                self._smart = await call(self.rc.smart_lists)
                live = set(snapshot.sectioned_list_titles(self.cfg, self._lists))
                self._sections = {t: s for t, s in self._sections.items() if t in live}
            else:
                self._sections[step] = snapshot.sections_from_show(await call(self.rc.show, step))
        reminders = await call(self.rc.export)
        merged: dict[int, str] = {}
        for sections in self._sections.values():
            merged.update(sections)
        snap = snapshot.Snapshot(reminders=reminders, lists=self._lists, smart_lists=self._smart, sections=merged)
        m = model.build(snap, self.cfg)
        self.links = {i.id: i.deep_link for i in m.items.values() if i.is_open and i.role and i.deep_link}
        now = self.clock()
        self._publish(state.build(m, rules.check(m, now), now))

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except RemctlError as exc:
                self._publish(state.error(str(exc), self.state if self.state and self.state.get("ok") else None))
            except Exception as exc:  # keep serving; surface the problem in the View
                self._publish(state.error(f"{type(exc).__name__}: {exc}", self.state))
            delay = self.interval if self.clients else self.idle_interval
            self._wake.clear()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._wake.wait(), timeout=delay)


def _web(name: str) -> str:
    return str(resources.files("remgtd") / "web" / name)


def create_app(
    cfg: Config,
    rc: Remctl,
    *,
    opener: Callable[[str], None] | None = None,
    start_polling: bool = True,
    poller: Poller | None = None,
) -> Starlette:
    poller = poller or Poller(cfg, rc)
    open_url = opener or (lambda url: subprocess.run(["open", url], check=False))

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        task = asyncio.create_task(poller.run()) if start_polling else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    async def index(request: Request) -> Response:
        return FileResponse(_web("index.html"), headers={"Cache-Control": "no-store"})

    async def health(request: Request) -> Response:
        return JSONResponse({"ok": True, "app": "remgtd", "version": poller.version})

    async def guide_json(request: Request) -> Response:
        return JSONResponse(guide.cards())

    async def state_json(request: Request) -> Response:
        if poller.state is None:
            return JSONResponse({"ok": False, "error": "Loading…"}, status_code=503)
        return Response(poller.payload, media_type="application/json")

    async def events(request: Request) -> Response:
        queue = poller.subscribe()

        async def stream() -> AsyncIterator[str]:
            try:
                if poller.payload:
                    yield f"event: state\ndata: {poller.payload}\n\n"
                while True:
                    try:
                        payload = await asyncio.wait_for(queue.get(), timeout=15)
                        yield f"event: state\ndata: {payload}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                poller.unsubscribe(queue)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    async def open_item(request: Request) -> Response:
        if request.headers.get("x-remgtd") != "1":
            return JSONResponse({"ok": False, "error": "missing header"}, status_code=403)
        link = poller.links.get(request.path_params["id"])
        if not link:
            return JSONResponse({"ok": False, "error": "unknown item"}, status_code=404)
        await asyncio.to_thread(open_url, link)
        return JSONResponse({"ok": True})

    return Starlette(
        routes=[
            Route("/", index),
            Route("/health", health),
            Route("/state.json", state_json),
            Route("/guide.json", guide_json),
            Route("/events", events),
            Route("/open/{id:int}", open_item, methods=["POST"]),
            Mount("/static", StaticFiles(directory=_web("")), name="static"),
        ],
        middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])],
        lifespan=lifespan,
    )
