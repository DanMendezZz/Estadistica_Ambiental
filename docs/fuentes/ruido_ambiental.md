# Ruido Ambiental

> **Responsable de la ficha:** Dan Méndez
> **Última sincronización:** 2026-09-09
> **Bloque:** B (transversal temática) — Alimenta: gestión de riesgo, ordenamiento territorial

---

## Resumen ejecutivo

Línea temática agregada en 2026-09 (issues #14/#33) para cubrir el control de ruido ambiental bajo la Resolución 627 de 2006, con la excepción de fuentes naturales del Art. 17 Parágrafo Segundo y la incertidumbre normativa introducida por la Ley 2450 de 2025 ("Ley contra el Ruido").

A diferencia de las demás líneas transversales (calidad del aire, cambio climático), esta ficha **no** documenta hallazgos empíricos de un NotebookLM de investigación externa ni evidencia de desempeño de modelos validada en este repo — el alcance actual es: capa de configuración normativa (`config.NORMA_RUIDO`), un validador de cumplimiento (`ruido_exceedance_report()`) y un notebook plantilla con datos sintéticos. No hay conector de datos automatizado ni benchmark de modelos predictivos propios de esta línea todavía.

---

## Objetivos

- Comparar mediciones de ruido ambiental (dB(A)) contra los estándares máximos permisibles de la Tabla 2 (Res. 627/2006), diferenciando sector y horario.
- Evitar reportar excedencias falsas cuando el nivel se explica por fuentes naturales sin intervención humana (Art. 17, Parágrafo Segundo).
- Dejar la puerta abierta a un conector de datos y validadores más completos cuando se identifique una fuente pública real (ver issue #33, sección "resto pendiente").

---

## Variables ambientales clave

| Variable | Unidad | Rango físico plausible | Frecuencia | Fuente habitual |
|---|---|---|---|---|
| Nivel de ruido / L_Aeq,T | dB(A) | 0–140 (`io/validators.py`) | Continua / sub-horaria idealmente | Sonómetro (medición puntual, no red continua) |

---

## Datos y fuentes

- **Sin conector automatizado hoy.** `io/connectors.py` no tiene una función `load_ruido_*` — a diferencia de calidad del aire (RMCAB/SIATA/OpenAQ), no se identificó todavía un portal público con series de ruido ambiental descargables.
- **Fuente real disponible:** mediciones puntuales de sonómetro realizadas por CARs/Secretarías de Ambiente ante quejas o procesos de licenciamiento — normalmente no publicadas como serie de tiempo continua.
- Si se identifica una fuente pública real, agregar el conector en `io/connectors.py` siguiendo el patrón de `load_rmcab`/`load_siata_aire` y actualizar esta ficha.
- Por lo mismo, esta línea **no** está registrada todavía en `scripts/run_linea_tematica.py` (no aparece en `--list`) — no es un olvido, es consecuencia directa de no tener conector ni notebook con datos reales aún.

---

## Indicadores y métricas oficiales

### Tabla 2 — Estándares Máximos Permisibles de Niveles de Ruido Ambiental (Art. 17, Res. 627/2006)

| Sector | Diurno (dB(A)) | Nocturno (dB(A)) |
|---|---|---|
| A — Hospitales, bibliotecas, guarderías, sanatorios, hogares geriátricos | 55 | 45 |
| B — Residencial, hotelería/hospedaje, universidades/colegios | 65 | 50 |
| C — Industrial (parques industriales, zonas portuarias, zonas francas) | 75 | 70 |
| C — Comercial (centros comerciales, talleres, gimnasios, bares, discotecas, casinos) | 70 | 55 |
| C — Oficinas / uso institucional | 65 | 50 |
| C — Espectáculos/vías (incl. troncales/autopistas/arterias, remite a Ley 769/2002) | 80 | 70 |
| D — Residencial suburbana, rural agropecuaria, parques naturales/reservas | 55 | 45 |

Horarios (Art. 2): **diurno** 7:01–21:00, **nocturno** 21:01–7:00. Los valores viven en `config.NORMA_RUIDO`; la procedencia legal completa (artículo, URL oficial, fecha de verificación, estado de vigencia) está en `config.NORMA_FUENTES["NORMA_RUIDO"]`.

> ⚠️ **No confundir con la Tabla 1** (Art. 9, estándares de emisión de una fuente puntual aislada) — la Tabla 2 aplica a mediciones de ruido ambiental continuo en una zona, que es el caso de uso de este repositorio (series de tiempo, no mediciones aisladas de una sola fuente).

---

## Normativa aplicable (Colombia)

- **Resolución 627 de 2006 (MinAmbiente, antes MAVDT):** norma técnica vigente — estándares de emisión (Tabla 1) y de ruido ambiental (Tabla 2), horarios, y excepción de fuentes naturales (Art. 17, Parágrafo Segundo).
- **Ley 2450 de 2025 ("Ley contra el Ruido"):** ordena a MinAmbiente y MinSalud expedir una reglamentación técnica actualizada dentro de 18 meses desde su sanción (marzo de 2025) — el plazo vence hacia el 2026-09-04. **Estado a 2026-09-09 (fuentes públicas no oficiales, sin verificación directa contra Diario Oficial):** esa reglamentación técnica aún no se había expedido — ver `config.NORMA_FUENTES["NORMA_RUIDO"]["estado"]` para el detalle y la fecha de la próxima reverificación recomendada.
- **Ley 769/2002:** referenciada por el Art. 17 Parágrafo 1 para la clasificación de vías (troncales/autopistas/arterias) que se evalúan contra la fila "espectáculos/vías" de la Tabla 2, nunca contra la Tabla 1.

---

## Preguntas analíticas típicas

1. ¿Cuántos días (y en qué horario) supera una zona el estándar de su sector en la Tabla 2?
2. ¿La excedencia es sistemáticamente peor en horario nocturno que diurno?
3. ¿Hay tendencia significativa de aumento del nivel de ruido en el período analizado? (Mann-Kendall, mismo criterio que el resto del repo)
4. ¿Una excedencia puntual se explica por una fuente natural (Art. 17 Parágrafo 2) o requiere intervención?

---

## Métodos estadísticos sugeridos

- **Cumplimiento normativo:** `inference/intervals.py → ruido_exceedance_report()` — L_Aeq,T por día/horario/sector, con la excepción de fuente natural como aserción explícita del analista (`natural_noise=True`), no una detección algorítmica.
- **Validación de plausibilidad física:** `io/validators.py → PHYSICAL_RANGES["ruido"]` (0–140 dB(A)).
- **Estacionariedad / tendencia:** los mismos módulos genéricos que el resto del repo (`inference/stationarity.py`, `inference/trend.py`) — sin ajuste específico de dominio todavía.
- **Predictiva:** no hay evidencia empírica propia de esta línea sobre qué modelo funciona mejor para ruido ambiental. Los modelos genéricos de `predictive/` se pueden aplicar igual que a cualquier serie de tiempo, pero sin el respaldo de un benchmark validado (a diferencia de la tabla de PM2.5 en `docs/fuentes/calidad_aire.md`).

---

## Actores institucionales

| Actor | Rol |
|---|---|
| MinAmbiente | Regulación técnica (Res. 627/2006), co-responsable de la reglamentación derivada de la Ley 2450/2025 |
| MinSalud | Co-responsable de la reglamentación derivada de la Ley 2450/2025 |
| MinTransporte / MinDefensa | Fuentes móviles y de infraestructura de transporte (Ley 2450/2025) |
| CARs / Secretarías de Ambiente | Mediciones puntuales, sanciones, mapas de ruido locales |

---

## Riesgos y sesgos en los datos

- **L_Aeq,T no es un promedio aritmético.** Promediar mediciones en dB directamente (en vez de pasar a escala lineal, promediar, y volver a dB) subestima sistemáticamente el nivel real cuando hay eventos puntuales de alto nivel.
- **Resolución temporal insuficiente.** Con mediciones muy espaciadas el L_Aeq calculado es una aproximación pobre del nivel continuo equivalente real definido por la norma.
- **Excepción de fuente natural mal aplicada.** Aplicar `natural_noise=True` sin evidencia de campo real (o no aplicarla cuando corresponde, especialmente en sector D) produce reportes de cumplimiento inválidos en cualquier dirección.
- **Ausencia de series continuas públicas.** A diferencia de calidad del aire, no hay una red de monitoreo continuo equivalente a RMCAB/SIATA — cualquier análisis real depende de mediciones puntuales de campo.

---

## Glosario mínimo

- **dB(A):** decibel con ponderación A — aproxima la sensibilidad del oído humano por frecuencia.
- **L_Aeq,T:** nivel de presión sonora continuo equivalente ponderado A sobre un intervalo T (Art. 4, Res. 627/2006). Promedio energético, no aritmético.
- **Sector (Tabla 2):** categoría de uso del suelo que determina el estándar máximo permisible aplicable.

---

## Preguntas abiertas / oportunidades

- Identificar una fuente pública real de datos de ruido ambiental (portal de datos abiertos, CAR específica) para implementar un conector automatizado.
- Verificar si la reglamentación técnica derivada de la Ley 2450/2025 ya se expidió (plazo vencido hacia 2026-09-04) y actualizar `config.NORMA_RUIDO`/`NORMA_FUENTES` si modifica la Tabla 2.
- Resto de la feature original del issue #14: mapas de ruido (componente espacial, posible integración con `spatial/`), y un notebook con datos reales una vez exista una fuente identificada.

---

## Referencias

- Resolución 627 de 2006 — Ministerio de Ambiente, Vivienda y Desarrollo Territorial (hoy MinAmbiente).
- Ley 2450 de 2025 — "Ley contra el Ruido", Congreso de la República de Colombia.
