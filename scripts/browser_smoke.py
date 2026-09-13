"""UI end-to-end checks using Chrome DevTools Protocol and the installed browser."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import httpx
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
URL="http://127.0.0.1:8012"

class Browser:
    def __init__(self,url):
        self.socket=connect(url,origin="http://localhost",max_size=20*1024*1024)
        self.sequence=0
        self.errors=[]
        self.call("Page.enable")
        self.call("Runtime.enable")

    def call(self,method,params=None):
        self.sequence+=1
        self.socket.send(json.dumps({"id":self.sequence,"method":method,"params":params or {}}))
        while True:
            message=json.loads(self.socket.recv(timeout=30))
            if message.get("method")=="Runtime.exceptionThrown":
                self.errors.append(message["params"]["exceptionDetails"].get("text","Browser exception"))
            if message.get("id")==self.sequence:
                if "error" in message:raise RuntimeError(message["error"])
                return message.get("result",{})

    def js(self,expression):
        result=self.call("Runtime.evaluate",{"expression":expression,"returnByValue":True,"awaitPromise":True})
        if result.get("exceptionDetails"):raise RuntimeError(result["exceptionDetails"])
        return result.get("result",{}).get("value")

    def wait(self,expression,timeout=30):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self.js(expression):return
            time.sleep(.15)
        raise AssertionError("Timed out: "+expression)

    def click(self,selector):
        self.js("document.querySelector("+json.dumps(selector)+").click()")

    def fill(self,selector,value):
        self.js("(()=>{const e=document.querySelector("+json.dumps(selector)+");e.value="+json.dumps(value)+";e.dispatchEvent(new Event('input',{bubbles:true}));})()")

    def select(self,selector,value):
        self.fill(selector,value)
        self.js("document.querySelector("+json.dumps(selector)+").dispatchEvent(new Event('change',{bubbles:true}))")

    def viewport(self,width,height):
        self.call("Emulation.setDeviceMetricsOverride",{"width":width,"height":height,"deviceScaleFactor":1,"mobile":False})

    def screenshot(self,name):
        metrics=self.call("Page.getLayoutMetrics")["cssContentSize"]
        result=self.call("Page.captureScreenshot",{"format":"png","captureBeyondViewport":True,
            "clip":{"x":0,"y":0,"width":metrics["width"],"height":metrics["height"],"scale":1}})
        (ROOT/"docs"/name).write_bytes(base64.b64decode(result["data"]))

def launch(args,env=None):
    return subprocess.Popen(args,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)

def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

def main():
    with tempfile.TemporaryDirectory(prefix="peopleops-browser-",ignore_cleanup_errors=True) as tmp:
        env={**os.environ,"HR_DB_PATH":str(Path(tmp)/"ui.db"),"PYTHONIOENCODING":"utf-8"}
        server=launch([sys.executable,str(ROOT/"src/web.py"),"--port","8012"],env)
        chrome=None
        try:
            for _ in range(100):
                if server.poll() is not None:raise RuntimeError("Test server exited; check port 8012.")
                try:
                    if httpx.get(URL+"/api/state",timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError("Test server did not start.")
            candidates=[Path(os.environ.get("PROGRAMFILES","C:/Program Files"))/"Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)","C:/Program Files (x86)"))/"Microsoft/Edge/Application/msedge.exe"]
            executable=next((p for p in candidates if p.exists()),None)
            if not executable:raise RuntimeError("Chrome or Edge is required for this Windows browser smoke test.")
            chrome=launch([str(executable),"--headless=new","--remote-debugging-port=9225","--remote-debugging-address=127.0.0.1",
                "--remote-allow-origins=http://localhost","--user-data-dir="+str(Path(tmp)/"browser"),
                "--no-first-run","--no-default-browser-check","about:blank"])
            for _ in range(100):
                try:
                    targets=httpx.get("http://127.0.0.1:9225/json/list",timeout=1).json()
                    page=next(t for t in targets if t["type"]=="page")
                    break
                except (httpx.HTTPError,StopIteration):time.sleep(.2)
            else:raise RuntimeError("Browser did not start.")
            b=Browser(page["webSocketDebuggerUrl"])
            b.viewport(1440,1100)
            b.call("Page.navigate",{"url":URL})
            b.wait("document.querySelector('#available-days')?.textContent==='12'")
            assert b.js("document.documentElement.scrollWidth<=innerWidth")
            b.screenshot("ui-demo.png")
            b.select("#provider-mode","mock")
            b.click('[data-prompt="balance"]')
            b.wait("document.querySelector('#trace-state').textContent==='Hoàn tất'")
            assert b.js("document.querySelector('.message.assistant .bubble').textContent.includes('12 ngày')")
            assert b.js("document.querySelector('#trace-calls').textContent==='1'")
            b.click("#new-chat")
            b.click('[data-prompt="create"]')
            b.fill("#leave-reason","việc gia đình")
            b.click('#leave-form button[type="submit"]')
            b.wait("document.querySelector('#trace-state').textContent==='Hoàn tất'")
            b.wait("document.querySelector('#available-days').textContent==='9'")
            assert b.js("document.querySelector('#pending-count').textContent==='1'")
            assert b.js("document.querySelector('.message.assistant .bubble').textContent.includes('PENDING')")
            b.js("document.querySelectorAll('details.observation')[2].open=true")
            b.screenshot("ui-trace.png")
            b.call("Browser.setDownloadBehavior",{"behavior":"allow","downloadPath":tmp})
            b.click("#download-trace")
            for _ in range(100):
                downloads=list(Path(tmp).glob("peopleops-trace-*.json"))
                if downloads:break
                time.sleep(.1)
            assert downloads,"Trace download missing"
            trace=json.loads(downloads[0].read_text(encoding="utf-8"))
            assert trace["tool_calls"]==3 and trace["live"] is False
            b.click('[data-page="requests"]')
            b.wait("document.querySelectorAll('#request-table tbody tr').length===1")
            b.select("#employee-filter","NV003")
            assert b.js("!!document.querySelector('.empty-table')")
            b.click('[data-page="policies"]')
            assert b.js("document.querySelectorAll('.policy-card').length===4")
            b.click('[data-page="presentation"]')
            assert b.js("document.querySelectorAll('.fit-card').length===4")
            b.click('[data-page="assistant"]')
            b.click('[data-agent-mode="baseline"]')
            b.fill("#message-input","Hãy tra cứu quỹ phép NV001.")
            b.click("#send-button")
            b.wait("document.querySelector('#trace-state').textContent==='Hoàn tất'")
            assert b.js("document.querySelector('#trace-calls').textContent==='0'")
            # Simulate a lost chat connection; keep state endpoints functional.
            b.js("window.originalFetch=window.fetch;window.fetch=(url,...args)=>url==='/api/chat'?Promise.reject(new TypeError('Failed to fetch')):window.originalFetch(url,...args)")
            b.fill("#message-input","Xin chào")
            b.click("#send-button")
            b.wait("document.querySelector('#trace-state').textContent==='Có lỗi'")
            b.wait("!document.querySelector('#send-button').disabled")
            b.js("window.fetch=window.originalFetch")
            b.viewport(390,844)
            b.click('[data-agent-mode="agent"]')
            for section in ("assistant","requests","policies","presentation"):
                b.click('[data-page="'+section+'"]')
                assert b.js("document.documentElement.scrollWidth<=innerWidth"),section
            b.click('[data-page="assistant"]')
            b.screenshot("ui-mobile.png")
            b.click("#hero-create")
            assert b.js("document.querySelector('#leave-dialog').open")
            b.click("#close-dialog")
            assert not b.errors,b.errors
            report={"status":"passed","browser":executable.name,"checks":["desktop layout","lookup","create request","balance refresh",
                "trace details","JSON download","request filter","policies","presentation","baseline has no tools",
                "network error recovery","mobile navigation and overflow","mobile form"],"console_errors":b.errors}
            (ROOT/"docs/browser-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print(json.dumps(report))
            b.call("Browser.close")
            b.socket.close()
            chrome.wait(timeout=10)
        finally:
            stop(chrome)
            stop(server)

if __name__=="__main__":main()
