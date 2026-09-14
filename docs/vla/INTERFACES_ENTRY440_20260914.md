# Interpretación de los avisos internos durante ENTRY440

2026-09-14, Europe/Madrid. VLA-01. **VERIFICADO offline / interpretación física
INFERENCIA.** Sólo cálculos del PC; sin consultas, movimientos, instalaciones,
recargas o modificaciones remotas. No se altera el modelo ni sus filtros.

## Los 54 avisos no equivalen a 54 choques físicos

Se desglosan para el acceso a ENTRY440 y retorno vacío ya calculados, incluyendo
la postura archivada con cabeza bajada y el final HOME20D:

- **30 pares invariantes:** la cadena cinemática relativa no contiene ninguno
  de los veinte ejes controlados. Si chasis y articulaciones auxiliares permanecen
  fijos, el movimiento no cambia su separación. Es una propiedad estructural,
  no una conclusión obtenida por muestreo. No constituyen una interferencia
  nueva introducida por ENTRY en ese modelo; no acredita el montaje real.
- **24 interfaces móviles:** uniones del elevador, cintura, cabeza, hombros,
  codos y muñecas. Se analizaron 696 combinaciones de sus uno o dos ejes
  relativos dentro del rectángulo que contiene acceso, retorno y error ±1°,
  intersectado con límites URDF.
- **Ninguno de estos 54 pares contiene las abrazaderas (`hand_link`).** Los
  pares que las afectan conservan la comprobación del análisis geométrico
  anterior. No se extrapola esto a trayectorias distintas de ENTRY440.

De las 24 interfaces móviles, **11 mantienen superficies CAD separadas en todas
las muestras**, 10 presentan cruce de superficies en todas y 3 alternan ambas
situaciones. Los 13 pares que presentan algún cruce también lo presentan en
al menos una referencia HOME/PICO. En ninguno de los 696 casos se encontró un
testigo CAD validado fuera de todas las cajas de referencia HOME/PICO ampliadas
2 mm. Esto apoya revisar la representación de las uniones antes de interpretar
los avisos como choques físicos, pero **no prueba ausencia continua de nuevos
contactos ni autoriza excluir los pares enteros**. Las cajas son cotas amplias;
los listados de contactos pueden truncarse a 64 y no cubren todo el solapamiento.

Ejemplos de distancia entre superficies originales en las muestras:

| Interfaz | Distancia observada |
|---|---:|
| Chasis–primer tramo del elevador | 20,65–20,78 mm |
| Torso–primer componente de cada hombro | 7,70–7,87 mm |
| Hombro roll–yaw, ambos lados | aproximadamente 0,309–0,311 mm |
| Base del elevador–primer tramo | aproximadamente 1,9996 mm |

Una holgura menor de 2 mm puede disparar el margen general sin que las superficies
se crucen. Un volumen derivado también puede rellenar un hueco del CAD y producir
un aviso. Por ello **no deben presentarse todos estos avisos como colisiones
reales**. La distancia entre fronteras tampoco demuestra por sí sola separación
del material: dos sólidos anidados pueden tener fronteras separadas.

## Comprobación continua de fronteras

Para las 11 interfaces que no cruzan superficies en las muestras se añade una
segunda comprobación. Parte del rectángulo completo de ángulos, calcula la
distancia exacta entre las fronteras CAD en cada centro y resta la cota global
de desplazamiento durante media caja: `distancia - radios · semianchos`.
Se conserva una reserva numérica de 1e-7 m. Si la cota es positiva, esa caja
queda demostrada; si no, se divide y exige demostrar ambos hijos.

Esto demuestra **separación continua de las superficies fuente**, no un margen
físico de 2 mm, ausencia de contención, precisión del montaje o autorización de
ejecución. La salida distingue esos campos explícitamente. La primera pasada
demuestra 8 pares y agota 10 s de presupuesto en otros 3; éstos se recalculan
separadamente con hasta 45 s y 65536 nodos. El informe de evidencia conserva
ambas pasadas y sus fuentes exactas. La segunda demuestra ambos hombros roll–yaw
con 2047 cajas consultadas por lado: sus cotas conservadoras de frontera son
0,05960 y 0,05949 mm. **Resultado acumulado: 10 fronteras separadas de forma
continua y una pendiente de prueba continua**, elevador2–torso. Ésta conserva
separación en las 132 muestras (0,279–0,344 mm), pero agota 45 s después de
21755 consultas; no se la marca como demostrada.

El desglose útil para revisar la representación es, por tanto, **30 invariantes,
10 con fronteras continuamente separadas, 13 con cruces CAD ya presentes en
referencias HOME/PICO y 1 cuya separación continua permanece pendiente**.
No son 54 interferencias nuevas introducidas por ENTRY. La ausencia de cruce
de fronteras en 10 pares no se convierte en una excepción de volumen ni en una
reducción de margen del ejecutor.

Los cruces CAD que alternan con separación están en torso–cabeza y ambos
codos roll–yaw. No se observó un contacto físico: son consultas al modelo.
Los otros diez cruces persistentes se concentran en elevador/cintura,
hombros pitch–roll y muñecas. El informe lista los ejes, rangos y referencias
de cada par, evitando pedir una aprobación genérica de los 54 avisos.

## Herramientas, pruebas y conservación

Herramientas nuevas del PC:

- `scripts/vla/audit_entry_route_interfaces.py`: clasificación por cadena
  relativa, superficies fuente y búsqueda de contactos fuera de referencias.
- `scripts/vla/prove_entry_interface_boundaries.py`: demostración continua de
  fronteras con cotas finitas y rechazo ante presupuesto agotado.
- Sus dos archivos de tests: **6 tests pasan**, incluyendo cobertura del error
  y límites, cajas completamente separadas, contacto, presupuesto y datos
  inválidos. Ninguna prueba se interpreta como validación del hardware.

Evidencia privada:
`../Humanoide-vla-evidence/20260914T093721Z_ENTRY440-INTERFACES/`.
Contiene `interfaces.json`, `boundaries.json`, `boundaries-refined.json`,
comandos/logs, backups documentales, fuentes finales y hashes. La primera
versión del demostrador queda conservada como `boundary-proof-source-initial.py`.
Modelos, dataset y estados de origen se referencian por hash, sin añadir
binarios del proveedor ni datos privados a Git.

Reproducción: ejecutar con `.venv/general-home/bin/python` existente los arrays
de `command.json`, `boundaries-command.json` y `boundaries-refined-command.json`,
usando rutas de salida nuevas. La segunda pasada verifica que la anterior
corresponde al mismo informe de interfaces. No hay dependencias nuevas.

Aplicación tras actualización: restaurar estas herramientas y evidencia por
hash, verificar modelo compatible y ejecutar offline. No se instala nada en
Motion/Vision. Reversión: retirar únicamente las cuatro herramientas/tests
nuevos y estas anotaciones documentales, preservando el trabajo anterior.
Sin cambios remotos que restaurar, commit o push.

El resultado ayuda a interpretar las uniones; **no se modifica el certificado
geométrico previo ni se emite aprobación física**. Registro de escena y error,
trayectoria aplicada, seguimiento y parada mantienen su estado anterior.
