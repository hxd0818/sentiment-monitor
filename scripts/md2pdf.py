#!/usr/bin/env python3
"""
md2pdf.py — 将 Agent 生成的舆情分析报告 (report_v1.md) 转换为专业 PDF
用法: python3 md2pdf.py <report.md路径> [输出PDF路径]
"""
import sys, os, re, subprocess
from pathlib import Path
from datetime import datetime


def escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def inline_md(text):
    """Convert inline markdown to HTML (called AFTER table cell extraction, on plain text)"""
    text = escape_html(text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    for label, cls in [("🔴致命","risk-fatal"), ("🟠高","risk-high"), ("🟡中","risk-med"), ("🟢低","risk-low")]:
        text = text.replace(label, '<span class="%s">%s</span>' % (cls, label))
    return text


def md_to_html(md_path):
    """将 Markdown 转换为带样式的 HTML"""
    text = Path(md_path).read_text(encoding="utf-8")
    brand = Path(md_path).parent.name

    lines = text.split("\n")
    body_parts = []  # Collect body fragments as strings
    in_table = False
    in_code_block = False
    toc_items = []
    list_buffer = []  # (type, indent, content)
    in_list = False

    def flush_list():
        nonlocal list_buffer, in_list
        if not list_buffer:
            return
        # Group by base indent level to determine ul vs ol
        parts = []
        current_tag = None
        current_indent = None
        for ltype, lindent, lcontent in list_buffer:
            if current_tag is None or lindent != current_indent:
                if current_tag:
                    parts.append("</%s>" % current_tag)
                current_tag = "ol" if ltype == "ordered" else "ul"
                current_indent = lindent
                parts.append('<%s style="padding-left:%dpx">' % (current_tag, 12 + lindent * 20))
            parts.append('<li>%s</li>' % inline_md(lcontent))
        if current_tag:
            parts.append("</%s>" % current_tag)
        body_parts.extend(parts)
        list_buffer = []
        in_list = False

    def flush_table():
        nonlocal in_table
        if in_table:
            body_parts.append("</tbody></table>")
            in_table = False

    for line in lines:
        stripped = line.strip()

        # ---- Code blocks ----
        if stripped.startswith("```"):
            if in_code_block:
                body_parts.append("</code></pre>")
                in_code_block = False
            else:
                lang = stripped[3:].strip()
                body_parts.append('<pre><code class="language-%s">' % lang if lang else "<pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            body_parts.append(escape_html(line))
            continue

        # ---- Empty line ----
        if not stripped:
            flush_list()
            flush_table()
            body_parts.append("")
            continue

        # ---- Table row ----
        if stripped.startswith("|") and not stripped.startswith("| --"):
            cells_raw = [c.strip() for c in stripped.strip("|").split("|")]
            
            # Detect separator row
            if all(re.match(r'^[\s\-:]+$', c) for c in cells_raw):
                continue  # Skip separator row
            
            if not in_table:
                body_parts.append('<table><thead>')
                body_parts.append("<tr>" + "".join("<th>%s</th>" % inline_md(c) for c in cells_raw) + "</tr>")
                body_parts.append("</thead><tbody>")
                in_table = True
            else:
                body_parts.append("<tr>" + "".join("<td>%s</td>" % inline_md(c) for c in cells_raw) + "</tr>")
            continue

        # Non-table line while in table → close table
        if in_table:
            flush_table()

        # ---- Headings ----
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            flush_list()
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '-', title).strip('-')
            title_clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', title)
            title_clean = re.sub(r'\*([^*]+)\*', r'\1', title_clean)
            tag = "h%d" % level
            if level <= 2:
                toc_items.append((level, title, anchor))
            body_parts.append('<%s id="%s">%s</%s>' % (tag, anchor, inline_md(title_clean), tag))
            continue

        # ---- Blockquote ----
        if line.startswith(">"):
            flush_list()
            body_parts.append('<blockquote>%s</blockquote>' % inline_md(line[1:].strip()))
            continue

        # ---- Horizontal rule ----
        if stripped in ("---", "***", "___"):
            flush_list()
            body_parts.append("<hr>")
            continue

        # ---- Unordered list ----
        um = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if um:
            indent = len(um.group(1)) // 2
            if not in_list:
                in_list = True
            list_buffer.append(("ul", indent, um.group(2)))
            continue

        # ---- Ordered list ----
        om = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if om:
            indent = len(om.group(1)) // 2
            if not in_list:
                in_list = True
            list_buffer.append(("ordered", indent, om.group(2)))
            continue

        # ---- Regular paragraph ----
        flush_list()
        body_parts.append('<p>%s</p>' % inline_md(line))

    # Finalize
    flush_list()
    flush_table()
    if in_code_block:
        body_parts.append("</code></pre>")

    # === Build TOC ===
    toc_html = ""
    if toc_items:
        toc_lines = ['<nav id="toc"><h2>📑 目录</h2><ul>']
        for lvl, t, anch in toc_items:
            t_plain = re.sub(r'<[^>]+>', '', inline_md(t))
            toc_lines.append('  <li class="toc-l%d"><a href="#%s">%s</a></li>' % (lvl, anch, t_plain))
        toc_lines.append('</ul></nav>')
        toc_html = "\n".join(toc_lines)

    # === Extract metadata ===
    ver_m = re.search(r'报告版本[:\s]*([^\n|]+)', text)
    date_m = re.search(r'数据截止[:\s]*([^\n|]+)', text)
    version = ver_m.group(1).strip().lstrip("* :") if ver_m else "v1"
    date_str = date_m.group(1).strip().lstrip("* :") if date_m else datetime.now().strftime("%Y-%m-%d")

    # === Full HTML ===
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{0} — 舆情分析报告</title>
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'PingFang SC','Noto Sans CJK SC','Microsoft YaHei','WenQuanYi Micro Hei',sans-serif;
    color: #1a1a2e; line-height: 1.82; font-size: 12px;
    padding: 15mm 16mm 18mm 16mm; margin: 0; background: #fff;
  }}
  .cover {{ page-break-after: always; text-align: center; padding-top: 180px; }}
  .cover h1 {{ font-size: 28px; color: #0f766e; margin-bottom: 16px; font-weight: 800; letter-spacing: 2px; }}
  .cover .subtitle {{ font-size: 15px; color: #374151; margin: 24px 0; }}
  .cover .meta-box {{
    display: inline-block; background: linear-gradient(135deg,#ecfeff 0%%%%,#dbeafe 100%%);
    border-radius: 12px; padding: 20px 40px; margin-top: 30px; text-align: left;
    font-size: 12.5px; color: #1e3a8a; line-height: 2;
  }}
  .cover .meta-box strong {{ color: #0891b2; }}
  .cover .footer-note {{ margin-top: 80px; font-size: 10px; color: #94a3b8; }}
  #toc {{ page-break-after: always; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px 28px; margin: 20px 0; }}
  #toc h2 {{ font-size: 16px; color: #0891b2; border: none; margin-bottom: 12px; }}
  #toc ul {{ list-style: none; padding-left: 0; }}
  #toc li {{ padding: 4px 0; font-size: 12px; border-bottom: 1px dotted #e2e8f0; }}
  #toc li:last-child {{ border-bottom: none; }}
  #toc a {{ color: #0284c7; text-decoration: none; }}
  #toc a:hover {{ color: #0369a1; text-decoration: underline; }}
  .toc-l1 {{ padding-left: 0 !important; font-weight: 600; font-size: 13px; }}
  .toc-l2 {{ padding-left: 20px !important; font-weight: 400; }}
  h1 {{ font-size: 22px; color: #0f766e; border-bottom: 3px solid #0ea5e9; padding-bottom: 10px; margin-top: 36px; font-weight: 700; page-break-after: avoid; }}
  h2 {{ font-size: 16px; color: #0369a1; border-left: 4px solid #0ea5e9; padding-left: 12px; margin-top: 28px; font-weight: 600; page-break-after: avoid; }}
  h3 {{ font-size: 13.5px; color: #0c4a6e; margin-top: 20px; font-weight: 600; page-break-after: avoid; }}
  h4 {{ font-size: 12.5px; color: #047857; margin-top: 16px; font-weight: 600; page-break-after: avoid; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0 12px 0; font-size: 9pt; page-break-inside: avoid; table-layout: fixed; word-wrap: break-word; overflow-wrap: break-word; }}
  th, td {{ border: 1px solid #e5e7eb; padding: 5px 8px; text-align: left; vertical-align: top; word-wrap: break-word; overflow-wrap: break-word; word-break: break-all; }}
  th {{ background: linear-gradient(180deg,#f0fdfa 0%%%%,#f0f9ff 100%%); font-weight: 600; color: #0c4a6e; font-size: 11px; }}
  tr:nth-child(even) {{ background: #f8fafc; }}
  tr:hover {{ background: #f0f9ff; }}
  p {{ margin: 6px 0; text-align: justify; }}
  blockquote {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px 16px; margin: 12px 0; font-style: italic; color: #92400e; border-radius: 0 8px 8px 0; page-break-inside: avoid; }}
  hr {{ border: none; border-top: 2px solid #e2e8f0; margin: 20px 0; }}
  strong, b {{ color: #1e3a8a; }}
  em, i {{ color: #64748b; }}
  code {{ background: #f0fdfa; padding: 1px 5px; border-radius: 3px; font-size: 11px; color: #991b1b; font-family: 'Consolas',monospace; }}
  pre {{ background: #0c4a6e; color: #e2e8f0; padding: 14px 18px; border-radius: 8px; overflow-x: auto; font-size: 11px; page-break-inside: avoid; }}
  pre code {{ background: none; color: inherit; padding: 0; }}
  ul, ol {{ padding-left: 20px; margin: 6px 0; }}
  li {{ margin: 3px 0; }}
  .page-footer {{ text-align: center; color: #94a3b8; font-size: 9px; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
  .risk-fatal {{ color: #dc2626; font-weight: 700; }}
  .risk-high {{ color: #ea580c; font-weight: 700; }}
  .risk-med {{ color: #d97706; font-weight: 700; }}
  .risk-low {{ color: #65a30d; font-weight: 700; }}
  @media print {{
    body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .cover {{ height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 0; }}
    #toc {{ break-after: page; }}
    h1, h2, h3, h4 {{ break-after: avoid; }}
    table {{ break-inside: avoid-page; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <h1>📊 品牌舆情分析<br>深度报告</h1>
  <div class="subtitle">目标：{1}</div>
  <div class="meta-box">
    <strong>📋 报告版本:</strong> {2}<br>
    <strong>📅 数据截止:</strong> {3}<br>
    <strong>📊 调查方法:</strong> 舆情螺旋迭代法 (Agent驱动)<br>
    <strong>🔧 技术支持:</strong> 赛迪网<br>
    <strong>📊 分析方法:</strong> 舆情螺旋迭代法 + 早期发现四层漏斗 + 隐匿性风险发现<br>
    <strong>📄 生成时间:</strong> {4}
  </div>
  <p class="footer-note">警告: 本报告基于公开OSINT数据生成，仅供研究参考，不构成任何商业决策建议</p>
</div>
""".format(brand, brand, version, date_str, datetime.now().strftime("%Y-%m-%d %H:%M"))

    if toc_html:
        html += toc_html

    html += '<div class="content">\n'
    html += "\n".join(body_parts)
    html += '\n<div class="page-footer">'
    html += '<p>赛迪网舆情监测系统 · 仅供参考 · 不构成任何投资/商业决策建议</p>'
    html += '</div></div></body></html>'

    return html


def html_to_pdf(html_path, pdf_path):
    """Use Chrome headless to convert HTML → PDF"""
    abs_html = str(html_path.resolve())
    abs_pdf = str(pdf_path.resolve())
    r = subprocess.run([
        "google-chrome",
        "--headless", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage",
        "--print-to-pdf=%s" % abs_pdf,
        "--print-to-pdf-no-header",
        "--print-to-pdf-no-footer",
        "file://%s" % abs_html
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)

    if Path(pdf_path).exists():
        size = Path(pdf_path).stat().st_size
        print("✅ PDF: %s (%d KB)" % (pdf_path.name, size // 1024))
        return True
    else:
        print("❌ PDF generation failed:")
        print(r.stderr.decode()[:500])
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 md2pdf.py <report.md> [output.pdf]")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print("File not found: %s" % md_path)
        sys.exit(1)

    pdf_path = Path(sys.argv[2]) if len(sys.argv) > 2 else md_path.parent / "report.pdf"

    print("📝 Reading: %s" % md_path.name)
    html = md_to_html(md_path)

    html_path = md_path.parent / "report_styled.html"
    html_path.write_text(html, encoding="utf-8")
    print("✅ HTML: %s (%d KB)" % (html_path.name, len(html) // 1024))

    print("🖨️  Converting to PDF...")
    if html_to_pdf(html_path, pdf_path):
        print("\nDone! → %s" % pdf_path)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
