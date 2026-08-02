"""
Print Money Maker - Generador de Productos Digitales
======================================================
Toma una tendencia o dato de mercado REAL (nunca inventado) y genera un
concepto de producto digital completo usando NVIDIA Nemotron: titulo,
descripcion, publico objetivo, esquema de contenido y precio sugerido.

El input SIEMPRE debe ser un dato real (una tendencia observada, un problema
de un cliente, un hallazgo del Auditor de Oportunidades) -- este script nunca
inventa datos de mercado, solo redacta y estructura a partir de lo que se le
da (regla #18 del ecosistema VenBraX: no inventar contenido).

Uso:
    NVIDIA_API_KEY=nvapi-... python product_generator.py "tendencia real aqui"

Requiere: pip install requests
"""

import json
import os
import sys
import re
from datetime import datetime, timezone

import requests

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"

SYSTEM_PROMPT = """Eres el generador de productos digitales de VenBraX. Recibes UNA tendencia \
o dato de mercado real (nunca lo inventes, nunca lo cambies, nunca agregues cifras que no te dieron). \
A partir de ESE dato, diseña un concepto de producto digital vendible (ebook, mini-curso, plantilla, \
o herramienta) para el ecosistema VenBraX (automatizacion IA, ciberseguridad, finanzas educativas LATAM).

Devuelve SOLO un objeto JSON valido, sin markdown ni texto extra, con exactamente estas claves:
- title (string, en espanol, gancho concreto)
- tagline (string, una frase de venta, sin superlativos vacios)
- description (string, 3-4 frases, honesta, sin prometer resultados que no se pueden garantizar)
- target_audience (string, especifico: quien es, que rol, que nivel)
- format (string: "ebook", "mini-curso", "plantilla", o "herramienta")
- outline (array de strings, 5 a 8 modulos/capitulos concretos)
- suggested_price_brl (numero, basado en el rango real de mercado brasileno para productos digitales \
similares, nunca inventado sin logica: productos educativos digitales tipicos van de R$27 a R$197)
- price_reasoning (string, por que ese precio, en una frase)
- marketing_angle (string, el angulo de venta principal, conectado al dato real recibido)

No inventes estadisticas, testimonios, ni resultados de clientes. Si el dato de entrada no da para \
un producto serio, dilo dentro de description en vez de forzar un producto vacio."""


def generate_product(trend: str) -> dict:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno NVIDIA_API_KEY")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Dato/tendencia real: {trend}"},
        ],
        "temperature": 0.5,
        "max_tokens": 1600,
    }
    resp = requests.post(
        NVIDIA_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]

    cleaned = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError(f"El modelo no devolvio JSON valido:\n{raw}")
    return json.loads(match.group(0))


def save_product(trend: str, product: dict, out_dir: str = "output") -> str:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(out_dir, f"producto-{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {product['title']}\n\n")
        f.write(f"> {product['tagline']}\n\n")
        f.write(f"**Dato/tendencia de origen:** {trend}\n\n")
        f.write(f"**Formato:** {product['format']}\n\n")
        f.write(f"**Publico objetivo:** {product['target_audience']}\n\n")
        f.write(f"**Descripcion:**\n{product['description']}\n\n")
        f.write(f"**Precio sugerido:** R${product['suggested_price_brl']}\n")
        f.write(f"_{product['price_reasoning']}_\n\n")
        f.write(f"**Angulo de marketing:** {product['marketing_angle']}\n\n")
        f.write("**Esquema de contenido:**\n")
        for i, item in enumerate(product["outline"], 1):
            f.write(f"{i}. {item}\n")
    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python product_generator.py \"tendencia o dato real\"")
        sys.exit(1)
    trend_input = " ".join(sys.argv[1:])
    result = generate_product(trend_input)
    saved_path = save_product(trend_input, result)
    print(f"Producto generado -> {saved_path}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
