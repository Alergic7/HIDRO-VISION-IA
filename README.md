# HIDRO-VISION AI

Comparación local de dos campañas de inspección de diques: ortofotos, videos sincronizados, progresivas y hallazgos supervisados.

## Ejecutar

Descarga **Code → Download ZIP**, descomprime y entra en **hidro-vision-ai-lite**. Instala Python 3.12 de 64 bits, ejecuta `INSTALAR_WINDOWS.cmd` una vez y luego `INICIAR_HIDRO_VISION.cmd`. Abre http://127.0.0.1:8765/. No necesitas ChatGPT ni Codex para la comparación local.

## Informe IA y correo

La integración genera un PDF analítico de dos páginas mediante la API de OpenAI, con imágenes seleccionadas, registros de precipitación disponibles, posibles anomalías y acciones de verificación. Make puede enviar el PDF a alexandra.colan.7@gmail.com.

Requiere clave API de OpenAI, modelo compatible con imágenes y un escenario de Make autorizado. Ejecuta `CONFIGURAR_IA_MAKE.cmd` dentro de la carpeta del aplicativo y sigue la [guía de configuración](hidro-vision-ai-lite/INTEGRACIONES.md). Las credenciales son locales y no se publican. Sin ellas no hay generación IA ni envío real.

La IA de redacción no sustituye un detector entrenado de anomalías ni una inspección técnica. Los registros SENAMHI incluidos son consultas archivadas, no datos en vivo.

[Manual del aplicativo](hidro-vision-ai-lite/README.md) · [Arquitectura](hidro-vision-ai-lite/ARQUITECTURA.md)

GitHub distribuye el código; GitHub Pages no ejecuta el servidor Python. Los ZIP de campañas y bases de datos permanecen en cada equipo.
