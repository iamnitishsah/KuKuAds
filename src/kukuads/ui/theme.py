"""Look and feel: one stylesheet and small HTML helpers. Colours use transparency so they work in light and dark mode."""
from __future__ import annotations

import html
import re

import streamlit as st

CSS = """<style>
.block-container{padding-top:4.5rem;max-width:1250px}
.brand{display:flex;align-items:baseline;gap:.6rem}
.brand b{font-size:1.9rem;letter-spacing:-.02em}.brand b span{color:#7C3AED}
.brand i{opacity:.65;font-style:normal;font-size:.95rem}
.hero{border-radius:18px;padding:2.2rem 2.4rem;margin:.4rem 0 1.2rem;color:#fff;background:linear-gradient(135deg,#4C1D95 0%,#7C3AED 55%,#DB2777 100%)}
.hero h1{margin:0 0 .5rem;font-size:2.3rem;line-height:1.15;color:#fff}
.hero p{margin:0 0 1.1rem;font-size:1.08rem;opacity:.93;max-width:46rem;color:#fff}
.hero .hc{display:inline-block;margin:0 .45rem .35rem 0;padding:.32rem .8rem;border-radius:99px;background:rgba(255,255,255,.18);font-weight:600;font-size:.9rem}
.stat{border:1px solid rgba(124,58,237,.28);background:rgba(124,58,237,.07);border-radius:14px;padding:1rem 1.1rem;min-height:9.4rem;box-sizing:border-box}
.stat .v{font-size:2rem;font-weight:800;line-height:1.05;color:#7C3AED}
.stat .l{font-weight:600;margin-top:.15rem}.stat .s{opacity:.65;font-size:.82rem;margin-top:.15rem}
.card{border:1px solid rgba(128,128,128,.28);border-radius:14px;padding:1.1rem 1.2rem;min-height:14.5rem;box-sizing:border-box}
.card h4{margin:0 0 .5rem;font-size:1.05rem}.card ul{margin:.2rem 0 0 1.1rem;padding:0}.card li{margin:.18rem 0}
.step{border:1px solid rgba(128,128,128,.28);border-radius:14px;padding:1rem;min-height:17rem;box-sizing:border-box}
.step .n{display:inline-flex;width:1.7rem;height:1.7rem;border-radius:99px;background:#7C3AED;color:#fff;align-items:center;justify-content:center;font-weight:700;margin-bottom:.4rem}
.step h5{margin:.1rem 0 .3rem;font-size:1rem}.step p{margin:.3rem 0 0;font-size:.88rem;opacity:.85}
.chip{display:inline-block;padding:.12rem .6rem;border-radius:99px;font-size:.78rem;font-weight:600;margin:0 .3rem .25rem 0;border:1px solid transparent}
.chip.green{background:rgba(22,163,74,.14);color:#16A34A;border-color:rgba(22,163,74,.35)}
.chip.amber{background:rgba(217,119,6,.14);color:#D97706;border-color:rgba(217,119,6,.35)}
.chip.red{background:rgba(220,38,38,.13);color:#DC2626;border-color:rgba(220,38,38,.35)}
.chip.purple{background:rgba(124,58,237,.14);color:#7C3AED;border-color:rgba(124,58,237,.35)}
.chip.gray{background:rgba(128,128,128,.14);opacity:.9;border-color:rgba(128,128,128,.3)}
.ph{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap}
.ph .rank{background:#7C3AED;color:#fff;border-radius:10px;padding:.15rem .6rem;font-weight:800}
.ph .pid{font-weight:800;font-size:1.15rem}.ph .meta{opacity:.7}.ph .sp{flex:1}
.tl{margin:.6rem 0 .8rem}.tl .bar{position:relative;height:14px;border-radius:99px;background:rgba(128,128,128,.22)}
.tl .seg{position:absolute;top:0;height:14px;border-radius:99px;background:linear-gradient(90deg,#7C3AED,#DB2777)}
.tl .hk{position:absolute;top:-4px;width:3px;height:22px;background:#16A34A;border-radius:2px}
.tl .ax{display:flex;justify-content:space-between;font-size:.74rem;opacity:.6;margin-top:.2rem}
.q{border-left:4px solid #7C3AED;background:rgba(124,58,237,.06);border-radius:0 10px 10px 0;padding:.5rem .8rem;margin:.4rem 0}
.q.cliff{border-color:#DB2777;background:rgba(219,39,119,.06)}.q.why{border-color:#16A34A;background:rgba(22,163,74,.06)}
.q b{display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;opacity:.7;margin-bottom:.1rem}
.sc{display:flex;align-items:center;gap:.5rem;margin:.22rem 0;font-size:.86rem}.sc .k{width:5.6rem;opacity:.8}
.sc .t{flex:1;height:9px;border-radius:99px;background:rgba(128,128,128,.22);overflow:hidden}.sc .f{height:9px;border-radius:99px}
.sc .x{width:2rem;text-align:right;font-weight:700}
.final{text-align:center;border:1px solid rgba(124,58,237,.3);border-radius:12px;padding:.5rem;background:rgba(124,58,237,.07)}
.final .v{font-size:1.9rem;font-weight:800;color:#7C3AED;line-height:1}.final .l{font-size:.72rem;opacity:.7}
.tx{border:1px solid rgba(128,128,128,.28);border-radius:12px;padding:.4rem .6rem;max-height:430px;overflow:auto}
.tx .r{display:flex;gap:.6rem;padding:.28rem .1rem;border-bottom:1px dashed rgba(128,128,128,.2);font-size:.86rem}
.tx .r:last-child{border:0}.tx .t{width:3rem;opacity:.55;font-variant-numeric:tabular-nums}
.tx .sp{font-weight:700}.tx .tg{opacity:.6;font-style:italic}.tx .os{opacity:.75;font-style:italic}.tx .cut{text-align:center;opacity:.55;padding:.3rem}
.sys{display:flex;flex-wrap:wrap;gap:.2rem;align-items:center;padding:.5rem .8rem;border-radius:12px;border:1px solid rgba(128,128,128,.28);margin-bottom:.8rem}
.sys b{margin-right:.6rem}
.demo-banner{padding:.6rem .9rem;border-radius:10px;background:rgba(217,119,6,.12);border:1px solid rgba(217,119,6,.35);margin:.4rem 0 .8rem}
.split{display:flex;height:26px;border-radius:8px;overflow:hidden;font-size:.78rem;font-weight:700;color:#fff}
.split div{display:flex;align-items:center;justify-content:center;min-width:1.8rem}
.row{display:grid;grid-template-columns:8.5rem 1fr 6rem;gap:.7rem;align-items:center;margin:.5rem 0;font-size:.9rem}
.row .n{opacity:.8}.row .e{text-align:right;opacity:.75;font-size:.8rem}
.legend{font-size:.8rem;opacity:.75;margin:.3rem 0 .6rem}.legend i{display:inline-block;width:.7rem;height:.7rem;border-radius:3px;margin:0 .25rem 0 .6rem;vertical-align:middle}
.arrow{text-align:center;font-size:1.4rem;opacity:.4;padding-top:2.2rem}
.formula{display:flex;height:34px;border-radius:10px;overflow:hidden;font-weight:700;color:#fff;font-size:.85rem}
.formula div{display:flex;align-items:center;justify-content:center}
.pick{display:inline-block;padding:.35rem .8rem;border-radius:10px;margin:0 .4rem .4rem 0;font-weight:700;border:1px solid rgba(124,58,237,.35);background:rgba(124,58,237,.08)}
.pick.first{background:#7C3AED;color:#fff;border-color:#7C3AED}
</style>"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape(str(x))


def show(markup: str) -> None:
    """Render HTML. Callers must build it with no blank lines and no leading indentation (Markdown would code-block it)."""
    st.markdown(markup, unsafe_allow_html=True)


def chip(text, kind: str = "gray") -> str:
    return f'<span class="chip {kind}">{esc(text)}</span>'


def stat(value, label, sub="") -> str:
    return f'<div class="stat"><div class="v">{esc(value)}</div><div class="l">{esc(label)}</div><div class="s">{esc(sub)}</div></div>'


def card(title: str, items: list[str]) -> str:
    return f'<div class="card"><h4>{esc(title)}</h4><ul>' + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul></div>"


def step(n: int, title: str, owner: str, body: str) -> str:
    kind = "purple" if owner == "AI" else "gray"
    return (f'<div class="step"><div class="n">{n}</div><h5>{esc(title)}</h5>{chip(owner, kind)}'
            f'<p>{esc(body)}</p></div>')


def quote(label: str, text, kind: str = "") -> str:
    return f'<div class="q {kind}"><b>{esc(label)}</b>{esc(text)}</div>'


def score_bar(label: str, value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    pct = max(0.0, min(100.0, (v - 1) / 4 * 100))
    color = "#16A34A" if v >= 4 else "#D97706" if v >= 3 else "#DC2626"
    return (f'<div class="sc"><span class="k">{esc(label)}</span><span class="t"><span class="f" style="display:block;'
            f'width:{pct:.0f}%;background:{color}"></span></span><span class="x">{v:g}</span></div>')


def timeline(segments: list[dict], hook_t: float | None, duration: float | None) -> str:
    """Where the clip sits in its episode. Needs the episode length; returns '' without it."""
    if not duration:
        return ""
    segs = "".join(f'<div class="seg" style="left:{s["start"] / duration * 100:.2f}%;'
                   f'width:{max((s["end"] - s["start"]) / duration * 100, 0.8):.2f}%"></div>' for s in segments)
    hook = f'<div class="hk" style="left:{hook_t / duration * 100:.2f}%"></div>' if hook_t is not None else ""
    mm = lambda s: f"{int(s // 60)}:{int(s % 60):02d}"
    return f'<div class="tl"><div class="bar">{segs}{hook}</div><div class="ax"><span>0:00</span><span>episode {mm(duration)}</span></div></div>'


LINE = re.compile(r"^\[\s*([\d.]+)s\]\s*(.*)$")


def transcript(text: str) -> str:
    """The judge's clip transcript as a readable list."""
    rows = []
    for raw in text.splitlines():
        m = LINE.match(raw)
        if not m:
            rows.append(f'<div class="cut">{esc(raw.strip("[]"))}</div>' if raw.strip() else "")
            continue
        t, rest = m.groups()
        if rest.startswith("(on screen)"):
            body = f'<span class="os">{esc(rest)}</span>'
        elif rest.startswith("(sound)"):
            body = f'<span class="os">{esc(rest)}</span>'
        else:
            who, _, said = rest.partition(": ")
            name, _, tone = who.partition(" (")
            body = f'<span><span class="sp">{esc(name)}</span>' + (f' <span class="tg">({esc(tone)}</span>' if tone else "") + f' {esc(said)}</span>'
        rows.append(f'<div class="r"><span class="t">{esc(t)}s</span>{body}</div>')
    return '<div class="tx">' + "".join(r for r in rows if r) + "</div>"


def split_bar(left: int, right: int, left_label="LLM better", right_label="baseline better") -> str:
    """Two-part bar: purple = the AI won, grey = the baseline won."""
    total = max(left + right, 1)
    return (f'<div class="split"><div style="width:{left / total * 100:.1f}%;background:#7C3AED">{left}</div>'
            f'<div style="width:{right / total * 100:.1f}%;background:#6B7280">{right}</div></div>')


def meter(value: float, maxv: float, color: str = "#7C3AED") -> str:
    pct = max(0.0, min(100.0, value / maxv * 100))
    return f'<div class="sc"><span class="t"><span class="f" style="display:block;width:{pct:.0f}%;background:{color}"></span></span></div>'


def formula(parts: list[tuple[str, float, str]]) -> str:
    total = sum(w for _, w, _ in parts)
    return '<div class="formula">' + "".join(f'<div style="width:{w / total * 100:.1f}%;background:{c}">{esc(n)} {w:g}</div>' for n, w, c in parts) + "</div>"
