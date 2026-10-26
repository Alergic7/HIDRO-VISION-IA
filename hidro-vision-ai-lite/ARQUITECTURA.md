# HIDRO-VISION AI: arquitectura local

```mermaid
flowchart LR
    A[Campaña mensual ZIP] --> B[Validación de cuatro carpetas]
    B --> C[Historial de campañas]
    C --> D[Seleccionar dos meses]
    D --> E[Ortofotos sobre cuadrícula común]
    D --> F[Fotogramas por GPS y progresiva XML]
    E --> G[Comparación visual y preguntas]
    F --> G
    G --> H[Revisión humana: evidencia y criticidad]
    H --> I[Banco de ejemplos supervisados]
    H --> J[Informe PDF local]
    H --> K[Alerta preparada sin envío]
    I -. etapa posterior .-> L[Entrenamiento y validación del modelo]
    J --> N[Informe analítico OpenAI: 2 páginas]
    N --> M[Webhook Make y correo con PDF]
```

## Componentes implementados

- `docs/index.html`, `platform.css`: registro, historial, comparación y revisión.
- `comparison.js`: resultados geoespaciales, notas por progresiva y videos sincronizados.
- `zoom.js`: zoom, desplazamiento, ajuste de cobertura y pantalla completa.
- `platform.js`: registro de campañas, hallazgos, exportación, informes y preparación de alertas.
- `server.py`: API local y entrega de archivos con soporte de rangos para video.
- `processor.py`: validación de ZIP, LandXML, SRT y ortofotos; extracción y comparación.
- `platform_store.py`: persistencia SQLite, auditoría de revisiones y PDF.

## Contrato de los datos

Cada ZIP contiene `VIDEO`, `ORTOFOTO`, `PLANO_OTROS` y `XML`. Cada campaña tiene identificador, mes y año. Los planos sirven como referencias. Las progresivas provienen del alineamiento XML y los fotogramas se seleccionan por la posición del dron en el SRT.

Cada hallazgo conserva comparación, progresiva, categoría, evidencia, justificación, revisor, verificación de campo y fechas. Cada corrección produce una revisión adicional. El conjunto exportado incluye etiquetas e imágenes referenciadas, sin convertirlas en predicciones.

## Estado de la IA y las alertas

El sistema está en recopilación de ejemplos supervisados. No existe un detector entrenado, una precisión medida ni un entrenamiento automático con cada carga. El siguiente ciclo requiere revisar etiquetas, separar campañas entre entrenamiento y evaluación, entrenar, medir errores y aprobar una versión antes de usar sus predicciones.

El PDF local de plantilla continúa disponible. `ai_reports.py` agrega Responses API, salida estructurada y PDF de dos páginas con evidencia y contexto SENAMHI archivado. `configure_integrations.py` guarda las credenciales fuera de la carpeta web. El webhook de Make recibe el PDF en base64 para alexandra.colan.7@gmail.com, con un solo intento por informe. La recepción del webhook y la confirmación de envío se registran por separado. Requiere configurar la clave OpenAI y el escenario Make; ver INTEGRACIONES.md. Las alertas individuales del flujo anterior siguen preparadas localmente.

## Verificación

`python -m unittest test_comparison test_platform -v` verifica comparación geográfica, nodata de cuatro bandas, lectura de campañas, auditoría de hallazgos, exportación, PDF y alertas preparadas. El visor se verificó con las campañas reales de enero y julio de 2026.
