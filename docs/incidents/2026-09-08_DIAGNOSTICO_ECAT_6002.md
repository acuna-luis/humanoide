# Diagnóstico EtherCAT 6002 tras reinicio

2026-09-08. Diagnóstico de lectura: sin llamadas de rearme, cambios de estado
EtherCAT, reinicios, publicaciones ni modificación de protecciones.

VERIFICADO: HW_TYPE=cruzr_s2_v1; configuración y log de inicialización identifican
6001=L_hand_ft, 6002=R_hand_ft (sensor seis ejes del brazo derecho).
El escaneo identifica 25 esclavos y ambos sensores FT; el 6002 se reconoce antes
del fallo. No es evidencia de ausencia permanente de alimentación/desconexión.

Secuencia (horas literales Motion, UTC+8; PC Madrid UTC+2):
- 16:23:52: sensores reconocidos, configuración s2_cruzr_config.yaml.
- 16:23:56: DCM in sync y transición PREOP→SAFEOP.
- 16:24:02.494: GetSdo timeout; a continuación intento vendor EnableServo.
- 16:24:05.032: 6002 SAFEOP ERROR 0x14, AL status0x1b Sync manager watchdog,
  no completa SAFEOP→OP. Master falla0x98110024 y se cierra.
- 16:24:06.103: SIGSEGV @0x0 del proceso de hardware.
- Docker reinicia hw automáticamente (RestartCount1, policyalways),
  StartedAt08:24:06.390Z; OOMKilledfalse.
- StartMotion falla reason19 tras timeout /mc/servo/enable. Manipulación espera
  ListControllers y no ofrece servidor ni estados de actuadores.

Código0x001B: esclavo no recibe datos de proceso en el plazo del watchdog,
según documentación EtherCAT de Beckhoff, sección Error Code0x001B:
https://download.beckhoff.com/download/Document/io/ethercat-terminals/ethercatsystem_en.pdf
No aumentar watchdog como reparación. No es código de sobrecarga mecánica.

Conclusión: mecanismo de bloqueo identificado en comunicación/inicialización
EtherCAT del sensor derecho; además defecto de robustez software (SIGSEGV
posterior al fallo). Relación causal exacta del timeout SDO no demostrada;
no se atribuye a llamada diagnóstica: el agente no llamó SDO/EnableServo.
No se demuestra sensor roto, cable suelto, caída de alimentación ni relación
causal con el disparo FT anterior. Enumeración y DCM no excluyen intermitencia.
La carga CPU posterior baja y OOMfalse no descartan un retardo durante arranque.
Las búsquedas PCI fallidas del kernel preceden a detección exitosa Intel157b
03:00.0; no tratarlas por sí solas como avería de tarjeta.

Siguiente paso técnico: conservar este paquete para UBTECH y solicitar análisis
6002/AL0x001B durante SAFEOP→OP y del SIGSEGV; comprobar configuración de datos
cíclicos/inicialización y, mediante personal cualificado con equipo aislado y
brazos asegurados, cableado/conectores/alimentación de la rama derecha. No
manipular conectores energizados ni ampliar watchdogs. No se envió informe
externo (sin autorización para mensajes). No nuevo reinicio para probar.
Estado final permanece Fault, HOME no demostrado, sin monitor persistente.

Evidencia externa: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T082658Z_ECAT6002-DIAG/`.
