# Estadística Ambiental

Base de conocimiento Python para el **ciclo estadístico completo** aplicado a datos ambientales —
EDA, estadística descriptiva e inferencial, modelos predictivos y reportes de cumplimiento normativo.
Metodología de estándares internacionales (ISO, WMO, literatura peer-reviewed) con implementación de
referencia para Colombia.

[![CI](https://github.com/DanMendezZz/Estadistica_Ambiental/actions/workflows/ci.yml/badge.svg)](https://github.com/DanMendezZz/Estadistica_Ambiental/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/DanMendezZz/Estadistica_Ambiental/branch/main/graph/badge.svg)](https://codecov.io/gh/DanMendezZz/Estadistica_Ambiental)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/DanMendezZz/Estadistica_Ambiental/blob/main/LICENSE)

---

## ¿Qué es esto?

Este repositorio es una **base de conocimiento, no un producto**. Reúne metodología documentada,
normas colombianas integradas en código y un pipeline validado sobre datos reales (PM2.5 horario en
Cundinamarca) para que cualquier analista de una entidad ambiental pueda **reutilizar el ciclo
estadístico** sin redescubrirlo cada vez.

Cubre **16 líneas temáticas** organizadas en tres bloques:

- **A — Gestión:** áreas protegidas, predios de conservación, gestión del riesgo, ordenamiento
  territorial, dirección directiva.
- **B — Transversales:** cambio climático, sistemas de información ambiental, geoespacial.
- **C — Técnicas:** calidad del aire, recurso hídrico, oferta hídrica, humedales, páramos, POMCA,
  PUEAA, rondas hídricas.

## Enlaces clave

- **[Empezar](getting-started.md)** — instalación y quick start.
- **[Metodología](metodologia.md)** — el ciclo EDA → Descriptiva → Inferencial → Predictiva.
- **[Modelos](modelos.md)** — catálogo de modelos disponibles y cuándo usarlos.
- **[Líneas temáticas](lineas_tematicas.md)** — fichas de dominio por línea.
- **[ADRs](decisiones.md)** — decisiones de diseño documentadas.
- **[API Reference](api.md)** — documentación auto-generada de los módulos.

## Alcance

Los métodos estadísticos (SARIMA, Kriging, GWR, I de Moran, XGBoost, Prophet, etc.) son estándares
internacionales aplicables a cualquier contexto ambiental. La capa de dominio — normas regulatorias,
fuentes de datos, umbrales, índices — está calibrada para Colombia y el Sistema Nacional Ambiental
(SINA). Adaptar el repo a otro país implica únicamente reemplazar las constantes de `config.py` con
la normativa local.
