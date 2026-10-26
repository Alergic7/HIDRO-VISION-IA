# Informe de dos páginas con OpenAI y envío por Make

## Activar en este equipo

1. Instala la aplicación con `INSTALAR_WINDOWS.cmd`.
2. Crea una clave en https://platform.openai.com/api-keys y habilita facturación de API. La suscripción de ChatGPT no sustituye este servicio. Selecciona un modelo disponible en tu proyecto que admita imágenes y salidas JSON estructuradas; el configurador propone `gpt-4o`.
3. Ejecuta `CONFIGURAR_IA_MAKE.cmd`. Introduce la clave y, cuando lo tengas, el webhook HTTPS de Make. Los campos secretos no se muestran mientras escribes. Enter conserva el valor existente. Para retirar una credencial, elimina su valor del archivo local de configuración.
4. Los valores se guardan en `settings.local.json`, fuera de la carpeta web y excluidos de Git. También se admiten las variables de entorno `OPENAI_API_KEY`, `OPENAI_MODEL`, `MAKE_WEBHOOK_URL` y `MAKE_API_KEY` (tienen prioridad). No publiques ni compartas `settings.local.json` ni `local_data`.
5. Inicia/reinicia el servidor y pulsa **Actualizar conexión**. El estado indica si hay configuración; la primera generación comprueba la conexión real.
6. Selecciona dos campañas. En Informe técnico pulsa **Generar informe IA de 2 páginas**. Si Make no está listo, desmarca **Enviar el PDF por Make al terminar**. Después puedes enviar un PDF ya generado sin pagar otra generación.

Sin clave o webhook la aplicación muestra qué falta; nunca simula una respuesta de OpenAI ni un correo enviado. El informe local de plantilla sigue disponible sin conexión. No se efectuaron llamadas reales ni envíos en las pruebas de desarrollo.

## Información enviada a OpenAI

Se utiliza Responses API con `store: false`: nombres de campañas, tramo, hasta 20 hallazgos (priorizando urgentes), notas de revisión, contexto SENAMHI y hasta seis imágenes reducidas de tres progresivas. Los hallazgos pueden incluir el nombre de su revisor. No se envían los ZIP ni videos completos, ni las claves a Make. `store: false` no sustituye las políticas de retención del proveedor.

El informe distingue evidencia, hipótesis y acciones de verificación. Los campos tienen límites de extensión; si el modelo excede el espacio o la solicitud falla, no se publica un PDF parcial. El PDF tiene dos páginas y un anexo JSON local conserva los datos utilizados, el identificador de respuesta y el modelo. La muestra no representa automáticamente todo el tramo. No es un detector entrenado ni una certificación estructural.

La precipitación procede de las tablas archivadas ya incluidas: solo Cañete, enero/julio de 2026 cuando corresponda a la estación más cercana. Para otras estaciones/meses se informa ausencia de datos, sin rellenar con cero. No se consulta SENAMHI en vivo. La lluvia local no basta para atribuir variaciones de caudal ni declarar una avenida.

## Configurar el escenario de Make

1. Crea un escenario: **Webhooks > Custom webhook**. Copia su URL en el configurador local. Opcionalmente agrega autenticación API key al webhook e introduce esa clave en `MAKE_API_KEY` (se envía en `x-make-apikey`).
2. Importa la estructura de ejemplo de `make-payload-example.json` o define los campos de ese JSON en el webhook. Es una muestra de estructura con PDF vacío: no enviarla por correo. Para detectar campos con datos reales, pon Make en **Run once** y usa **Enviar PDF por Make** sobre un informe real cuando el escenario esté preparado.
3. Antes del módulo de correo, añade deduplicación persistente por `event_id` con **Data store** y procesamiento secuencial. Si ese evento ya figura como enviado, omite el correo. Conserva su `message_id`. Para estados de intento en curso o incierto, revisa el historial antes de repetir. No conectes una ruta de errores que vuelva a enviar correos a ciegas.
4. Añade **Gmail > Send an email** y conecta la cuenta que enviará el correo. Esa cuenta remitente se autoriza en Make; no tiene que ser la cuenta destinataria.
5. Configura **To** como `alexandra.colan.7@gmail.com`; **Subject** desde `subject`; cuerpo de texto desde `body`. Para adjuntos: nombre desde `attachment.filename` y datos con la función `toBinary(attachment.base64; base64)` (selecciona el campo `base64` del webhook y el literal `base64` como codificación).
6. Guarda el `event_id` y el ID del mensaje devuelto por Gmail tras el envío exitoso.
7. Al final, agrega **Webhooks > Webhook response**, código 200 y Content-Type `application/json`. Responde `{"status":"sent","event_id":"<event_id recibido>","message_id":"<ID devuelto por Gmail>"}` mapeando los campos reales. No uses `sent` en una ruta que solo haya recibido el webhook.
8. Activa el escenario. Al marcar el envío en HIDRO-VISION, el PDF se transmite en base64 a Make y se adjunta al correo: no necesita que Make acceda a localhost.

El destinatario está fijado en el servidor. El webhook recibe únicamente el PDF, destinatario, asunto y cuerpo, no el anexo JSON ni la clave OpenAI. El tamaño total debe ser menor o igual a 5 MiB.

## Estados y reintentos

- `accepted_by_make`: respuesta HTTP exitosa; Make lo recibió, el correo no está confirmado.
- `sent_confirmed`: respuesta estructurada con el mismo evento y un ID de correo; Make confirmó el envío, no la recepción en bandeja.
- `unknown`: tiempo de espera, error de red/servidor o interrupción. Puede haberse enviado; revisa Make.
- `rejected`: error HTTP 4xx. Revisa configuración e historial.
- `sending`: intento registrado antes de la llamada. Si el proceso se cerró, revisa Make.

Cada PDF admite un solo intento desde la aplicación, incluso con doble clic o reinicio. No hay reenvío automático de estados inciertos. Una nueva generación produce otro PDF y puede enviar otro correo: evita repetirla para resolver un fallo de entrega. En Make comprueba el evento y reanuda manualmente solo si no hubo envío.

## Fuentes de integración

- https://developers.openai.com/api/docs/guides/structured-outputs
- https://apps.make.com/gateway
- https://apps.make.com/gmail-modules

## Pruebas sin servicios externos

`python -m unittest test_comparison test_platform test_ai_reports -v`

Las pruebas usan respuestas simuladas para verificar PDF de dos páginas, errores, secreto de configuración, destinatario, adjunto e idempotencia. Para validar el flujo real se necesitan tus credenciales y el escenario activo en Make.
