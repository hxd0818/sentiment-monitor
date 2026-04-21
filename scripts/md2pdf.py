#!/usr/bin/env python3
# md2pdf.py — Markdown → PDF (no cover, no TOC, no header/footer via CDP)
import sys, os, re, subprocess, time, json, tempfile, urllib.request
from pathlib import Path
from datetime import datetime


def esc(text):
    return str(text).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def inline_md(text):
    text = esc(text)
    for pat, tag in [(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>'), (r'\*([^*]+)\*', r'<em>\1</em>'), (r'`([^`]+)`', r'<code>\1</code>')]:
        text = re.sub(pat, tag, text)
    for label, cls in [("🔴致命","rf"),("🟠高","rh"),("🟡中","rm"),("🟢低","rl")]:
        text = text.replace(label, '<span class="%s">%s</span>'%(cls,label))
    return text


def md_to_html(md_path):
    text = Path(md_path).read_text(encoding="utf-8")
    brand = Path(md_path).parent.name
    lines = text.split("\n")
    body = []
    in_table = False
    in_code = False
    list_buf = []
    in_list = False

    def flush_list():
        nonlocal list_buf, in_list
        if not list_buf: return
        parts = []; cur_tag = None; cur_ind = None
        for lt, li, lc in list_buf:
            if cur_tag is None or li != cur_ind:
                if cur_tag: parts.append("</%s>"%cur_tag)
                cur_tag = "ol" if lt=="ordered" else "ul"
                cur_ind = li
                parts.append('<%s style="padding-left:%dpx">'%(cur_tag,12+li*20))
            parts.append('<li>%s</li>'%inline_md(lc))
        if cur_tag: parts.append("</%s>"%cur_tag)
        body.extend(parts); list_buf=[]; in_list=False

    def flush_table():
        nonlocal in_table
        if in_table: body.append("</tbody></table>"); in_table=False

    for line in lines:
        s = line.strip()
        if s.startswith("```"):
            if in_code: body.append("</code></pre>"); in_code=False
            else: body.append('<pre><code>'); in_code=True
            continue
        if in_code: body.append(esc(line)); continue
        if not s: flush_list(); flush_table(); body.append(""); continue
        if s.startswith("|") and not s.startswith("| --"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.match(r'^[\s\-:]+$',c) for c in cells): continue
            if not in_table:
                body.append('<table><thead>')
                body.append("<tr>"+"".join("<th>%s</th>"%inline_md(c) for c in cells)+"</tr>")
                body.append("</thead><tbody>"); in_table=True
            else:
                body.append("<tr>"+"".join("<td>%s</td>"%inline_md(c) for c in cells)+"</tr>")
            continue
        if in_table: flush_table()
        m = re.match(r'^(#{1,6})\s+(.+)',line)
        if m:
            flush_list()
            lv=len(m.group(1)); title=m.group(2).strip()
            anchor=re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+','-',title).strip('-')
            tc=re.sub(r'\*\*([^*]+)\*\*',r'\1',title); tc=re.sub(r'\*([^*]+)\*',r'\1',tc)
            body.append('<h%d id="%s">%s</h%d>'%(lv,anchor,inline_md(tc),lv))
            continue
        if line.startswith(">"): flush_list(); body.append('<blockquote>%s</blockquote>'%inline_md(line[1:].strip())); continue
        if s in ("---","***","___"): flush_list(); body.append("<hr>"); continue
        um=re.match(r'^(\s*)[-*+]\s+(.*)',line)
        if um:
            indent=len(um.group(1))//2
            if not in_list: in_list=True
            list_buf.append(("ul",indent,um.group(2))); continue
        om=re.match(r'^(\s*)\d+\.\s+(.*)',line)
        if om:
            indent=len(om.group(1))//2
            if not in_list: in_list=True
            list_buf.append(("ordered",indent,om.group(2))); continue
        flush_list()
        body.append('<p>%s</p>'%inline_md(line))

    flush_list(); flush_table()
    if in_code: body.append("</code></pre>")

    ver_m=re.search(r'报告版本[:\s]*([^\n|]+)',text)
    date_m=re.search(r'数据截止[:\s]*([^\n|]+)',text)
    version=ver_m.group(1).strip().lstrip("* :") if ver_m else "v1"
    date_str=date_m.group(1).strip().lstrip("* :") if date_m else datetime.now().strftime("%Y-%m-%d")

    html_parts = []
    h = html_parts.append
    h('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">')
    h('<title>%s — 舆情分析报告</title>' % brand)
    h('<style>')
    h('@page { size: A4; margin: 0; }')
    h('* { box-sizing: border-box; }')
    h('body { font-family: "PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif; color: #1a1a2e; line-height: 1.82; font-size: 12px; padding: 15mm 16mm 18mm 16mm; margin: 0; background: #fff; }')
    h('.meta-box { display: inline-block; background: linear-gradient(135deg,#ecfeff 0%%,#dbeafe 100%%); border-radius: 12px; padding: 18px 30px; margin-top: 10px; text-align: left; font-size: 11.5px; color: #1e3a8a; line-height: 1.9; }')
    h('.meta-box strong { color: #0891b2; }')
    h('h1 { font-size: 22px; color: #0f766e; border-bottom: 3px solid #0ea5e9; padding-bottom: 8px; margin-top: 30px; font-weight: 700; page-break-after: avoid; }')
    h('h2 { font-size: 16px; color: #0369a1; border-left: 4px solid #0ea5e9; padding-left: 12px; margin-top: 24px; font-weight: 600; page-break-after: avoid; }')
    h('h3 { font-size: 13.5px; color: #0c4a6e; margin-top: 18px; font-weight: 600; page-break-after: avoid; }')
    h('h4 { font-size: 12.5px; color: #047857; margin-top: 14px; font-weight: 600; page-break-after: avoid; }')
    h('table { width: 100%%; border-collapse: collapse; margin: 8px 0 10px 0; font-size: 9pt; page-break-inside: avoid; table-layout: fixed; word-wrap: break-word; overflow-wrap: break-word; }')
    h('th,td { border: 1px solid #e5e7eb; padding: 5px 8px; text-align: left; vertical-align: top; word-wrap: break-word; overflow-wrap: break-word; word-break: break-all; }')
    h('th { background: linear-gradient(180deg,#f0fdfa 0%%,#f0f9ff 100%%); font-weight: 600; color: #0c4a6e; font-size: 11px; }')
    h('tr:nth-child(even) { background: #f8fafc; }')
    h('p { margin: 5px 0; text-align: justify; }')
    h('blockquote { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 8px 14px; margin: 10px 0; font-style: italic; color: #92400e; border-radius: 0 8px 8px 0; }')
    h('hr { border: none; border-top: 2px solid #e2e8f0; margin: 16px 0; }')
    h('strong,b { color: #1e3a8a; } em,i { color: #64748b; }')
    h('code { background: #f0fdfa; padding: 1px 5px; border-radius: 3px; font-size: 11px; color: #991b1b; font-family: Consolas,monospace; }')
    h('pre { background: #0c4a6e; color: #e2e8f0; padding: 12px 16px; border-radius: 8px; overflow-x: auto; font-size: 11px; page-break-inside: avoid; }')
    h('pre code { background: none; color: inherit; padding: 0; }')
    h('ul,ol { padding-left: 20px; margin: 5px 0; } li { margin: 2px 0; }')
    h('.page-footer { text-align: center; color: #94a3b8; font-size: 9px; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 10px; }')
    h('.rf { color: #dc2626; font-weight: 700; } .rh { color: #ea580c; font-weight: 700; }')
    h('.rm { color: #d97706; font-weight: 700; } .rl { color: #65a30d; font-weight: 700; }')
    h('@media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } h1,h2,h3,h4 { break-after: avoid; } table { break-inside: avoid-page; } }')
    h('</style></head><body>')
    h('<div class="meta-box">')
    h('<strong>📋 报告版本:</strong> %s<br>' % version)
    h('<strong>📅 数据截止:</strong> %s<br>' % date_str)
    h('<strong>📊 调查方法:</strong> 舆情螺旋迭代法 (Agent驱动)<br>')
    h('<strong>🔧 技术支持:</strong> 赛迪网<br>')
    h('<strong>📊 分析方法:</strong> 舆情螺旋迭代法 + 早期发现四层漏斗 + 隐匿性风险发现<br>')
    h('<strong>📄 生成时间:</strong> %s' % datetime.now().strftime("%Y-%m-%d %H:%M"))
    h('</div>')
    h('<p style="font-size:10px;color:#94a3b8;margin:8px 0;">⚠️ 本报告基于公开OSINT数据生成，仅供研究参考，不构成任何商业决策建议</p>')
    h('<div class="content">' + "\n".join(body))
    h('<div class="page-footer"><p>赛迪网舆情监测系统 · 仅供参考 · 不构成任何投资/商业决策建议</p></div>')
    h('</div></body></html>')
    return "".join(html_parts)


def write_cdp_script(ws_url, abs_html, abs_pdf):
    """Write CDP client script to temp file"""
    lines = []
    w = lines.append
    w('# -*- coding: utf-8 -*-\n')
    w('import json,time,os\n')
    w('from websocket import create_connection\n')
    w('ws=create_connection("%s",timeout=15)\n' % ws_url)
    w('mid=[1];cbs={}\n')
    w('def c(m,p=None,cb=None):\n')
    w(' i=mid[0];mid[0]+=1\n')
    w(' if cb:cbs[i]=cb\n')
    w(' d={"id":i,"method":m}\n')
    w(' if p:d["params"]=p\n')
    w(' ws.send(json.dumps(d))\n')
    w('def w(n):\n')
    w(' for _ in range(n):\n')
    w('  try:\n')
    w('   m=json.loads(ws.recv())\n')
    w('   if m.get("id")in cbs:cbs.pop(m["id"])(m);return\n')
    w('  except:break\n')
    w('c("Page.enable");w(3)\n')
    w('c("Page.navigate",{"url":"file://%s"});time.sleep(4);w(3)\n' % abs_html)
    w('def on(r):\n')
    w(' d=r.get("result",{}).get("data")\n')
    w(' if d:\n')
    w('  with open("%s","wb")as f:f.write(bytes(d,"utf-8"))\n' % abs_pdf)
    w('  print("CDP_OK:"+str(len(bytes(d,"utf-8"))))\n')
    w(' else:print("CDP_FAIL:"+str(r)[:200])\n')
    w('c("Page.printToPDF",{"displayHeaderFooter":False,"printBackground":True,"preferCSSPageSize":True,"paperWidth":8.27,"paperHeight":11.69,"marginTop":0.4,"marginBottom":0.4,"marginLeft":0.4,"marginRight":0.4},on)\n')
    w('w(10)\nws.close()\n')
    return "".join(lines)


def html_to_pdf(html_path, pdf_path):
    """Chrome CDP via page-level target: displayHeaderFooter=False"""
    import subprocess as sp, pathlib as pl

    abs_html = str(pl.Path(html_path).resolve())
    abs_pdf = str(pl.Path(pdf_path).resolve())
    port = 19999

    # Ensure Chrome is running
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=2)
    except Exception:
        sp.Popen(["google-chrome","--headless","--disable-gpu","--no-sandbox",
            "--disable-dev-shm-usage","--remote-debugging-port=%d"%port,
            "--remote-allow-origins=*","about:blank"],
            stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        time.sleep(4)

    # Get page-level WS URL (not browser-level!)
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port)
        tabs = json.loads(resp.read().decode())
        ws_url = tabs[0]["webSocketDebuggerUrl"]
    except Exception as e:
        print("❌ Chrome connect failed: %s" % e); return False

    # Write CDP script (page-level)
    tf_path = "/tmp/cdp_print_%d.py" % port
    with open(tf_path, "w") as tf:
        tf.write("# -*- coding: utf-8 -*-\n")
        tf.write("import json,time,os\n")
        tf.write("from websocket import create_connection\n")
        tf.write("ws=create_connection(\"%s\",timeout=15)\n" % ws_url)
        tf.write("mid=[1];cbs={}\n")
        tf.write("def c(m,p=None,cb=None):\n i=mid[0];mid[0]+=1\n if cb:cbs[i]=cb\n d={\"id\":i,\"method\":m}\n if p:d[\"params\"]=p\n ws.send(json.dumps(d))\n")
        tf.write("def w(n):\n for _ in range(n):\n  try:\n   m=json.loads(ws.recv())\n   if m.get(\"id\")in cbs:cbs.pop(m[\"id\"])(m);return\n  except:break\n")
        tf.write("c(\"Page.navigate\",{\"url\":\"file://%s\"});time.sleep(4);w(5)\n" % abs_html)
        tf.write("def on(r):\n d=r.get(\"result\",{}).get(\"data\")\n if d:\n  with open(\"%s\",\"wb\")as f:f.write(bytes(d,\"utf-8\"))\n  print(\"CDP_OK:\"+str(len(bytes(d,\"utf-8\"))))\n else:print(\"CDP_FAIL:\"+str(r)[:200])\n" % abs_pdf)
        tf.write("c(\"Page.printToPDF\",{\"displayHeaderFooter\":False,\"printBackground\":True,\"preferCSSPageSize\":True,\"paperWidth\":8.27,\"paperHeight\":11.69,\"marginTop\":0.4,\"marginBottom\":0.4,\"marginLeft\":0.4,\"marginRight\":0.4},on)\n")
        tf.write("w(15)\nws.close()\n")

    r = sp.run([sys.executable,tf_path],stdout=sp.PIPE,stderr=sp.PIPE,timeout=35)
    try: os.remove(tf_path)
    except: pass

    out = r.stdout.decode() if isinstance(r.stdout,bytes) else r.stdout
    err = r.stderr.decode() if isinstance(r.stderr,bytes) else r.stderr

    if "CDP_OK" in out:
        size = os.path.getsize(abs_pdf)
        print("✅ PDF: %s (%d KB)"%(pl.Path(pdf_path).name,size//1024))
        return True
    else:
        print("❌ PDF failed:")
        print((err or out)[:300])
        return False


    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 md2pdf.py <report.md> [output.pdf]"); sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print("File not found: %s" % md_path); sys.exit(1)

    pdf_path = Path(sys.argv[2]) if len(sys.argv) > 2 else md_path.parent / "report.pdf"

    print("📝 Reading: %s" % md_path.name)
    html = md_to_html(md_path)

    html_path = md_path.parent / "report_styled.html"
    html_path.write_text(html, encoding="utf-8")
    print("✅ HTML: %s (%d KB)" % (html_path.name, len(html)//1024))

    print("🖨️  Converting to PDF...")
    if html_to_pdf(html_path, pdf_path):
        print("\nDone! → %s" % pdf_path)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
