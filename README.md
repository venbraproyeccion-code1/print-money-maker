# Print Money Maker 💸
Sistema automatizado de inteligencia de mercado, generación y auditoría de productos digitales de la suite VenBraX.

## Estructura del Proyecto
* **src/**: Scripts principales del radar de tendencias, generador y auditor.
* **tools/**: Submódulos enlazados de herramientas externas de automatización.

## Estado real (2026-08-02)

- **`product_generator.py`** — ✅ implementado y probado con datos reales. Toma una tendencia/dato de
  mercado real como argumento (nunca lo inventa) y usa NVIDIA Nemotron (`nvidia/nemotron-3-ultra-550b-a55b`)
  para generar un concepto de producto digital completo: título, descripción, público objetivo, esquema
  de contenido y precio sugerido (con lógica de mercado real, no inventado). Guarda el resultado en
  `src/output/producto-<timestamp>.md`.

  ```bash
  pip install -r requirements.txt
  export NVIDIA_API_KEY=nvapi-...
  python src/product_generator.py "tendencia o dato de mercado real aqui"
  ```

- **`market_radar.py`** y **`marketing_auditor.py`** — todavía vacíos, sin construir.
