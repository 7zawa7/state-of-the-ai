# State of the AI – Live bringen

Diese Anleitung bringt deine Seite in rund 30 Minuten online. Danach scannt sie **alle 15 Minuten** automatisch nach neuen KI-Funden und schreibt Artikel, ohne dass du etwas tun musst.

**Was im Paket steckt**

| Ordner/Datei | Wofür |
|---|---|
| `docs/index.html` | Die komplette Seite (App-Ansicht + Zeitung) |
| `docs/data.json` | Alle Artikel. Wird vom Scanner automatisch erweitert |
| `docs/logo.svg` | Logo, auch als Browser-Icon |
| `docs/impressum.html`, `docs/datenschutz.html` | Vorlagen, musst du ausfüllen |
| `docs/fonts/` | Platz für die Zeitungsschriften (siehe Schritt 6) |
| `scanner/scan.py` | Der Scanner |
| `.github/workflows/scan.yml` | Startet den Scanner alle 15 Minuten |

**So funktioniert es**

1. GitHub startet alle 15 Minuten den Scanner (kostenlos).
2. Der Scanner fragt kostenlose Quellen ab: Hugging Face (Trending-Modelle und -Papers), GitHub (neue Repos), Hacker News und RSS-Feeds von Fachpresse und Lab-Blogs.
3. Nur wenn es Neues gibt, wählt ein kleines KI-Modell die wichtigsten Funde aus und schreibt dazu Artikel, inklusive Vorschau-Animation, „Was du damit machen kannst“ und Prompt zum Ausprobieren.
4. Die neue `data.json` wird gespeichert, GitHub Pages veröffentlicht sie, und die Seite lädt jede Minute nach.

---

## Was du brauchst

- Einen **GitHub-Account** (kostenlos): https://github.com/signup
- Einen **API-Schlüssel von Anthropic** mit etwas Guthaben: https://console.anthropic.com. Das ist nicht dasselbe wie dein Claude-Abo, die API wird separat nach Verbrauch abgerechnet.
- Optional: eine eigene **Domain** (z. B. `stateofthe.ai`), etwa 10–40 € im Jahr je nach Endung

---

## Schritt 1 – Repository anlegen

1. Auf GitHub oben rechts **+ → New repository**.
2. Name: `state-of-the-ai`.
3. **Public** wählen. Bei öffentlichen Repos sind die Actions-Minuten kostenlos und unbegrenzt. Bei privaten Repos sind nur 2.000 Minuten im Monat frei, das reicht nicht für alle 15 Minuten.
4. **Create repository**.

## Schritt 2 – Dateien hochladen

1. Entpacke das ZIP auf deinem Rechner.
2. Im neuen Repo auf **uploading an existing file** klicken.
3. Den **Inhalt** des Ordners `state-of-the-ai` (also `docs`, `scanner`, `.github`, `README.md`) per Drag & Drop ins Fenster ziehen.
4. **Wichtig:** Der Ordner `.github` ist versteckt. Auf dem Mac zeigst du ihn im Finder mit `Cmd + Shift + .` an, unter Windows über *Ansicht → Ausgeblendete Elemente*.
5. Unten auf **Commit changes**.

> Alternative ohne Gefummel: [GitHub Desktop](https://desktop.github.com) installieren, Repo klonen, Dateien hineinkopieren, *Commit* und *Push*.

## Schritt 3 – API-Schlüssel hinterlegen

1. Im Repo: **Settings → Secrets and variables → Actions → New repository secret**.
2. Name: `ANTHROPIC_API_KEY`, Wert: dein Schlüssel aus der Anthropic Console.
3. **Add secret**. Der Schlüssel ist danach für niemanden sichtbar, auch nicht im Code.

## Schritt 4 – Schreibrechte für den Scanner

**Settings → Actions → General → Workflow permissions** auf **Read and write permissions** stellen und **Save** klicken.

## Schritt 5 – Seite veröffentlichen (GitHub Pages)

1. **Settings → Pages**.
2. *Source*: **Deploy from a branch**.
3. *Branch*: `main`, Ordner: **`/docs`**, dann **Save**.
4. Nach 1–2 Minuten steht oben die Adresse, z. B. `https://DEINNAME.github.io/state-of-the-ai/`. Deine Seite ist live.

## Schritt 6 – Zeitungsschriften selbst hosten (Datenschutz)

Schriften direkt von Google zu laden ist in Deutschland datenschutzrechtlich heikel. Deshalb lädt die Seite sie aus dem eigenen Ordner.

1. Öffne https://gwfh.mranftl.com/fonts.
2. Lade jeweils die **woff2**-Dateien für *latin* herunter:
   - UnifrakturMaguntia: regular
   - Playfair Display: 700, 900, 700 italic
   - Libre Caslon Text: regular, italic, 700
   - Special Elite: regular
   - Newsreader: regular, 500, italic, 500 italic (Startseite)
   - Schibsted Grotesk: regular, 500, 600 (Startseite)
   - IBM Plex Mono: regular, 500 (Startseite)
3. Lade sie in den Ordner `docs/fonts/` hoch. Die Dateinamen müssen zu `docs/fonts/fonts.css` passen. Falls sie leicht anders heißen, passe sie in der CSS-Datei an.

Solange die Dateien fehlen, funktioniert alles trotzdem, nur mit Ersatzschriften.

## Schritt 7 – Ersten Scan starten

1. Im Repo auf **Actions → KI-Scan → Run workflow**.
2. Nach etwa 1–2 Minuten ist der Lauf grün. Im Log siehst du z. B. `+ radar …` für neue Einträge.
3. Ab jetzt läuft er automatisch alle 15 Minuten.

## Schritt 8 – Impressum und Datenschutz ausfüllen

Öffne `docs/impressum.html` und `docs/datenschutz.html` direkt auf GitHub (Stift-Symbol) und ersetze alles in `[eckigen Klammern]`.

Eine öffentliche Seite braucht in Deutschland ein Impressum mit ladungsfähiger Anschrift. Wenn du deine Wohnadresse nicht zeigen willst, gibt es Impressum- bzw. Adress-Services für einige Euro im Monat. Ich bin kein Anwalt: Bei Zweifeln lass die Texte kurz prüfen oder nutze einen Generator wie den von e-recht24.

## Schritt 9 (optional) – Eigene Domain

1. Domain kaufen (z. B. bei INWX, Namecheap, Strato).
2. **Settings → Pages → Custom domain**: Domain eintragen und speichern.
3. Beim Domain-Anbieter die DNS-Einträge setzen, die GitHub dort anzeigt (für `www` einen CNAME auf `DEINNAME.github.io`).
4. **Enforce HTTPS** anhaken, sobald es verfügbar ist.

## Schritt 10 – Instagram

Den Link in deine Bio packen und eines der Reels posten. Fertig.

---

## Kosten im Griff behalten

| Posten | Kosten |
|---|---|
| GitHub Pages + Actions (öffentliches Repo) | 0 € |
| Quellen (Hugging Face, GitHub, HN, RSS) | 0 € |
| KI-Artikel | Nach Verbrauch, kleines Modell, nur bei echten Funden. Aktuelle Preise: https://docs.claude.com |
| Domain (optional) | ca. 10–40 € / Jahr |

**Stellschrauben** (Settings → Secrets and variables → Actions → Tab *Variables*):

- `MAX_NEW`: maximal neue Artikel pro Lauf (Standard 4)
- `MODEL`: Modellname (Standard `claude-haiku-5-5`, das kleinste und günstigste)
- Seltener scannen: in `.github/workflows/scan.yml` die `cron`-Zeile ändern, z. B. `"7 * * * *"` für stündlich

**Unbedingt:** In der Anthropic Console unter *Billing* ein **monatliches Ausgabenlimit** setzen. Dann kann nie mehr abgebucht werden als geplant.

---

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| Seite zeigt „offline“ | `docs/data.json` fehlt oder ist kaputt. Im Repo prüfen. |
| Action rot mit `403` beim Push | Schritt 4 vergessen (Schreibrechte). |
| Action läuft, aber keine Artikel | Secret `ANTHROPIC_API_KEY` fehlt oder hat kein Guthaben, oder es gab schlicht nichts Neues. |
| Action startet nicht alle 15 Minuten | GitHub verzögert geplante Läufe bei hoher Last; das ist normal. Nach 60 Tagen ohne Commits pausiert GitHub Zeitpläne, die laufenden Scans committen aber selbst. |
| Eine Quelle meldet Fehler im Log | Egal, die anderen laufen weiter. Defekte RSS-Feeds in `RSS_FEEDS` in `scanner/scan.py` löschen oder austauschen. |
| Falscher oder schlechter Artikel | In `docs/data.json` den Eintrag löschen (Stift-Symbol auf GitHub) und speichern. |
