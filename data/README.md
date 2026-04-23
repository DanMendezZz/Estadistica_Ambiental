# data/

Las subcarpetas `raw/`, `processed/` y `output/` están en `.gitignore` y no se suben al repositorio.

- `raw/` — datos originales sin modificar (CSV, Excel, NetCDF, SHP, etc.)
- `processed/` — datos limpios e imputados listos para modelar
- `output/` — resultados: predicciones, reportes HTML/PDF, gráficos

Para datasets de ejemplo o datos públicos reproducibles, documentar la fuente y el comando de descarga en `docs/fuentes/<linea>.md`.

## Política de datos en el repositorio

- El directorio `data/` está en `.gitignore`: los archivos de datos reales (CSV, Parquet, XLSX, NetCDF, SHP y similares) **no se suben al repositorio**.
- Solo se commitean ejemplos muy pequeños (< 1 MB) o archivos de configuración relacionados con datos.
- Para datos de producción, usar rutas externas configuradas en `CLAUDE.local.md` o un data lake (S3, GCS, ADLS, etc.).
