# Brief de Diagnóstico de Datos — Para líderes de área

> **¿Para qué sirve este documento?**  
> Te ayuda a articular, junto con tu IA de confianza, qué datos tienes, qué necesitas saber con ellos y qué tipo de análisis tendría más valor para tu área. No se trata únicamente de modelos predictivos — puede ser tableros, seguimiento de metas, reportes automáticos o alertas tempranas.
>
> **¿Cómo usarlo?**  
> Comparte este archivo con tu IA (ChatGPT, Copilot, Claude, Gemini, etc.) y dile:
> *"Ayúdame a responder estas preguntas de forma clara y completa. Hazme las preguntas una por una, espera mi respuesta y luego construye el documento de salida en formato Markdown."*
>
> Al final, envíanos:  
> 1. El archivo `.md` de respuestas que generó tu IA (ver `intake_output_template.md`)  
> 2. Una muestra de tus datos (ver Sección D)  
> 3. Cualquier reporte o tablero que hoy produces manualmente

---

## Instrucciones para tu IA

Cuando compartas este documento con tu IA, puedes darle la siguiente instrucción inicial:

> *"Voy a responderte una serie de preguntas sobre mi área de trabajo y los datos que manejo. Tu rol es hacerme las preguntas de forma conversacional, capturar mis respuestas con detalle y al final producir un documento Markdown estructurado según el template que te indicaré. No asumas nada que yo no te haya dicho. Si algo no queda claro, pregúntame."*

---

## Sección A — Tu rol y contexto institucional

> Estas preguntas ayudan a entender desde dónde partes y qué decisiones tomas.

1. **¿Cuál es tu cargo y a qué área o dependencia perteneces?**

2. **¿Cuáles son los 3 objetivos principales de tu área este año?**  
   *(Por ejemplo: reducir el tiempo de respuesta a PQRS, mejorar el índice de calidad del agua en cuencas priorizadas, aumentar la superficie de áreas protegidas bajo conservación efectiva.)*

3. **¿Qué decisiones importantes tomas regularmente que hoy tomas "a ojo" o con información incompleta?**  
   *(Por ejemplo: dónde priorizar una visita de campo, si una cuenca está en riesgo, cuándo alertar a una CAR.)*

4. **¿Qué reportes o informes debes entregar periódicamente y a quién?**  
   *(Frecuencia, destinatario, si son manuales o automatizados.)*

---

## Sección B — Tus datos

> Queremos entender qué información ya existe antes de proponer cualquier análisis.

5. **¿Qué datos recolecta o recibe tu área regularmente?**  
   Para cada fuente de datos, describe:
   - ¿Qué mide o registra? (calidad del agua, precipitación, áreas deforestadas, predios, etc.)
   - ¿Con qué frecuencia llega? (diaria, mensual, anual, cuando ocurre un evento)
   - ¿En qué formato está? (Excel, CSV, base de datos, papel, sistema institucional como SIRH, IDEAM, SIGAM)
   - ¿Cuántos años de histórico tienes?
   - ¿Cuántas filas/registros aproximados tiene?

6. **¿Quién gestiona esos datos hoy? ¿Hay una persona o sistema responsable?**

7. **¿Qué tan confiables consideras esos datos? ¿Tienen muchos vacíos, errores o inconsistencias conocidas?**

8. **¿Hay datos que sabes que existen pero que hoy no tienes acceso fácil a ellos?**  
   *(Por ejemplo: datos del IDEAM, registros de otras dependencias, información satelital.)*

---

## Sección C — Tus necesidades analíticas

> No todo tiene que ser un modelo predictivo. Aquí exploramos qué tipo de análisis tendría más impacto en tu trabajo.

9. **¿Qué preguntas concretas quisieras poder responder con tus datos?**  
   Ejemplo de preguntas bien formuladas:
   - *"¿En qué municipios la calidad del agua empeoró más en los últimos 5 años?"*
   - *"¿Cuántos días al año supero el límite normativo de PM2.5 en mis estaciones?"*
   - *"¿Qué predios bajo conservación muestran pérdida de cobertura vegetal?"*
   - *"¿Voy a cumplir la meta de hectáreas conservadas al ritmo actual?"*

10. **¿Qué tipo de producto te sería más útil?** *(Puedes marcar más de uno)*
    - [ ] Tablero de seguimiento (dashboard) que actualice automáticamente
    - [ ] Reporte periódico (mensual/trimestral) con indicadores clave
    - [ ] Alerta automática cuando un indicador supere un umbral crítico
    - [ ] Mapa o análisis espacial de una variable
    - [ ] Análisis de tendencia (¿estamos mejorando o empeorando?)
    - [ ] Proyección o pronóstico (¿qué puede pasar si seguimos así?)
    - [ ] Análisis de cumplimiento normativo (¿cuánto tiempo estamos fuera de norma?)
    - [ ] Otro: ___________________

11. **¿Con qué herramientas trabaja hoy tu equipo?**  
    *(Excel, Power BI, ArcGIS, QGIS, Python, R, ninguna especializada, etc.)*

12. **¿Qué tan técnico es tu equipo? ¿Tienen personas que puedan interpretar estadísticas o prefieren visualizaciones simples?**

---

## Sección D — Entregables y plazos

> Para poder planear el trabajo contigo, necesitamos saber hacia dónde va esto.

13. **¿Hay algún plazo importante en el que necesites resultados?**  
    *(Auditoría, rendición de cuentas, entrega a MADS/CAR, fin de vigencia, etc.)*

14. **¿Cómo medirías el éxito de este trabajo?**  
    *(Por ejemplo: "poder mostrar en una reunión de directivos la tendencia de calidad del aire en los últimos 3 años sin necesitar a un ingeniero para prepararlo".)*

15. **¿Hay restricciones de confidencialidad sobre los datos?**  
    *(Datos sensibles, reserva estadística, información que no puede salir de la entidad, etc.)*

---

## Sección E — Contexto organizacional

16. **¿Con qué otras áreas o entidades deberías articularte para este análisis?**  
    *(Por ejemplo: Sistemas, Planeación, la CAR de tu zona, IDEAM, IGAC.)*

17. **¿Ha habido intentos anteriores de hacer algo similar? ¿Qué pasó?**  
    *(Proyectos de datos que no llegaron a ningún lado, consultorías que dejaron entregables sin uso, etc.)*

18. **¿Tienes un equipo o persona que pueda ser el punto de contacto técnico del lado de tu área?**

---

## ¿Qué nos envías al final?

Una vez que hayas respondido estas preguntas con tu IA, envíanos:

### 1. El documento de respuestas (`.md`)
Tu IA debe generar un archivo Markdown estructurado con todas tus respuestas. Puedes pedirle:  
*"Genera ahora el documento de salida en formato Markdown siguiendo el template `intake_output_template.md`."*

### 2. Una muestra de tus datos
- Si son Excel/CSV: envía las primeras 100-200 filas con los encabezados reales (puedes anonimizar si es necesario)
- Si están en un sistema institucional: una captura de pantalla o exportación de prueba
- Si son muchos archivos: el más representativo del tipo de dato que más usas

### 3. Un ejemplo de reporte actual
Si hoy produces un informe o tablero (aunque sea en Excel), compártelo. Nos ayuda a entender qué ya existe y qué podemos automatizar.

---

> **Nota:** No se requiere que seas experto en datos. Entre más detallado y honesto seas en tus respuestas, mejor podremos diseñar un plan de trabajo que se ajuste a tu realidad y produzca resultados que realmente uses.
