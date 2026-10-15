"""Tiny local chat UI for the bot: python chat.py -> http://127.0.0.1:8000 (API key stays server-side)."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from ask import answer

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>OptiBot</title>
<style>
:root{--g:#4caf91;--g2:#3a9d80;--tx:#2f3440;--mu:#6b7280;--bg:#f6f8fb}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:16px/1.5 system-ui,-apple-system,sans-serif;color:var(--tx);display:flex;justify-content:center}
#app{width:100%;max-width:480px;height:100vh;display:flex;flex-direction:column;background:#fff;padding:20px 22px}
header{display:flex;align-items:center;gap:12px;font-size:26px;font-weight:600}
.av{width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#3cc47c,#4aa8d8);display:flex;align-items:center;justify-content:center;flex:none}
.av svg{width:22px;height:22px;stroke:#fff;fill:none;stroke-width:2}
.sup{display:flex;gap:12px;align-items:center;background:var(--bg);border-radius:14px;padding:12px 16px;margin:18px 0;font-size:14px}
.sup b{display:block;font-weight:500}.sup a{color:var(--g)}
#log{flex:1;overflow:auto;display:flex;flex-direction:column;gap:16px;padding-bottom:8px}
.row{display:flex;gap:12px}.row .av{width:36px;height:36px}.row .av svg{width:18px;height:18px}
.msg{flex:1;min-width:0}.msg p{margin:0 0 .7em}.msg ul{margin:0 0 .7em;padding-left:1.2em}.msg a{color:var(--g)}
.u{align-self:flex-end;max-width:80%}.u .bub{background:#4caf91;color:#fff;padding:12px 18px;border-radius:14px}
.ts{font-size:12px;color:var(--mu);margin-top:4px}.u .ts{text-align:right}
.step{font-size:14px;color:var(--mu);display:flex;gap:8px;align-items:center}.step i{color:var(--g);font-style:normal}
.src{font-size:13px;color:var(--mu);border-top:1px solid #eef0f3;padding-top:8px;margin-top:6px;word-break:break-all}
.fb{color:var(--mu);font-size:14px;margin-top:6px}
form{border:1px solid #dfe3ea;border-radius:16px;padding:12px 14px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 8px #0000000d}
input{flex:1;border:0;outline:0;font:inherit;padding:8px 0}
button{width:44px;height:44px;border:0;border-radius:12px;background:var(--g);color:#fff;font-size:18px;cursor:pointer}button:disabled{opacity:.5}
</style>
<div id=app>
<header><span class=av><svg viewBox="0 0 24 24"><rect x=4 y=8 width=16 height=11 rx=3 /><path d="M12 4v4M9 13h.01M15 13h.01"/></svg></span>OptiBot</header>
<div class=sup><span>&#127911;</span><div><b>Contact Support Team</b><a href="mailto:support@optisigns.com">support@optisigns.com</a> &middot; Mon - Fri: 7AM - 7PM CDT</div></div>
<div id=log></div>
<form id=f><input id=q placeholder="Ask me anything..." autocomplete=off autofocus><button id=s>&#10148;</button></form>
</div>
<script>
const AV='<span class=av><svg viewBox="0 0 24 24"><rect x=4 y=8 width=16 height=11 rx=3 /><path d="M12 4v4M9 13h.01M15 13h.01"/></svg></span>';
const log=document.getElementById('log');
const esc=t=>t.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const time=()=>new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
function md(t){
  const src=[];t=t.split('\\n').filter(l=>{const m=l.match(/^Article URL:\\s*(\\S+)/);if(m){src.push(m[1]);return false}return true}).join('\\n');
  let h=esc(t).replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>').replace(/\\[([^\\]]+)\\]\\((https?:[^)]+)\\)/g,'<a href="$2" target=_blank>$1</a>');
  h=h.split(/\\n{2,}/).map(b=>/^\\s*[*-] /.test(b)?'<ul>'+b.split('\\n').map(l=>'<li>'+l.replace(/^\\s*[*-] /,'')+'</li>').join('')+'</ul>':'<p>'+b.replace(/\\n/g,'<br>')+'</p>').join('');
  return h+src.map(u=>'<div class=src>Article URL: <a href="'+u+'" target=_blank>'+u+'</a></div>').join('');
}
function bot(html){const d=document.createElement('div');d.className='row';d.innerHTML=AV+'<div class=msg>'+html+'</div>';log.append(d);log.scrollTop=1e9;return d.querySelector('.msg')}
bot('<p><b>Hi! I\\'m OptiBot,</b> your AI assistant for OptiSigns. I can help you with setup, troubleshooting, managing your screens, playlists, and schedules. How can I help you today?</p>');
f.onsubmit=async e=>{e.preventDefault();const t=q.value.trim();if(!t)return;q.value='';s.disabled=true;
 const u=document.createElement('div');u.className='u';u.innerHTML='<div class=bub>'+esc(t)+'</div><div class=ts>'+time()+'</div>';log.append(u);
 const m=bot('<div class=step><i>&#9675;</i> Searching articles...</div>');
 try{const r=await fetch('/ask',{method:'POST',body:JSON.stringify({q:t})});const j=await r.json();
  m.innerHTML=j.answer?'<div class=step><i>&#10003;</i> Searched articles</div><div class=step><i>&#10003;</i> Read article</div>'+md(j.answer)+'<div class=fb>&#128077; &#128078; &nbsp;<span class=ts>'+time()+'</span></div>':'<p>'+esc(j.error)+'</p>'}
 catch(x){m.textContent='Error: '+x}
 s.disabled=false;log.scrollTop=1e9};
</script>"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        self._send(200, PAGE, "text/html; charset=utf-8")

    def do_POST(self):
        q = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["q"]
        try:
            out = {"answer": answer(q)}
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"[:300]}
        self._send(200, json.dumps(out), "application/json")


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), H).serve_forever()  # localhost only: no auth
