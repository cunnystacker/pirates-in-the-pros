"""Screenshots of the built site (desktop + mobile). Usage: .venv/bin/python scripts/screenshots.py"""
import os, http.server, threading, functools
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
srv=http.server.ThreadingHTTPServer(("127.0.0.1",8765),functools.partial(http.server.SimpleHTTPRequestHandler,directory=os.path.join(ROOT,"site")))
threading.Thread(target=srv.serve_forever,daemon=True).start()
pages={"home":"index.html","player-carter-cunningham":"players/carter-cunningham-701860.html"}
os.makedirs(os.path.join(ROOT,"screenshots"),exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    for dev,opts in {"desktop":dict(viewport={"width":1366,"height":900}),"mobile":dict(viewport={"width":390,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True)}.items():
        ctx=b.new_context(**opts); pg=ctx.new_page()
        for name,path in pages.items():
            pg.goto(f"http://127.0.0.1:8765/{path}"); pg.wait_for_load_state("networkidle")
            out=os.path.join(ROOT,"screenshots",f"{name}-{dev}.png"); pg.screenshot(path=out,full_page=True); print(out)
        ctx.close()
    b.close()
srv.shutdown()
