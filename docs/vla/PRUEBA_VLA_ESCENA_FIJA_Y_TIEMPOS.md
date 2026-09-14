# Prueba VLA en escena fija: tiempos y secuencia física

**2026-09-14 — Ensayo mínimo VLA preparado, aún no ejecutado.**
Replay parcial del primer punto del chunk2 desde ENTRY410: ambos brazos,
25 % de la transición, máximo 1,396°, 4 s; no agarre ni chunk completo.
El punto completo mantiene un par mano derecha/mesa sin resolver; el prefijo
conserva 1018 pares certificados y los 54 avisos internos históricos, sin nuevos
fallos geométricos. Trece tests y --check pasan. Ejecutor SDK con lectura de
salud/paros/cargador/postura, seguimiento y llegada; sin reintentos ni HOME.
No requiere instalar XML, recargar o reiniciar. Scripts del operador intactos.
[Comando, límites, reproducción y estado pendiente](ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**Continuación vigente — 2026-09-14: ENTRY medido y shadow task 0 completado.**
98 muestras inmóviles, error final máximo 0,1593° respecto a ENTRY410. Seis
propuestas y seis aceptaciones por el perfil shadow existente de 14 ejes de
brazos; primer cambio máximo 6,1643° (umbral shadow 0,35 rad), sin envío físico.
Inferencia caliente mediana 0,436 s; arranque exterior 79,394 s. Caja completa
visible en la cámara. Sesión cerrada: ambos contenedores VLA exited y cero
publicadores de movimiento. No se cambiaron tareas ni umbrales. Siguiente:
adaptar el ejecutor físico a ENTRY410 y resolver entrada al primer punto;
no repetir HOME/READY/ENTRY ni confundir aceptación shadow con agarre probado.
[Ensayo, tiempos, reproducción y evidencia](ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: READY→ENTRY410 probado físicamente,
5/5 etapas con éxito según el operador y sus cinco resultados Motion SUCCEED.**
HOME→READY nuevo y READY→ENTRY410 quedan completados para los ensayos comunicados.
Se conserva `force_entry.sh` del operador. Siguiente: lectura fresca y propuestas
VLA task 0 en shadow desde ENTRY; el agarre VLA aún no se ha probado.
[Registro del ensayo, Goal ID y evidencia](ENSAYO_READY_ENTRY410_20260914.md).


2026-09-14, Europe/Madrid. VLA-01. El ensayo realizado es shadow, sin movimiento.
La mesa/caja/base se mantendrán en la misma colocación según el operador.
Esto permite reutilizar una revisión cuyo dominio siga siendo válido, pero
no elimina la lectura fresca de postura, imagen y estado antes de cada ensayo.

## Resultado medido

Una sesión task0 de30,029s produjo seis propuestas. Primera llamada separada
de las cinco siguientes; mediana caliente descriptiva, no garantía de plazo:

| Medida interna de tiempo de pared | Primera | Mediana siguientes | Máximo siguientes |
|---|---:|---:|---:|
| Inicialización nodo/modelo |27,467s|—|—|
| Sincronización de entrada disponible |0,243ms|0,243ms|0,257ms|
| Guardado de evidencia RGB/estado |62,508ms|43,779ms|51,467ms|
| policy.get_action |1,624s|0,397s|0,424s|
| model.inference |1,633s|0,401s|0,428s|
| Iteración de inferencia completa |1,697s|0,444s|0,474s|

Las medidas están anidadas: NO sumarlas. get_action mide la llamada completa,
no sólo kernels GPU. Sincronización mide la selección de buffers disponibles,
no edad de adquisición ni espera hasta el primer sensor. No se ha medido aquí
el tiempo interno del validador, ni la ejecución física o la distancia de parada.

Fuente instalada enVision: gr00t_inference.py SHA256
bb3b14b6917becc2c474933672f71978180062c8b335543c5cc014bcccdbf1c1.
DEFAULT_HZ=0.2, periodo5s. Publicaciones posteriores observadas aproximadamente
cada5s. CHUNK_NUM=10 y CHUNK_POINT_DT=0.08: último punto a0.72s. Este horizonte
no debe confundirse con los5s entre nuevas propuestas. No basta aumentar Hz
para habilitar ejecución: caducidad, continuidad y consumo de chunks necesitan
su contrato propio. No se modificó la frecuencia ni la velocidad física.

Seis REJECT, todos first_point_delta_violations:8. Es un ensayo de rendimiento
en la postura actual, no validación de calidad desde ENTRY. Lectura nominal
por nombre: cuerpo/brazos cerca de cero, pitch cabeza−0,428268rad, velocidades0.
No HOME20D completo ni ENTRY. No se enviaron objetivos de movimiento.

## Repetir la medición

Con VLA detenido y sin otros publicadores de mando:

```bash
python3 scripts/vla/benchmark_vla_shadow.py \
 --task-id 0 --duration 30 \
 --output-dir ../Humanoide-vla-evidence/benchmark-nuevo
```

El directorio debe ser nuevo. Exporta los logs anteriores antes de borrarlos
mediante el arranque existente. Carga el modelo una vez, espera disponibilidad,
solicita una sesión con varios chunks, detiene y exporta. report.json separa
inicialización/primera/siguientes; host-times.json separa costes del wrapper.
No relanzarlo para cada chunk, porque repetiría carga y comprobaciones.

Esta primera ejecución del orquestador se interrumpió antes del trigger:
no existe report.json de finalización en benchmark/. Se descubrieron estados
vivos; el validador había agotado su ventana sin chunks, modelo seguía cargado.
Se reanudó sólo shadow y se solicitó una tarea30s, sin recargar el modelo.
Resultados efectivos en results/ y timing-summary.json, separados del intento
incompleto. Se añadieron manejo SIGINT/SIGTERM e intent/host-times persistentes;
SIGKILL/corte puede impedir limpieza: comprobar --status antes de reanudar.
No se ha ensayado de extremo a extremo la versión final del orquestador.

## Secuencia física para esta escena

Esta es la secuencia prevista; NO está autorizada por el resultado de tiempos.
El acceso a ENTRY y la habilitación del ejecutor siguen pendientes.

1. Conservar la escena y comprobar postura fresca, caja apoyada, abrazaderas
   vacías, zona libre, cargador, ruedas, paros, modo exclusivo y operador.
2. Ejecutar el acceso determinista revisado a READY y ENTRY410 por etapas.
   Verificar final de cada etapa. La cabeza baja actual debe formar parte del
   inicio medido; no ordenar HOME genérico para corregirla ni usar etapa1 desdeHOME.
3. Con ENTRY medida, cargar/calentar VLA una vez y obtener cinco chunks shadow
   frescos aceptables de esta misma escena. No ampliar tolerancias para ocultar
   el rechazo. Los seis chunks desde postura actual no sustituyen esta prueba.
4. Con contrato físico habilitado, ejecutar un único tramo limitado, registrar
   estado solicitado/medido, antigüedad de imagen y respuesta de detención.
   Observar suavidad, separación y extremo antes de continuar. No ejecutar una
   secuencia entera de propuestas antiguas al terminar el cálculo.
5. Ampliar al agarre y elevación limitada de caja vacía. Verificar sujeción y
   finalización; mantener el chasis quieto en esta primera prueba.
6. Validar depósito en la misma mesa y retorno vacío por la ruta revisada.
   Repetir tres ciclos completos con resultados y tiempos antes de añadir
   navegación a otra mesa. Tras interrupción clasificar apoyo/sujeción/postura;
   no reiniciar el ciclo de recogida desde el principio.

No hay actualmente un único comando físico completo habilitado para esta
secuencia. El paso2 exige el acceso y contrato descritos en
[Ejecución por etapas](EJECUTOR_ENTRY410_POR_ETAPAS.md); no fabricar su JSON.

## Optimización que indican los datos

Conservar modelo caliente durante una sesión supervisada ahorra recarga.
El mayor tiempo evitable entre propuestas parece estar en el periodo5s.
Próximo experimento de rendimiento: comparar sólo en shadow1Hz, manteniendo
inputs frescos y el mismo modelo, antes de cambiar ningún ritmo físico.
No se ha aplicado1Hz. Con sólo cinco muestras calientes no hay cota de peor caso.
El guardado de imágenes cuesta unos44ms: no es el cuello principal observado;
conservar evidencia en las primeras pruebas. Reutilizar resultados geométricos
únicamente con configuración, trayectorias y dominio de escena coincidentes.

## Instalación, verificación y reversión

Adaptador propio scripts/vla/runtime/cruzr_s2_inference_shadow.py: instrumenta
llamadas existentes con perf_counter y logs VLA_TIMING, conserva retornos y
excepciones. No altera pesos, propuestas, frecuencia, límites ni SDK original.
Instalado enVision /home/walker/cruzr-vla/additional/safe-runtime/
cruzr_s2_inference_shadow.py con contenedor detenido, mediante
scripts/vla/install_shadow_inference_adapter.py y hash anterior173b55da…b81.
Hash nuevo86f6a2ee47a77913154c9eda1291feea72ce04ca2051f779d862d9d20fe23fe7.
Backup remoto con sufijo .backup-20260914T161513486568Z; copia anterior externa
adapter-before.py, hash igual al anterior. Activado sólo al arrancar inferencia
shadow; seis llamadas medidas. Compilación Python, conservación de retorno y
excepciones y separación primera/caliente comprobadas localmente.

Reaplicar mediante el instalador con --check primero y --install
--expected-sha256 HASH_ACTUAL sólo con contenedor detenido y respaldo previo.
Tras firmware verificar compatibilidad de self.model.inference,
self.model.policy.get_action y callbacks antes de reaplicar instrumentación.
Para revertir: conservar versión actual, restaurar adaptador local desde
adapter-before.py y usar el mismo instalador con hash esperado86f6a2ee…23fe7,
contenedor detenido; guardar recibo y volver a comprobar. No reiniciar Motion.

Evidencia: ../Humanoide-vla-evidence/20260914_VLA_TIMING/. No contiene commit
necesario para reproducir fuentes locales: copias/hashes en sources/.
Cierre: INFERENCE_CONTAINER=exited, CONTROL_CONTAINER=exited,
COMMAND_PATH_SAFE=publishers:0. Sin HOME/READY/ENTRY ni prueba física realizada.
