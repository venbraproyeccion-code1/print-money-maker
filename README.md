# Print Money Maker 💸
Sistema automatizado de inteligencia de mercado, generación y auditoría de productos digitales de la suite VenBraX.

## Estructura del Proyecto
* **src/**: Scripts principales del radar de tendencias, generador y auditor.
* **tools/**: Submódulos enlazados de herramientas externas de automatización.
* **mockups/**: Mockups estáticos de identidad/e-commerce (HTML autocontenido, sin build), para revisar
  en navegador antes de portarlos a un tema real de Shopify.

## Estado real (2026-08-02)

- **`content_ideas_generator.py`** — ✅ implementado y probado con datos reales. **Prioridad actual**:
  genera ideas de contenido GRATUITO (no producto pago) para crecimiento orgánico — cada idea trae
  plataforma, gancho, caption y prompt visual, en el mismo formato que espera el nodo "Config — Marca y
  Prompt" del pipeline de Lyra (n8n), listo para copiar/pegar. Usa `nvidia/nemotron-3-ultra-550b-a55b`.

  ```bash
  pip install -r requirements.txt
  export NVIDIA_API_KEY=nvapi-...
  python src/content_ideas_generator.py guayaba "tendencia o dato real aqui"
  # o: python src/content_ideas_generator.py venbrax "tendencia o dato real aqui"
  ```

- **`product_generator.py`** — implementado y probado, pero **pausado por decisión de Alfonso (2026-08-02)**:
  genera conceptos de producto digital PAGO (curso/ebook). Se prioriza primero construir audiencia con
  contenido gratuito (ver arriba); esto se retoma cuando haya tracción real, no antes.

- **`market_radar.py`** y **`marketing_auditor.py`** — todavía vacíos, sin construir.

- **`mockups/pdp-command-nexus.html`** — mockup de la página de producto (PDP) "The Command Nexus"
  del rebranding VENBRAX (identidad "angular", titanium frío + acentos neón). Incluye el reveal de
  logo tipo "corte láser", el "Anillo de Integridad" pulsante alrededor del CTA principal y la
  garantía dinámica ("Protocolo VENBRAX activo: latencia de cifrado < 0.01ms"). Ábrelo directo en el
  navegador — no requiere build ni dependencias. Es un punto de partida visual para el tema de
  Shopify/Storefront, no una implementación de theme Liquid.
