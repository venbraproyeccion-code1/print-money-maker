#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKET RADAR — VenBraX print-money-maker
=========================================
Módulo 1 del pipeline: detecta tendencias calientes en YouTube y (opcional)
las combina con un export de tendencias de Pinterest.

Flujo:
  1. Busca en YouTube los videos más relevantes para cada palabra clave
     (usa yt-dlp: primero el submódulo local en tools/yt-dlp, si no, el paquete pip).
  2. Extrae título, etiquetas, vistas, canal y descripción de cada video.
  3. Si se pasa --pinterest-json, carga ese archivo (generado por el repo
     hermano Pinterest-Scraper) y lo suma al análisis con el mismo peso
     editorial que un video.
  4. Analiza todo el texto y cuenta los términos y bigramas más repetidos
     (filtrando stopwords en español e inglés).
  5. Guarda el resultado en data/trends_detected.json — insumo directo
     para src/product_generator.py.

Integración con Pinterest-Scraper:
  Este módulo NO scrapea Pinterest directamente (ese trabajo con Selenium
  vive en su propio repo, Pinterest-Scraper). Lo que hace es leer un JSON
  que ese scraper exporte, con este esquema mínimo por item:
    [{"title": "...", "description": "...", "tags": ["...", ...]}, ...]
  (mismo esquema que un video de YouTube, para que analyze_trends() lo
  procese sin cambios). Ver load_pinterest_export() más abajo.

Uso:
  python src/market_radar.py
  python src/market_radar.py --keywords "n8n" "make.com" --max-videos 15
  python src/market_radar.py --pinterest-json data/pinterest_export.json
  python src/market_radar.py --output data/mi_radar.json
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# yt-dlp: preferir el submódulo local (tools/yt-dlp), luego el paquete pip
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
SUBMODULE_YTDLP = REPO_ROOT / "tools" / "yt-dlp"

if (SUBMODULE_YTDLP / "yt_dlp").is_dir():
    sys.path.insert(0, str(SUBMODULE_YTDLP))

try:
    from yt_dlp import YoutubeDL
except ImportError:
    sys.exit(
        "[ERROR] yt-dlp no está disponible.\n"
        "  Opción A: pip install -r requirements.txt\n"
        "  Opción B: git submodule update --init tools/yt-dlp"
    )

# ---------------------------------------------------------------------------
# Configuración por defecto
# ---------------------------------------------------------------------------
DEFAULT_KEYWORDS = ["n8n", "automatización IA", "agentes autónomos"]
DEFAULT_MAX_VIDEOS = 10
DEFAULT_OUTPUT = REPO_ROOT / "data" / "trends_detected.json"

# Stopwords ES + EN (mínimas y suficientes para títulos/tags de YouTube)
STOPWORDS = {
    # español
    "al", "algo", "como", "con", "cuando", "del", "desde", "donde",
    "ella", "entre", "era", "esta", "este", "esto", "estos",
    "estas", "hace", "hasta", "hay", "las", "les", "los",
    "mas", "muy", "nos", "otra", "otro", "para",
    "pero", "por", "porque", "que", "ser", "sin",
    "sobre", "son", "sus", "tiene", "tus", "una",
    "uno", "unos", "unas", "como", "asi", "ese", "esa",
    "mis", "nuestro", "nuestra", "vamos", "puede", "puedes", "todo", "toda",
    "todos", "todas", "esta", "estan", "fue",
    # inglés
    "and", "are", "best", "but", "can",
    "for", "from", "get", "how", "just", "make", "new", "our",
    "that", "the", "this", "top", "use", "using", "what", "when",
    "why", "will", "with", "you", "your",
}

# Términos que son ruido de plataforma, no tendencia
PLATFORM_NOISE = {"youtube", "video", "videos", "shorts", "subscribe",
                  "suscribete", "canal", "channel", "link",
                  "links", "gratis", "free", "http", "https", "www", "com"}


# ---------------------------------------------------------------------------
# 1) EXTRACCIÓN — YouTube vía yt-dlp
# ---------------------------------------------------------------------------
def search_youtube(keyword: str, max_videos: int) -> list:
    """Busca en YouTube y devuelve metadatos completos de cada video."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,      # queremos tags + descripción completos
        "ignoreerrors": True,       # un video roto no tumba el radar
        "socket_timeout": 20,
    }
    query = f"ytsearch{max_videos}:{keyword}"

    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(query, download=False)

    videos = []
    for entry in (result or {}).get("entries") or []:
        if not entry:
            continue
        videos.append({
            "title": entry.get("title", ""),
            "url": entry.get("webpage_url") or entry.get("url", ""),
            "channel": entry.get("channel") or entry.get("uploader", ""),
            "views": entry.get("view_count") or 0,
            "duration_s": entry.get("duration") or 0,
            "upload_date": entry.get("upload_date", ""),
            "tags": entry.get("tags") or [],
            "description": (entry.get("description") or "")[:1500],
        })
    return videos


# ---------------------------------------------------------------------------
# 1b) EXTRACCIÓN — Pinterest (vía export de Pinterest-Scraper, no scrapea aquí)
# ---------------------------------------------------------------------------
def load_pinterest_export(path: Path) -> list:
    """Carga un JSON exportado por el repo Pinterest-Scraper y lo normaliza
    al mismo esquema que search_youtube() (title/tags/description/views),
    para que analyze_trends() los procese sin distinguir la fuente.

    Esquema mínimo esperado por item: {"title": str, "description": str,
    "tags": [str, ...]}. Campos extra se ignoran; campos ausentes usan
    valores vacíos en lugar de fallar (un pin mal formado no tumba el radar).
    """
    if not path.exists():
        print(f"[WARN] No existe el export de Pinterest: {path}")
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] No pude leer el export de Pinterest ({path}): {exc}")
        return []

    items = raw if isinstance(raw, list) else raw.get("pins", raw.get("items", []))
    pins = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pins.append({
            "title": item.get("title", ""),
            "url": item.get("url") or item.get("link", ""),
            "channel": item.get("board") or item.get("author", ""),
            "views": item.get("saves") or item.get("views") or 0,
            "duration_s": 0,
            "upload_date": item.get("date", ""),
            "tags": item.get("tags") or item.get("hashtags") or [],
            "description": (item.get("description") or "")[:1500],
        })
    return pins


# ---------------------------------------------------------------------------
# 2) ANÁLISIS — términos y bigramas más repetidos
# ---------------------------------------------------------------------------
def normalize(text: str) -> str:
    """minúsculas + sin acentos (agrupa 'automatización'/'automatizacion')."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenize(text: str) -> list:
    words = re.findall(r"[a-záéíóúüñ0-9][a-záéíóúüñ0-9\-\.]{2,}", text.lower())
    clean = []
    for w in words:
        n = normalize(w).strip(".-")
        if len(n) < 3 or n in STOPWORDS or n in PLATFORM_NOISE or n.isdigit():
            continue
        clean.append(n)
    return clean


def analyze_trends(videos: list) -> dict:
    """Cuenta términos y bigramas ponderando: tags > títulos > descripción."""
    unigrams = Counter()
    bigrams = Counter()

    for v in videos:
        # peso 3: tags (señal editorial directa del creador)
        for tag in v["tags"]:
            for tok in tokenize(tag):
                unigrams[tok] += 3
        # peso 2: título
        title_toks = tokenize(v["title"])
        for tok in title_toks:
            unigrams[tok] += 2
        for i in range(len(title_toks) - 1):
            bigrams[f"{title_toks[i]} {title_toks[i+1]}"] += 2
        # peso 1: descripción
        desc_toks = tokenize(v["description"])
        for tok in desc_toks:
            unigrams[tok] += 1
        for i in range(len(desc_toks) - 1):
            bigrams[f"{desc_toks[i]} {desc_toks[i+1]}"] += 1

    return {
        "hot_terms": [{"term": t, "score": s} for t, s in unigrams.most_common(30)],
        "hot_phrases": [{"phrase": p, "score": s} for p, s in bigrams.most_common(20)],
    }


# ---------------------------------------------------------------------------
# 3) ORQUESTACIÓN + SALIDA JSON
# ---------------------------------------------------------------------------
def run_radar(keywords: list, max_videos: int, output: Path,
             pinterest_json: Path = None) -> dict:
    all_videos = []
    per_keyword = {}

    for kw in keywords:
        print(f"[RADAR] Escaneando YouTube: '{kw}' (top {max_videos})...")
        try:
            videos = search_youtube(kw, max_videos)
        except Exception as exc:  # red caída, bloqueo, etc.
            print(f"[WARN]  Falló la búsqueda de '{kw}': {exc}")
            videos = []
        print(f"[RADAR]   -> {len(videos)} videos capturados")
        per_keyword[kw] = {
            "videos_found": len(videos),
            "trends": analyze_trends(videos),
            "top_videos": sorted(videos, key=lambda v: v["views"], reverse=True)[:5],
        }
        all_videos.extend(videos)

    pinterest_pins = []
    if pinterest_json:
        print(f"[RADAR] Cargando export de Pinterest: {pinterest_json}...")
        pinterest_pins = load_pinterest_export(pinterest_json)
        print(f"[RADAR]   -> {len(pinterest_pins)} pins cargados")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "keywords_scanned": keywords,
        "total_videos_analyzed": len(all_videos),
        "total_pins_analyzed": len(pinterest_pins),
        "global_trends": analyze_trends(all_videos + pinterest_pins),
        "youtube_trends": analyze_trends(all_videos),
        "pinterest_trends": analyze_trends(pinterest_pins) if pinterest_pins else None,
        "by_keyword": per_keyword,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"[RADAR] Reporte guardado en: {output}")

    # resumen ejecutivo en consola
    top = report["global_trends"]["hot_terms"][:10]
    if top:
        print("\nTOP 10 TENDENCIAS DETECTADAS:")
        for i, t in enumerate(top, 1):
            print(f"  {i:2d}. {t['term']:<25} (score {t['score']})")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Market Radar — detecta tendencias calientes en YouTube")
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS,
                        help="Palabras clave a escanear")
    parser.add_argument("--max-videos", type=int, default=DEFAULT_MAX_VIDEOS,
                        help="Videos por palabra clave (default: 10)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Ruta del JSON de salida")
    parser.add_argument("--pinterest-json", type=Path, default=None,
                        help="JSON exportado por Pinterest-Scraper a sumar al análisis")
    args = parser.parse_args()
    run_radar(args.keywords, args.max_videos, args.output, args.pinterest_json)


if __name__ == "__main__":
    main()
