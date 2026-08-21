# Checklist de sesión de teleoperación y captura VLA

Copiar este documento por sesión o imprimirlo. No sustituye la evaluación de
riesgos ni una función de seguridad certificada.

## Identificación

- [ ] Session ID: `____________________________`
- [ ] Fecha/hora/zona: `____________________________`
- [ ] Responsable técnico: `____________________________`
- [ ] Teleoperador: `____________________________`
- [ ] Observador con paro: `____________________________`
- [ ] Tarea/task ID: `____________________________`
- [ ] Número de episodios previsto: `____________________________`

## 1. Configuración congelada

- [ ] Robot Cruzr S2 identificado.
- [ ] Versión/build de motion y vision registrada.
- [ ] `HW_TYPE` registrado y coherente con el efector.
- [ ] `TELE_DEVICE=pico` verificado.
- [ ] `transmit=local` verificado para esta sesión LAN.
- [ ] Hash de configuraciones e instaladores registrado.
- [ ] Checkpoint/base de datos identificados.
- [ ] Cámara, resolución y topics registrados.
- [ ] No se realizarán actualizaciones durante la sesión.
- [ ] Espacio libre suficiente, incluyendo temporales y copia.

## 2. Robot y seguridad

- [ ] Efector fijado, cableado y sin daños.
- [ ] Cargador desconectado.
- [ ] Baterías dentro del margen operativo acordado.
- [ ] Paros liberados y diagnóstico sin fallo activo.
- [ ] Protección de fuerza izquierda activa.
- [ ] Protección de fuerza derecha activa.
- [ ] Objeto/carga dentro del rango autorizado.
- [ ] Zona completa y recorrido del chasis despejados.
- [ ] Teleoperador fuera del alcance del robot.
- [ ] Observador dedicado sujetando/preparado con el paro.
- [ ] Regla de aborto comunicada y comprendida.

## 3. PC de datos

- [ ] Ubuntu y variante XRoboToolkit correspondientes.
- [ ] Ethernet directa y direccionamiento verificados.
- [ ] `ubt-controller.service` activo.
- [ ] `ubt-remote-control` disponible.
- [ ] ADB detecta un único PICO autorizado.
- [ ] Reloj, zona horaria y estrategia de timestamps registrados.
- [ ] Directorio de sesión nuevo y vacío.
- [ ] Disco secundario disponible para backup.

## 4. PICO 4 Ultra Enterprise

- [ ] Modelo Enterprise confirmado.
- [ ] Batería suficiente o alimentación USB segura.
- [ ] Modo desarrollador activo.
- [ ] Suspensión y apagado de pantalla desactivados.
- [ ] Wi-Fi del PICO apagado durante la teleoperación.
- [ ] USB conectado sin tensión mecánica.
- [ ] XRoboToolkit en `Shared network (connect USB first)`.
- [ ] Servicio PC conectado; indicador `working` verde.
- [ ] Modo `Head + Controller` o modo de trackers registrado.
- [ ] Trackers calibrados en esta sesión, si aplica.
- [ ] Aplicación minimizada para evitar toques accidentales.

## 5. Prueba funcional sin captura

- [ ] Robot arrancó mediante el flujo validado.
- [ ] PICO habilita/deshabilita teleoperación con `Y`.
- [ ] `X` selecciona el modo previsto.
- [ ] Movimientos pequeños de brazos verificados.
- [ ] Cintura y elevador verificados si la tarea los necesita.
- [ ] Base verificada sólo si la tarea requiere modo móvil.
- [ ] Trigger/manos verificados sólo con hardware compatible.
- [ ] Reset `A` entendido: no resetea el elevador.
- [ ] Robot devuelto a postura inicial canónica.
- [ ] Imagen, estado, acción, fuerza y timestamps recibidos.

## 6. Piloto de captura

- [ ] Se grabó un solo episodio piloto con `B`.
- [ ] El episodio empieza antes del movimiento, sin espera larga.
- [ ] Contiene un solo intento.
- [ ] Termina después de un resultado estable y observable.
- [ ] El archivo/vídeo existe y se puede abrir.
- [ ] Estado y acción tienen la dimensión y orden esperados.
- [ ] Timestamps son monótonos.
- [ ] Task ID e instrucción son correctos.
- [ ] Resultado aceptado/rechazado anotado.

No continuar con una sesión grande si falla cualquiera de estos puntos.

## 7. Por cada episodio

- [ ] Objeto colocado en la celda planificada.
- [ ] Pose/condición real registrada.
- [ ] Robot en postura inicial canónica.
- [ ] Task ID e instrucción confirmados.
- [ ] Escena estable antes de pulsar `B`.
- [ ] Demostración fluida, sin dos intentos concatenados.
- [ ] Resultado estable antes de cerrar con `B`.
- [ ] Episode ID y resultado anotados inmediatamente.
- [ ] Fallos enviados a cuarentena, no a train.
- [ ] Retake guardado con un ID nuevo.

## 8. Cierre de sesión

- [ ] Teleoperación terminada en modo de cuerpo completo en sitio.
- [ ] No queda una captura abierta.
- [ ] Robot en postura segura y apagado normalmente.
- [ ] Número de episodios exportados coincide con la bitácora.
- [ ] Inventario y SHA-256 generados.
- [ ] Copia secundaria terminada y verificada.
- [ ] QC automático ejecutado.
- [ ] Outliers y muestra visual revisados.
- [ ] Episodios aceptados, rechazados y pendientes contabilizados.
- [ ] Incidencias y cambios de configuración documentados.
- [ ] Manifiesto firmado/cerrado.

## Resultado

- Episodios aceptados: `__________`
- Episodios rechazados: `__________`
- Episodios pendientes: `__________`
- Incidencias de seguridad: `__________`
- Dataset liberado para entrenamiento: `SÍ / NO`
- Responsable y firma: `____________________________`
