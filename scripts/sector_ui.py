#!/usr/bin/env python3
"""sector_ui.py — a small web UI to run the SUPER sector-filter seed verification.

Pick a seed + mode (full / sector / adaptive) + fixed-yaw + GUI, hit Launch: it tears
down, brings up that seed, starts a live collision monitor + RViz, and flies one
perimeter loop (Gazebo GUI optional). Live panel shows phase, corners, collisions and
min-clearance. Stop tears everything down.

  python3 sector_ui.py [--port 8097]   ->  open http://localhost:8097
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
UI_RUN = HERE / "ui_run.sh"
TD = "/tmp/td.sh"
UIDIR = Path("/tmp/sector_ui")
RUN_LOG = UIDIR / "run.log"
COLL_LOG = UIDIR / "coll.log"
STATUS = UIDIR / "status.json"
SESSION = "gsuper"

# seed -> (condition, obstacle radius [m], surface gap [m])
SEED_INFO = {
    1: ("small", 0.15, 1.4), 2: ("small", 0.15, 1.4),
    3: ("baseline", 0.25, 1.4), 4: ("baseline", 0.25, 1.4),
    5: ("large", 0.40, 1.4), 6: ("large", 0.40, 1.4),
    7: ("dense", 0.25, 1.1), 8: ("dense", 0.25, 1.1),
    9: ("sparse", 0.25, 1.8), 10: ("sparse", 0.25, 1.8),
    77: ("dense + corner-clutter", 0.25, 1.1),
}
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 77]
MODES = ["full", "sector", "adaptive"]

HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SUPER Sector Verify</title>
<style>
  :root{color-scheme:dark;--bg:#111318;--panel:#1b1f27;--line:#313846;--text:#eef2f8;
    --muted:#9ca8b8;--accent:#39a7ff;--good:#41d889;--warn:#ffcc66;--bad:#ff7070;}
  *{box-sizing:border-box;} body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);
    font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;}
  main{width:min(980px,calc(100vw - 32px));margin:24px auto;}
  header{display:flex;justify-content:space-between;align-items:end;gap:16px;margin-bottom:18px;}
  h1{margin:0;font-size:23px;font-weight:720;} .sub{color:var(--muted);margin-top:4px;}
  .status{padding:8px 12px;border:1px solid var(--line);border-radius:6px;color:var(--muted);white-space:nowrap;}
  section{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:16px;margin-bottom:14px;}
  h2{margin:0 0 12px;font-size:14px;color:var(--muted);font-weight:680;text-transform:uppercase;letter-spacing:.04em;}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(72px,1fr));gap:8px;}
  button{height:42px;border-radius:6px;border:1px solid var(--line);background:#252b35;color:var(--text);
    font:inherit;cursor:pointer;font-weight:650;} button:hover{border-color:#566274;}
  button.active{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent);color:#dff2ff;}
  button.primary{background:#1267a8;border-color:#278bd5;} button.bad{background:#7a2626;border-color:#d75a5a;}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
  input{height:42px;border-radius:6px;border:1px solid var(--line);background:#252b35;color:var(--text);
    font:inherit;width:110px;padding:0 12px;}
  .kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:4px;}
  .kv div{border:1px solid var(--line);border-radius:6px;padding:10px 12px;background:#151922;}
  .kv span{display:block;color:var(--muted);font-size:12px;} .kv strong{display:block;margin-top:3px;font-size:19px;}
  .kv strong.big{font-size:24px;} .good{color:var(--good);} .warn{color:var(--warn);} .bad{color:var(--bad);}
  pre{min-height:120px;max-height:340px;overflow:auto;margin:0;padding:12px;border-radius:6px;background:#0b0d11;
    border:1px solid var(--line);color:#c9d3df;white-space:pre-wrap;font-size:12.5px;}
  .hint{color:var(--muted);font-size:12.5px;margin-top:8px;}
  label.tog{display:inline-flex;align-items:center;gap:6px;cursor:pointer;}
</style></head><body><main>
<header><div><h1>SUPER Sector Verify</h1>
  <div class="sub">시드 · 모드 · 고정기수 골라서 한 바퀴 검증 (Gazebo GUI + RViz)</div></div>
  <div class="status" id="status">loading</div></header>

<section><h2>1 · 시드</h2><div class="grid" id="seeds"></div>
  <div class="hint" id="seedInfo">-</div></section>

<section><h2>2 · 모드</h2><div class="grid" id="modes" style="grid-template-columns:repeat(3,1fr);max-width:360px;"></div>
  <div class="hint">full=360° · sector=기수고정 콘 · adaptive=속도정렬 콘 (콘이 진행방향 추종)</div></section>

<section><h2>3 · 옵션</h2><div class="row">
  <label class="tog"><input type="checkbox" id="fixedYaw" style="width:auto;height:auto;"> 고정기수(blindspot)</label>
  <input id="fixedYawDeg" type="number" step="15" value="0" title="고정 헤딩 각도 deg(NED)">
  <label class="tog"><input type="checkbox" id="gui" style="width:auto;height:auto;" checked> Gazebo GUI</label>
  </div><div class="hint">고정기수 ON = 기수-속도 분리 → sector에 사각지대 발생 (adaptive가 복구하는 시나리오). full엔 무의미.</div></section>

<section><h2>실행</h2><div class="row">
  <button class="primary" id="launchBtn" onclick="launch()">▶ Launch</button>
  <button class="bad" onclick="stop()">■ Stop (teardown)</button>
  <button onclick="refresh()">새로고침</button></div></section>

<section><h2>라이브 상태</h2><div class="kv">
  <div><span>스택</span><strong id="stack">-</strong></div>
  <div><span>단계</span><strong id="phase">-</strong></div>
  <div><span>코너</span><strong id="corners">-</strong></div>
  <div><span>충돌</span><strong id="coll" class="big">-</strong></div>
  <div><span>최소간격 [m]</span><strong id="clr">-</strong></div>
  <div><span>실행 중</span><strong id="cfg">-</strong></div>
</div></section>

<section><h2>로그</h2><pre id="log"></pre></section>
</main><script>
const seeds=__SEEDS__, modes=__MODES__, seedInfo=__SEEDINFO__;
let selSeed=7, selMode="sector";
function qs(id){return document.getElementById(id);}
async function api(path,body){const o=body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{};
  const r=await fetch(path,o);const d=await r.json();if(!r.ok)throw new Error(d.error||'fail');return d;}
function renderSeeds(){const w=qs('seeds');w.innerHTML='';for(const s of seeds){const b=document.createElement('button');
  b.textContent=s;b.className=s===selSeed?'active':'';b.onclick=()=>{selSeed=s;renderSeeds();showSeed();};w.appendChild(b);}}
function showSeed(){const i=seedInfo[selSeed];qs('seedInfo').textContent=i?`seed ${selSeed}: ${i[0]} · 반경 ${i[1]}m · 간격 ${i[2]}m · 장애물 100개 · 필드 ±15m`:'-';}
function renderModes(){const w=qs('modes');w.innerHTML='';for(const m of modes){const b=document.createElement('button');
  b.textContent=m;b.className=m===selMode?'active':'';b.onclick=()=>{selMode=m;renderModes();};w.appendChild(b);}}
async function launch(){qs('launchBtn').disabled=true;try{
  const d=await api('/api/launch',{seed:selSeed,mode:selMode,fixedYaw:qs('fixedYaw').checked,
    fixedYawDeg:Number(qs('fixedYawDeg').value),gui:qs('gui').checked});
  qs('log').textContent=d.output||'launched';}catch(e){qs('log').textContent=String(e);}
  setTimeout(()=>{qs('launchBtn').disabled=false;},2000);await refresh();}
async function stop(){try{const d=await api('/api/stop',{});qs('log').textContent=d.output||'stopped';}catch(e){qs('log').textContent=String(e);}await refresh();}
function cls(el,c){el.className=c;}
async function refresh(){try{const d=await api('/api/state');
  qs('status').textContent=d.stackUp?'gsuper RUN':'idle';
  qs('stack').textContent=d.stackUp?'UP':'down';cls(qs('stack'),d.stackUp?'good':'muted');
  qs('phase').textContent=d.phase||'-';
  qs('corners').textContent=(d.corners==null?'-':d.corners+' / 4');
  qs('coll').textContent=(d.collisions==null?'-':d.collisions);
  cls(qs('coll'),'big '+(d.collisions==null?'':(d.collisions>0?'bad':'good')));
  qs('clr').textContent=(d.clearance==null?'-':d.clearance.toFixed(3));
  qs('cfg').textContent=d.cfg||'-';
  qs('log').textContent=d.log||'';
}catch(e){qs('status').textContent='error';}}
renderSeeds();renderModes();showSeed();refresh();setInterval(refresh,3000);
</script></body></html>
"""


def sh(cmd: list[str], timeout: float = 12.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, check=False)


def tmux_up() -> bool:
    return subprocess.run(["tmux", "has-session", "-t", SESSION],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          check=False).returncode == 0


def tail(path: Path, n: int = 6000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-n:]


def read_status() -> dict:
    try:
        return json.loads(STATUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def parse_state() -> dict:
    st = read_status()
    run = tail(RUN_LOG)
    coll = tail(COLL_LOG, 4000)
    # phase from the ui_run PHASE= markers
    phases = re.findall(r"PHASE=([a-z+\-]+)", run)
    phase = phases[-1] if phases else ("-" if not run else "starting")
    # corners reached (g_mission logs "CORNER N reached")
    corners = None
    cs = re.findall(r"CORNER\s+\d+\s+reached", run)
    if "PHASE=flying" in run or "PHASE=done" in run:
        corners = len(cs)
    # collisions + clearance from the live collision monitor heartbeat / events
    collisions = None
    clearance = None
    mc = re.findall(r"collisions=(\d+)", coll)
    if mc:
        collisions = int(mc[-1])
    mcl = re.findall(r"clearance so far = ([-\d.]+)", coll)
    if mcl:
        try:
            clearance = float(mcl[-1])
        except ValueError:
            pass
    cfg = "-"
    if st:
        fy = st.get("fixed_yaw", "999.0")
        fytxt = "track-vel" if str(fy).startswith("999") else f"yaw {fy}°"
        cfg = f"seed{st.get('seed')} · {st.get('mode')} · {fytxt} · {'GUI' if st.get('gui') else 'headless'}"
    # combined log view (mission log + last collision line)
    logview = run
    if collisions is not None:
        logview += f"\n--- monitor: collisions={collisions} min_clearance={clearance} ---"
    return {
        "stackUp": tmux_up(), "phase": phase, "corners": corners,
        "collisions": collisions, "clearance": clearance, "cfg": cfg,
        "log": logview[-6000:],
    }


def do_launch(seed: int, mode: str, fixed_yaw_on: bool, fixed_yaw_deg: float, gui: bool) -> dict:
    if seed not in SEEDS:
        return {"error": f"bad seed {seed}"}
    if mode not in MODES:
        return {"error": f"bad mode {mode}"}
    UIDIR.mkdir(parents=True, exist_ok=True)
    RUN_LOG.write_text("", encoding="utf-8")
    COLL_LOG.write_text("", encoding="utf-8")
    fy = f"{float(fixed_yaw_deg):.1f}" if fixed_yaw_on else "999.0"
    args = [str(seed), mode, fy, "1" if gui else "0"]
    log = open(RUN_LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(["bash", str(UI_RUN), *args], cwd=str(HERE),
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    STATUS.write_text(json.dumps({"pid": proc.pid, "seed": seed, "mode": mode,
                                  "fixed_yaw": fy, "gui": gui, "started_at": time.time()}),
                      encoding="utf-8")
    return {"ok": True, "output": f"launched seed{seed} {mode} (fixed_yaw={fy}, gui={gui}) — bringup ~2-3분"}


def do_stop() -> dict:
    p = sh(["bash", TD], timeout=30)
    if STATUS.exists():
        STATUS.unlink()
    return {"ok": True, "output": "teardown 완료\n" + (p.stdout or "")}


class Handler(BaseHTTPRequestHandler):
    server_version = "SectorUI/1.0"

    def log_message(self, *a):  # quiet
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", "0") or "0")
        return json.loads(self.rfile.read(n).decode("utf-8")) if n > 0 else {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            html = (HTML.replace("__SEEDS__", json.dumps(SEEDS))
                    .replace("__MODES__", json.dumps(MODES))
                    .replace("__SEEDINFO__", json.dumps({str(k): v for k, v in SEED_INFO.items()})))
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/state":
            self._json(200, parse_state())
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            p = self._body()
            if path == "/api/launch":
                self._json(200, do_launch(int(p.get("seed", 7)), str(p.get("mode", "sector")),
                                          bool(p.get("fixedYaw", False)), float(p.get("fixedYawDeg", 0.0)),
                                          bool(p.get("gui", True))))
                return
            if path == "/api/stop":
                self._json(200, do_stop())
                return
            self._json(404, {"error": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._json(500, {"error": str(exc)})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8097)
    args = ap.parse_args()
    UIDIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Sector UI: http://localhost:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
