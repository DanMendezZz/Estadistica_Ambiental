# ADR-020: `NORMA_FUENTES`, procedencia legal verificada de los umbrales normativos

**Fecha:** 2026-07-25
**Estado:** Aceptado

## Contexto

ADR-005 centralizó las normas colombianas en `config.py`, pero cada umbral solo
citaba su fuente como comentario `#` (ej. "Resolución 2254 de 2017"), sin
artículo, sin URL oficial y sin fecha de verificación. Al auditar los 17
cuadernos de NotebookLM que alimentan las 16 líneas temáticas (ver la
auditoría normativa fechada 2026-07-25), se aprovechó para verificar el texto
oficial completo de las 4 normas base contra los valores hardcodeados.

La verificación (agente especializado en normativa ambiental colombiana,
lectura artículo por artículo del texto oficial, no resumen de terceros)
encontró que el problema no era solo falta de metadatos: **6 valores
numéricos no coincidían con la norma vigente** (`pm10_annual`, `no2_annual`,
`co_8h`, `nitratos_max`, `dqo_max`, y los breakpoints de CO en
`ICA_BREAKPOINTS`), la cita del ICA apuntaba a un anexo inexistente, y 3
campos (`od_min` y `dbo5_max` en `NORMA_AGUA_POTABLE`, más `od_min` en
`NORMA_VERTIMIENTOS`) estaban atribuidos a una resolución que no los
contiene. Una revisión de código posterior (`code-reviewer`) encontró además
que `ICA_BREAKPOINTS["co"]` era, número por número, la tabla AQI de CO de la
EPA en **ppm** mal etiquetada como mg/m³; nunca fue la tabla colombiana.

## Decisión

1. **Corregir los valores con discrepancia verificada** en `config.py`:
   - `NORMA_CO["pm10_annual"]`: 40.0 → **50.0** µg/m³ (Res. 2254/2017 Art. 2,
     Tabla 1 vigente; 30.0 es la meta 2030, aún no exigible).
   - `NORMA_CO["no2_annual"]`: 40.0 → **60.0** µg/m³ (mismo motivo; 40.0 es la
     meta 2030).
   - `NORMA_CO["co_8h"]`: 10.0 → **5.0** mg/m³ (Tabla 1: 5.000 µg/m³).
   - ICA: la cita "Anexo 3" era incorrecta; la Res. 2254/2017 no tiene ese
     anexo. Corregido a **Arts. 19 y 20 (Tablas 5 y 6)**.
   - `ICA_BREAKPOINTS["co"]`: `[4.4, 9.4, 12.4, 15.4, 30.4]` (tabla EPA en ppm)
     → **`[5.094, 10.189, 14.254, 17.688, 34.867]`** mg/m³ (Res. 2254/2017
     Art. 20, Tabla 6). Extraídos de una tabla incrustada como imagen en el
     PDF oficial (OCR); el último dígito tiene incertidumbre residual,
     documentada en el comentario del código.
   - `NORMA_AGUA_POTABLE["nitratos_max"]`: 50.0 → **10.0** mg/L NO₃⁻ (Res.
     2115/2007 Art. 6, Cuadro 3). El 50 no tiene respaldo en la norma
     colombiana verificada.
   - `NORMA_VERTIMIENTOS["dqo_max"]`: 200.0 → **180.0** mg/L (Res. 631/2015
     Art. 8: el valor de 200.0 pertenece a la columna de "soluciones
     individuales unifamiliares/bifamiliares", que no define DBO5; el valor
     coherente con DBO5=90/SST=90 (sector prestadores de alcantarillado) es
     180.0).
2. **Documentar honestamente los campos sin respaldo legal vigente**, en vez
   de eliminarlos o dejarlos con una cita falsa: `NORMA_AGUA_POTABLE.od_min`,
   `NORMA_AGUA_POTABLE.dbo5_max` y `NORMA_VERTIMIENTOS.od_min` no tienen
   fuente vigente. Existieron en el Decreto 1594/1984 Art. 45 (uso
   "preservación de flora y fauna", no "consumo humano" ni "vertimiento
   genérico"), derogado por el Art. 79 del Decreto 3930/2010 (hoy Decreto
   1076/2015) sin reemplazo por un valor fijo nacional; hoy el criterio se
   fija caso por caso vía PORH. Se mantienen como **valores de referencia
   técnica** (útiles para clasificación interna), pero `NORMA_FUENTES` los
   marca explícitamente con `estado: derogado_sin_reemplazo_fijo`.
3. **Corregir la atribución de `AMENAZA_PRECIPITACION`**: la Ley 1523/2012 y
   el Decreto 1807/2014 no fijan umbrales numéricos de precipitación (son
   marco institucional y metodológico, no una tabla de valores). Se
   documenta como convención metodológica propia, sin incluirla en
   `NORMA_FUENTES` como si fuera ley.
4. **Corregir `inference/intervals.py`**: el mapeo `_NORMA_MAP` etiquetaba
   `dbo`/`dbo5` (rama agua potable) como `"Res. 2115/2007, agua potable"`,
   la misma atribución falsa que `od`. Corregido a la misma referencia
   histórica que `od_min`.
5. **Nuevo diccionario `NORMA_FUENTES`** en `config.py`: asocia cada
   constante normativa con `codigo`, `articulo`, `url_oficial`,
   `fecha_verificacion` y un campo `estado` (`vigente` /
   `guia_no_vinculante` / `derogado_sin_reemplazo_fijo`). Incluye también
   `NORMA_OMS` (guía internacional, no norma colombiana). Es el punto de
   verdad que consumen los tests nuevos.
6. **`tests/test_config_normas.py`** (nuevo): descubre por introspección las
   constantes `NORMA_*`/`ICA_BREAKPOINTS` de `config.py` y falla si falta su
   entrada en `NORMA_FUENTES`, si un campo está vacío, si la key no
   corresponde a una constante real, o si `estado` tiene un valor no
   reconocido. El chequeo de vigencia (`fecha_verificacion` > 12 meses) vive
   en una clase separada marcada `@pytest.mark.normativa_vigencia` y
   **excluida de la suite por defecto** (`pyproject.toml` `addopts`) para no
   tumbar el CI de cada PR cuando el calendario avanza; solo corre en el
   job programado.
7. **Job nuevo en `.github/workflows/scheduled.yml`**: corre
   `pytest tests/test_config_normas.py -m ""` semanalmente (mismo cron que
   `security-audit`) y abre un Issue si falla, con `permissions: issues:
   write` explícito y deduplicación (no crea un Issue nuevo si ya hay uno
   abierto con la misma etiqueta); el mismo fix se aplicó a `security-audit`,
   que tenía el mismo defecto de permisos.

## Consecuencias

- `compliance_report()` y `exceedance_report()` **cambian de comportamiento**
  para PM10 anual, NO2 anual, CO 8h y nitratos: reportarán excedencias
  distintas a las que reportaban antes de esta corrección (más estrictas
  para CO y nitratos, donde el valor anterior era mucho más permisivo que la
  ley; ligeramente distintas para PM10/NO2 anual). La clasificación ICA de
  CO también cambia (antes usaba cortes ~1000x más bajos por el error de
  unidades). Cualquier reporte HTML generado antes de este commit con esas
  variables queda desactualizado.
- El proceso de verificación queda documentado y repetible: la auditoría
  normativa (corrida NotebookLM + revisión de texto oficial) es lo que
  refresca `fecha_verificacion` en el futuro.
- Los valores de referencia técnica sin respaldo legal (`od_min`, `dbo5_max`
  en agua potable; `od_min` en vertimientos) siguen disponibles para quien
  los use, pero ya no se presentan como ley; evita que un reporte de
  cumplimiento cite una resolución que en realidad no exige ese valor.

## Referencias

- Auditoría normativa NotebookLM, 2026-07-25 (vault:
  `03_Resources/Ambiental/Normativa/_Auditorias/2026-07-25 Auditoria normativa NotebookLM.md`).
- `src/estadistica_ambiental/config.py`: `NORMA_CO`, `ICA_BREAKPOINTS`,
  `NORMA_AGUA_POTABLE`, `NORMA_VERTIMIENTOS`, `NORMA_FUENTES`,
  `AMENAZA_PRECIPITACION`.
- `tests/test_config_normas.py`.
- `.github/workflows/scheduled.yml`, job `normativa-audit`.
