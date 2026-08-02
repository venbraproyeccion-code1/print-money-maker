"""
Print Money Maker - Generador de Ideas de Contenido Gratuito
==============================================================
Toma una marca (guayaba/venbrax) y una tendencia o dato de mercado REAL
(nunca inventado) y genera varias ideas de publicaciones GRATUITAS listas
para el pipeline de Lyra (n8n), orientadas a crecimiento organico (seguidores,
likes, alcance) -- no a vender un producto pago.

Cada idea sale en el mismo formato que espera el nodo "Config - Marca y
Prompt" del workflow de Lyra: brand, prompt (para fal.ai/Replicate) y caption
(para Buffer). Se pueden copiar directo ahi.

El input SIEMPRE debe ser un dato real -- este script nunca inventa datos de
mercado, solo redacta y estructura a partir de lo que se le da (regla #18 del
ecosistema VenBraX: no inventar contenido).

Uso:
    NVIDIA_API_KEY=nvapi-... python content_ideas_generator.py <brand> "tendencia real aqui"

    <brand> es "guayaba" o "venbrax"

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

BRAND_ANGLES = {
    "guayaba": "exponer mecanicas reales de estafas financieras/cripto en LATAM (Ponzi, trading "
               "garantizado, bots milagrosos) -- NUNCA educacion financiera generica de ahorro/inversion.",
    "venbrax": "automatizacion con IA, ciberseguridad y gobernanza de negocios -- casos concretos y "
               "tecnicos, no charla motivacional generica.",
}

SYSTEM_TEMPLATE = """Eres el Director Creativo de {brand} (VenBraX). Tu objetivo NO es producir \
contenido -- es producir ATENCION, CONFIANZA y CONVERSION. Recibes UN dato/tendencia real (nunca lo \
inventes, nunca lo cambies, nunca agregues cifras que no te dieron). El objetivo de estas piezas es \
CRECIMIENTO ORGANICO (seguidores, likes, alcance) -- contenido gratuito, no un producto pago. El angulo \
de la marca es: {angle}

FILOSOFIA (obligatoria en cada pieza):
- Cada publicacion debe sentirse creada para UNA persona, nunca para un algoritmo: natural, autentica, \
organica, emocional, humana, moderna -- sin aparentar automatizacion ni IA.
- Contenido FACELESS: no depende del rostro de un creador. La historia sostiene el video, el mensaje \
sostiene la atencion, las imagenes sostienen la emocion.
- Estructura de la caption: Hook inmediato -> Curiosidad -> Microhistoria -> Valor -> Confianza -> \
Cierre natural -> Llamado a la accion elegante (NUNCA agresivo, nunca "compra ya", nunca suena a ad).
- Prohibido: que la pieza parezca publicidad, que parezca generada por IA, y repetir la misma \
estructura, edicion, ritmo o voz narrativa entre las {n} ideas de esta tanda -- cada una debe sentirse \
unica y usar una voz narrativa distinta (ej: confesion personal, investigacion/denuncia, advertencia \
urgente, historia de un tercero, pregunta retorica directa al espectador).

Genera exactamente {n} ideas de publicacion DISTINTAS a partir del mismo dato, cada una con voz \
narrativa, ritmo y estructura de edicion diferentes entre si. Devuelve SOLO un array JSON valido, sin \
markdown ni texto extra, donde cada elemento tenga exactamente estas claves:
- platform (string: "tiktok", "instagram", o "linkedin")
- narrative_voice (string, la voz narrativa elegida para ESTA pieza, ej: "confesion personal", \
"investigacion", "advertencia urgente", "historia de un tercero", "pregunta directa")
- hook (string, primera linea, debe frenar el scroll en 1 segundo, sin sonar a ad ni a IA)
- caption (string, en espanol, siguiendo la estructura Hook->Curiosidad->Microhistoria->Valor->Confianza->\
Cierre elegante, tono organico y humano, NUNCA generico ni publicitario, basado EXCLUSIVAMENTE en el dato \
real recibido, sin inventar cifras ni hechos ni testimonios)
- image_prompt (string, en ingles, descripcion cinematografica y visual concreta para un generador de \
imagen/video IA, orientada a contenido FACELESS -- b-roll, simbolismo visual, texto en pantalla, entornos, \
objetos -- evita primeros planos de rostro hablando salvo que sea estrictamente necesario)
- pacing_note (string, una frase sobre el ritmo/edicion de ESTA pieza para que se distinga de las demas \
de la misma tanda, ej: "corte rapido cada 1-2s, energia alta" vs "toma unica sostenida, tension lenta")
- format_note (string, una frase: por que este formato/plataforma encaja con este dato)

No inventes estadisticas, testimonios, ni resultados. Si el dato de entrada no da para contenido serio, \
dilo en un solo elemento del array con platform:"ninguna" en vez de forzar contenido vacio."""


def generate_content_ideas(brand: str, trend: str, n: int = 3) -> list:
    if brand not in BRAND_ANGLES:
        raise ValueError(f"brand debe ser una de {list(BRAND_ANGLES)}, recibido: {brand}")

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno NVIDIA_API_KEY")

    system_prompt = SYSTEM_TEMPLATE.format(brand=brand, angle=BRAND_ANGLES[brand], n=n)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Dato/tendencia real: {trend}"},
        ],
        "temperature": 0.6,
        "max_tokens": 3200,
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
    match = re.search(r"\[[\s\S]*\]", cleaned)
    if not match:
        raise ValueError(f"El modelo no devolvio un array JSON valido:\n{raw}")
    return json.loads(match.group(0))


def save_ideas(brand: str, trend: str, ideas: list, out_dir: str = "output") -> str:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(out_dir, f"ideas-{brand}-{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Ideas de contenido gratuito -- {brand}\n\n")
        f.write(f"**Dato/tendencia de origen:** {trend}\n\n")
        for i, idea in enumerate(ideas, 1):
            f.write(f"## Idea {i} -- {idea.get('platform', '?')} ({idea.get('narrative_voice', '?')})\n\n")
            f.write(f"**Gancho:** {idea.get('hook', '')}\n\n")
            f.write(f"**Caption (para nodo Config -> caption):**\n{idea.get('caption', '')}\n\n")
            f.write(f"**Prompt visual (para nodo Config -> prompt):**\n{idea.get('image_prompt', '')}\n\n")
            f.write(f"**Ritmo/edicion:** {idea.get('pacing_note', '')}\n\n")
            f.write(f"**Por que este formato:** {idea.get('format_note', '')}\n\n")
            f.write("---\n\n")
    return path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python content_ideas_generator.py <guayaba|venbrax> \"tendencia o dato real\"")
        sys.exit(1)
    brand_input = sys.argv[1]
    trend_input = " ".join(sys.argv[2:])
    ideas_result = generate_content_ideas(brand_input, trend_input)
    saved_path = save_ideas(brand_input, trend_input, ideas_result)
    print(f"Ideas generadas -> {saved_path}")
    print(json.dumps(ideas_result, indent=2, ensure_ascii=False))
