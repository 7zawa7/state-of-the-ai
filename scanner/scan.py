"""
State of the AI – Scanner
-------------------------
Läuft per GitHub Actions automatisch (siehe .github/workflows/scan.yml).

Ablauf pro Lauf:
1. Kostenlose Quellen abfragen (Hugging Face, GitHub, Hacker News, RSS-Feeds) – ganz ohne KI.
2. Bereits bekannte Links aussortieren.
3. EIN günstiger KI-Aufruf wählt die wichtigsten neuen Funde aus (Triage).
4. Nur für diese Funde: Quelle laden und einen Artikel schreiben lassen.
5. Ergebnis in docs/data.json speichern. GitHub Pages veröffentlicht automatisch.

Kosten sparen: Die KI wird nur aufgerufen, wenn es wirklich neue Kandidaten gibt,
und höchstens MAX_NEW Artikel pro Lauf geschrieben.
"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import feedparser
import requests
from anthropic import Anthropic

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data.json"

MODEL = os.environ.get("MODEL", "claude-haiku-5-5")       # kleines, günstiges Modell
MAX_NEW = int(os.environ.get("MAX_NEW", "4"))             # max. neue Artikel pro Lauf
MAX_AGE_H = int(os.environ.get("MAX_AGE_H", "72"))        # nur Funde der letzten X Stunden
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "300"))       # so viele Einträge pro Rubrik behalten
UA = {"User-Agent": "state-of-the-ai-scanner/1.0 (+https://github.com)"}
NOW = dt.datetime.now(dt.timezone.utc)

RSS_FEEDS = [
    ("Fachpresse", "https://the-decoder.com/feed/"),
    ("Fachpresse", "https://www.marktechpost.com/feed/"),
    ("Fachpresse", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("Lab-Blog", "https://openai.com/news/rss.xml"),
    ("Lab-Blog", "https://huggingface.co/blog/feed.xml"),
    ("Lab-Blog", "https://deepmind.google/blog/rss.xml"),
]


def log(*a):
    print(*a, flush=True)


def get_json(url, **kw):
    r = requests.get(url, headers={**UA, **kw.pop("headers", {})}, timeout=25, **kw)
    r.raise_for_status()
    return r.json()


def parse_time(s):
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def fresh(t):
    return t is None or (NOW - t).total_seconds() < MAX_AGE_H * 3600


# ---------------- 1. Quellen (kostenlos) ----------------
def src_hf_models():
    out = []
    for m in get_json("https://huggingface.co/api/models", params={"sort": "trendingScore", "direction": -1, "limit": 25}):
        mid = m.get("id") or m.get("modelId")
        out.append({"titel": mid, "url": f"https://huggingface.co/{mid}", "quelle": "Hugging Face",
                    "signal": f"{m.get('likes', 0)} Likes · Trending", "score": m.get("trendingScore", 0) or 0,
                    "zeit": m.get("createdAt"), "info": f"Pipeline: {m.get('pipeline_tag')}, Downloads: {m.get('downloads')}"})
    return out


def src_hf_papers():
    out = []
    for p in get_json("https://huggingface.co/api/daily_papers", params={"limit": 30}):
        paper = p.get("paper", {})
        out.append({"titel": paper.get("title") or p.get("title"), "url": f"https://huggingface.co/papers/{paper.get('id')}",
                    "quelle": "arXiv", "signal": f"{paper.get('upvotes', 0)} Upvotes HF", "score": paper.get("upvotes", 0),
                    "zeit": p.get("publishedAt"), "info": (paper.get("summary") or "")[:600]})
    return out


def src_github():
    since = (NOW - dt.timedelta(days=10)).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    out = []
    for topic in ("llm", "ai-agents", "generative-ai"):
        q = f"topic:{topic} created:>{since}"
        res = get_json("https://api.github.com/search/repositories", params={"q": q, "sort": "stars", "order": "desc", "per_page": 10}, headers=headers)
        for r in res.get("items", []):
            out.append({"titel": r["full_name"], "url": r["html_url"], "quelle": "GitHub",
                        "signal": f"{r['stargazers_count']:,} ★".replace(",", "."), "score": r["stargazers_count"],
                        "zeit": r.get("created_at"), "info": r.get("description") or ""})
    return out


def src_hn():
    since = int((NOW - dt.timedelta(hours=MAX_AGE_H)).timestamp())
    out = []
    for q in ("AI", "LLM", "model"):
        res = get_json("https://hn.algolia.com/api/v1/search", params={"query": q, "tags": "story", "numericFilters": f"points>150,created_at_i>{since}", "hitsPerPage": 15})
        for h in res.get("hits", []):
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
            out.append({"titel": h.get("title"), "url": url, "quelle": "Hacker News", "signal": f"{h.get('points')} Punkte auf HN",
                        "score": h.get("points", 0), "zeit": h.get("created_at"), "info": f"HN-Diskussion: https://news.ycombinator.com/item?id={h['objectID']}"})
    return out


def src_rss():
    out = []
    for quelle, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url, agent=UA["User-Agent"])
        except Exception as e:  # noqa
            log("RSS-Fehler", url, e)
            continue
        for e in feed.entries[:12]:
            t = None
            if getattr(e, "published_parsed", None):
                t = dt.datetime(*e.published_parsed[:6], tzinfo=dt.timezone.utc)
            out.append({"titel": e.get("title"), "url": e.get("link"), "quelle": quelle, "signal": "", "score": 0,
                        "zeit": t.isoformat() if t else None, "info": re.sub("<[^>]+>", " ", e.get("summary", ""))[:500]})
    return out


def collect():
    cands = []
    for fn in (src_hf_models, src_hf_papers, src_github, src_hn, src_rss):
        try:
            got = fn()
            log(f"{fn.__name__}: {len(got)}")
            cands += got
        except Exception as e:  # eine Quelle darf ausfallen, der Rest läuft weiter
            log(f"{fn.__name__} fehlgeschlagen: {e}")
    return [c for c in cands if c.get("titel") and c.get("url") and fresh(parse_time(c.get("zeit")))]


# ---------------- 2. Bekanntes aussortieren ----------------
def known_urls(data):
    urls = set()
    for col in ("news", "radar", "projekte"):
        for d in data.get(col, []):
            if d.get("link"):
                urls.add(d["link"].rstrip("/"))
            for q in d.get("quellen", []):
                if q.get("url"):
                    urls.add(q["url"].rstrip("/"))
    return urls


# ---------------- 3./4. KI ----------------
client = None


def ask(prompt, max_tokens=4000):
    global client
    client = client or Anthropic()
    msg = client.messages.create(model=MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    text = re.sub(r"```(?:json)?", "", text)
    starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
    if not starts:
        log("Antwort ohne JSON:", text[:300]); return None
    i = min(starts); j = text.rfind("]" if text[i] == "[" else "}")
    try:
        return json.loads(text[i:j + 1])
    except Exception as e:  # noqa
        log("JSON nicht lesbar:", e, text[:300]); return None


def triage(cands, existing_titles):
    lines = "\n".join(f"{i}. [{c['quelle']}] {c['titel']} — {c['signal']} — {c['info'][:160]}" for i, c in enumerate(cands))
    prompt = f"""Du bist Chefredakteur von „State of the AI“, einer deutschen Seite, die als Erste über wichtige KI-Neuheiten berichtet:
neue Modelle und Releases, Insider-Funde aus Engineering-Kreisen (Repos, Papers, Infrastruktur) und echte Projekte, die Menschen mit KI gebaut haben.

Bereits veröffentlicht (nicht doppelt nehmen): {existing_titles[:60]}

Kandidaten:
{lines}

Wähle 1 bis {MAX_NEW} Kandidaten (nur wenn wirklich gar nichts taugt, gib [] zurück), die relevant, neu und für ein breites, technikinteressiertes Publikum spannend sind.
Ignoriere Werbung, Gerüchte, Finanznachrichten ohne Technikbezug und Duplikate.
Antworte NUR mit JSON: [{{"nr": <Nummer>, "rubrik": "news"|"radar"|"projekte"}}]
- "news" = große Releases/Ereignisse für alle
- "radar" = technische Insider-Funde (Repos, Papers, Modelle, Infra)
- "projekte" = konkrete Werke/Projekte von Menschen, gebaut mit KI"""
    try:
        res = ask(prompt, 800) or []
    except Exception as e:  # noqa
        log("Triage fehlgeschlagen:", e); return []
    if isinstance(res, dict):
        res = res.get("auswahl") or res.get("items") or [res]
    out = []
    for r in res:
        if not isinstance(r, dict): continue
        try: nr = int(r.get("nr", -1))
        except (TypeError, ValueError): continue
        rub = str(r.get("rubrik", "")).lower()
        if 0 <= nr < len(cands) and rub in ("news", "radar", "projekte"):
            out.append((cands[nr], rub))
    log(f"Triage: {len(out)} ausgewählt", [c["titel"][:50] for c, _ in out])
    return out


def page_text(url, limit=7000):
    try:
        r = requests.get(url, headers=UA, timeout=25)
        t = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", r.text)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
        return re.sub(r"\s+", " ", t)[:limit]
    except Exception as e:  # noqa
        return f"(Seite nicht ladbar: {e})"


SCHEMA = """
Gemeinsame Felder:
- "titel": prägnante deutsche Schlagzeile
- "kurz": 1–2 Sätze Zusammenfassung
- "artikel": Liste von Absätzen (150–350 Wörter gesamt), Zwischenüberschriften als eigener Eintrag "## Überschrift"
- "quellen": [{"titel": ..., "url": ...}] (mindestens die Original-URL)
- "demo": einer von "video","bild","musik","stimme","code","game","modell","3d","agent","security","paper"
- "machen": 2–3 kurze Sätze: was kann ein Kreativer/eine Privatperson damit konkret tun?
- "ausprobieren" (nur wenn es ein nutzbares Tool gibt): {"prompt": kopierbarer Beispiel-Prompt, "tool": Name, "url": offizielle Startseite}
- "vorschau": Ergebnis-Vorschau passend zum Eintrag. Eine der Szenen:
   {"szene":"terminal","titel":"<programm>","zeilen":["> Eingabe","✓ Erfolg","⚠ Warnung","- entfernt","+ hinzugefügt","● Status"]}
   {"szene":"balken","titel":"<was>","balken":[{"label":..,"wert":Zahl,"anzeige":"Text"}]}  (nur echte Zahlen aus der Quelle; letzter Balken = das Neue)
   {"szene":"moe","titel":"<aktiv> von <gesamt> aktiv","gesamt":Zahl,"aktiv":Zahl}
   {"szene":"netz","zeilen":[4 kurze Labels]}
   {"szene":"stadt"|"natur"|"zug"|"sport"|"dose"|"buehne","badges":[..],"dauer":"0:30"} (Video)
   {"szene":"runner"|"flug"|"fahren"} (Spiele), {"szene":"logo","titel":"<Name>"}, {"szene":"tv"}, {"szene":"sandbox"}, {"szene":"schnitt","titel":".."}
   Musik: {"titel":"<Song>","untertitel":"<Künstler · Info>","zeilen":[2 Fakten, KEINE Songtexte]}
   Stimme: {"titel":"Aufnahme 0:10","sprachen":[["Sprache","Beispielsatz"],x3]}
   Optional "tag": kurzes Label.
Rubrik "news": zusätzlich "bereich": "Video"|"Bild"|"Musik"|"Stimme"|"Text"|"Apps"|"3D"|"Agenten"|"Recht", "datum": ISO-Datum des Ereignisses
Rubrik "radar": zusätzlich "quelle": "GitHub"|"Hugging Face"|"arXiv"|"X"|"Hacker News"|"Lab-Blog"|"Reddit"|"Fachpresse", "datum", "kennzahlen": [{"label","wert"}] harte Specs, "signal", "link", "linkLabel"
Rubrik "projekte": zusätzlich "macher", "branche", "jahr", "tools": [..], "kennzahlen", "link", "linkLabel"
"""


def write_article(c, rubrik):
    text = page_text(c["url"])
    prompt = f"""Schreibe für „State of the AI“ einen deutschen Eintrag der Rubrik "{rubrik}".
Nutze NUR Fakten aus dem Material unten. Schreibe komplett in eigenen Worten, höchstens ein Zitat unter 15 Wörtern.
Erkläre Fachbegriffe kurz. Kennzeichne Herstellerangaben als solche. Keine Gerüchte, nichts erfinden.
Wenn das Material zu dünn oder irrelevant ist, antworte nur mit {{"skip": true}}.

Fund: {c['titel']} ({c['quelle']}, {c['signal']})
URL: {c['url']}
Zusatzinfo: {c['info']}
Seiteninhalt (Auszug): {text}

Gib NUR ein JSON-Objekt zurück mit diesen Feldern:{SCHEMA}"""
    return ask(prompt, 3500)


def slug(s):
    s = s.lower().translate(str.maketrans("äöüß", "aous"))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or f"eintrag-{int(time.time())}"


# ---------------- 5. Speichern ----------------
def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for col in ("news", "radar", "projekte", "bereiche"):
        data.setdefault(col, [])
    seen = known_urls(data)
    cands = [c for c in collect() if c["url"].rstrip("/") not in seen]
    # Pro Quelle nur die stärksten, damit der Triage-Aufruf klein bleibt
    cands.sort(key=lambda c: c["score"], reverse=True)
    per, picked = {}, []
    for c in cands:
        if per.get(c["quelle"], 0) < 6:
            picked.append(c); per[c["quelle"]] = per.get(c["quelle"], 0) + 1
    log(f"{len(picked)} neue Kandidaten")
    added = 0
    if picked and os.environ.get("ANTHROPIC_API_KEY"):
        titles = [d.get("titel", "") for col in ("news", "radar", "projekte") for d in data[col]]
        for c, rubrik in triage(picked, titles):
            try:
                art = write_article(c, rubrik)
            except Exception as e:  # noqa
                log("Artikel fehlgeschlagen:", c["titel"], e); continue
            if not isinstance(art, dict) or art.get("skip") or not art.get("titel"):
                continue
            art["id"] = slug(art["titel"])
            art["hinzugefuegt"] = NOW.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            art.setdefault("quellen", [{"titel": c["quelle"], "url": c["url"]}])
            if rubrik != "news":
                art.setdefault("link", c["url"])
            if any(d.get("id") == art["id"] for d in data[rubrik]):
                art["id"] += "-" + str(int(time.time()))
            data[rubrik].append(art); added += 1
            log("+", rubrik, art["titel"])
    elif picked:
        log("Kein ANTHROPIC_API_KEY gesetzt – es werden keine Artikel geschrieben.")
    for col in ("news", "radar", "projekte"):
        data[col] = sorted(data[col], key=lambda d: d.get("hinzugefuegt", ""), reverse=True)[:MAX_ITEMS]
    data["meta"] = {"letzterScan": NOW.replace(microsecond=0).isoformat().replace("+00:00", "Z"), "neueFunde": added}
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Fertig: {added} neue Einträge")


if __name__ == "__main__":
    sys.exit(main())
