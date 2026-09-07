# HOME de arranque: temporización y avisos de rango

## Resultado offline, 07-09-2026

Se reconstruyeron las **órdenes registradas**, no la trayectoria articular real,
del primer HOME de cada log del 04-09. Son los dos arranques de 13:58 y 14:20
de Madrid ya identificados en la auditoría. No se accedió al robot.

| Grupo | Desfase desde primera orden, primer HOME | Segundo HOME | Objetivo / duración |
|---|---:|---:|---|
| Elevador | 0 s | 0 s | 3 ceros / 6 s |
| Brazo izquierdo | 0,199405 s | 0,200993 s | 7 ceros / 6 s |
| Brazo derecho | 0,401412 s | 0,402475 s | 7 ceros / 6 s |
| Cintura | 0,603841 s | 0,604015 s | 1 cero / 6 s |
| Cabeza | 0,805274 s | 0,806148 s | 2 ceros / 6 s |

**VERIFICADO:** concurrencia no equivale a comienzo sincronizado de las
órdenes. Las marcas `Now move` no miden cuándo empezó físicamente cada eje.
No se ha demostrado que estos desfases causaran el contacto; sí son una
condición que una reconstrucción del movimiento no debe omitir.

## Avisos anteriores al fallo de fuerza

Primer HOME: el registro muestra consignas fuera de rango en tres grupos:

| Índice literal del log (no nombre ROS asignado) | Primera consigna | Límite excedido | Exceso máximo registrado |
|---|---:|---:|---:|
| left_arm:2 | 0,103160 rad | máximo 0,0987266 | 0,0044334 rad |
| right_arm:2 | 0,121184 rad | máximo 0,0987266 | 0,0224574 rad |
| head:2 | −0,698728 rad | mínimo −0,688727 | 0,0100010 rad |

Son consignas avisadas, no prueba de posición medida, de límites desactivados
ni de cómo el controlador trató cada aviso. No ampliar límites para suprimirlos.
El segundo HOME registra aviso head:2 con exceso máximo 0,008179 rad y termina
en SUCCESS. No registra alarma FT en esa ventana; eso no demuestra ausencia
de rayado ni autoriza a reutilizar el retorno.

En el primer HOME, la primera alarma FT izquierda aparece a las
13:58:04.108008, unos **1,672 s tras la orden de brazo izquierdo**. El fallo
del árbol se registra a las 13:58:04.422351. Ese intervalo no es una medida
de tiempo/distancia de parada ni localiza el primer contacto. No inferir
velocidades o distancias cartesianas sin telemetría.

## Consecuencias para la recalificación

1. Verificar postura inicial completa y que está dentro de límites antes de
   diseñar el retorno; no sólo comprobar que el objetivo HOME está en rango.
2. Registrar geometría de ambos clamps respecto a cada muñeca, incluyendo
   patitas/soporte/holguras. La corrección del montaje no valida la ruta.
3. Comprobar el volumen recorrido con desfases entre grupos y su incertidumbre,
   no sólo extremos ni una interpolación común perfectamente sincronizada.
4. Si se diseña retirada por fases, verificar cada trayectoria y estado final
   antes de pasar a la siguiente. No asignar ahora ángulos de retirada a ciegas.
5. Cubrir HOME interno de arranque: arreglar sólo el wrapper del PC no lo
   intercepta. No ensayar reinicio para comprobarlo.

**Pendiente explícito:** no se ha reconstruido aquí la serie medida de las
20 articulaciones, la ley real de interpolación, ni la trayectoria cartesiana
de las abrazaderas. El resultado no es una nueva validación de colisiones.

## Reproducción y evidencia

Herramienta `scripts/audit_home_group_timing.py`: lectura local, SHA-256 de cada
log, números de línea, delimitación del primer HOME hasta resultado del árbol,
salida exclusiva sin sobrescritura. Pruebas en `scripts/test_home_group_timing.py`.

Evidencia:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_home_group_timing.json`.
Fuentes de la colección sellada `20260907T053541Z_CONTACT-AUDIT`, subdirectorio
`motion/etc/walker/log/motion/`:

- `robot_app.20260904-194905.65.log`: órdenes líneas 634, 639, 745, 954, 1158;
  primer FT 1976; fallo 2099.
- `robot_app.20260904-201849.65.log`: órdenes líneas 182, 187, 192, 197, 201;
  éxito 423.

Conversión específica de estos logs: hora robot menos seis horas = Madrid
(UTC+02). No es una regla universal para otros equipos o fechas.

No hay cambios persistentes en robot, ni comandos de movimiento. No se
modificó ninguna tarea HOME ni el SDK. Informes y logs previos conservados.
