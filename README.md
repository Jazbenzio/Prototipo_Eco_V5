# Eco - Asistente virtual de estudio

## Instalación
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # y pon tu API key
python main.py
```

## Equipo
- **Persona 1 (Visión):** `vision/` -> `obtener_contexto_visual()`
- **Persona 2 (Voz y cerebro):** `voz/`, `cerebro/` -> `preguntar(texto, imagen, modo)`
- **Persona 3 (UI y memoria):** `ui/`, `memoria/` -> `guardar_eco()`, `ecos_pendientes()`

Ramas de Git: `vision`, `voz`, `ui`.
