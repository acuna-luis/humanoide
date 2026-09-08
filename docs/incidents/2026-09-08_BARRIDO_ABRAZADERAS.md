# Barrido condicionado de ambas abrazaderas: HOME → READY → HOME

**Actualización vigente 08-09 — ciclo HOME→READY→HOME satisfactorio:**
[Retorno y validación conjunta](2026-09-08_HOME_DESDE_READY_AUTORIZADO.md). Ambas acciones autorizadas por
el propietario terminaron SUCCEED/status=4, con extremos medidos y confirmación
visual posterior sin problemas/contacto. Estado final HOME: máximo 20D
0,002684 rad, velocidad 0 y actuadores sanos; VLA detenido, writers 0.
PASS físico de ida y vuelta con montaje actual para este ensayo. Captura parcial
del retorno: 2.251 estados, pico de velocidad reportada 2,049366 rad/s; no valida
el candidato offline lento ni frenado. Geometría continua/registro pendientes.
No monitor persistente ni habilitación ENTRY/VLA. El texto siguiente conserva
los resultados históricos de cada análisis; no anula el ensayo autorizado.
Los wrappers locales antiguos no fueron editados y conservan sus restricciones.

2026-09-08 — CALCULADO OFFLINE; no aprobación física ni movimiento.

## Geometría incluida

Se eliminan las seis geometrías históricas PGC. Se incluyen las dos
abrazaderas mediante envolventes esféricas: la caja descriptiva completa
u=[−35,47], v=[−55,45], profundidad=[−35,95] mm contiene, según las
medidas declaradas, placa, almohadillas, soporte y patitas. Su radio máximo
respecto al origen descriptivo es 119,411055 mm. La esfera contiene la pieza
para cualquier orientación, sin adivinar una rotación de montaje.

El centro se coloca en el origen sixforce del URDF **sólo como hipótesis**.
Se calculan errores radiales de ubicación de 10,25,50,75 mm y una reserva
geométrica de 10 mm. Son casos de sensibilidad: no se han demostrado esos
límites de error en el robot. Los radios resultantes son 139,411 a 204,411 mm.

## Cobertura del cálculo

Se evalúan seis tramos (tres de ida y tres de vuelta), con brazos simultáneos,
izquierdo primero y derecho primero. La cabeza sigue yaw=0/pitch hasta −0,65
en la primera etapa, y vuelve en la última. HOME sintético y demás ejes cero.
READY no se modifica. Cada tramo se divide en 2048 intervalos: 36.864 celdas.

No es sólo un chequeo puntual: a cada celda se le resta una cota de movimiento
entre su centro y cualquier instante del intervalo, para los dos cuerpos.
La cota usa la suma de cambios angulares por una cota global de brazo de
palanca (7,346695 m), más desplazamientos prismáticos si los hubiera. Los
ejes prismáticos permanecen a cero en estas curvas. El máximo desplazamiento
acotado de un punto por media celda es 17,729040 mm. Se conservan también
AABB exteriores del volumen barrido por cada abrazadera y tramo.

Esto cubre continuamente **las curvas articulares lineales y sincronizaciones
especificadas**, no demuestra la interpolación, sobrepasos, seguimiento ni
frenado del controlador real. Los tiempos/TimeRatio no se usan como garantía
de velocidad. Las distancias son contra cajas que contienen las mallas del
robot en sus marcos locales; hombros pitch usan el fallback visual explícito.

## Resultados refinados

Cota inferior de separación respecto a geometrías no L_/R_ (cuerpo central,
cabeza y base representadas); mínimos de ambos lados y tres sincronizaciones:

| Error supuesto del centro + reserva geométrica | HOME → READY | READY → HOME |
|---|---:|---:|
| 10 + 10 mm | 73,91 mm | 73,91 mm |
| 25 + 10 mm | 58,91 mm | 58,91 mm |
| 50 + 10 mm | 33,91 mm | 33,91 mm |
| 75 + 10 mm | 8,91 mm | 8,91 mm |

En el caso mayor, el mínimo contra el brazo contrario es 383,96 mm y entre
ambas envolventes de abrazaderas 243,72 mm (mínimos globales de ida/vuelta).
Son separaciones geométricas **condicionadas al modelo e hipótesis**, no
holguras medidas ni márgenes operativos recomendados.

No se obtiene separación demostrada respecto al propio brazo:

- Incluso en el caso de 10+10 mm quedan inconclusos sixforce, wrist_pitch,
  wrist_roll y elbow_yaw de cada lado.
- En 75+10 mm también queda inconcluso elbow_roll propio.
- No se excluyó artificialmente ninguna interfaz de montaje para lograr un OK.
  Una cota negativa no es una profundidad de penetración ni prueba de choque.

El cálculo inicial de 256 intervalos daba torso inconcluso. La refinación
elimina esa indeterminación numérica para estos casos, sin reducir los radios
ni alterar la ruta. La indeterminación propia muñeca/antebrazo persiste.

## Evidencia y reproducción

Script: `scripts/audit_clamp_continuous_routes.py`.
Resultados en directorio hermano `Humanoide-vla-evidence`:

- `20260908_clamp_continuous_routes.json`: 4608 celdas, primera resolución.
- `20260908_clamp_continuous_routes_refined.json`: 36.864 celdas, refinado.

Cada JSON contiene hipótesis, hashes de fuentes, pares, cotas y testigos por
celda mínima, AABB exteriores y exclusión de autorización física.

Comando reproducible, destino nuevo obligatorio:

```sh
python scripts/audit_clamp_continuous_routes.py --intervals 2048 --output /ruta/nueva/barrido.json
```

Pruebas: 4/4 nuevas (sincronizaciones, cota angular/prismática, contención de
arco y radio), 3/3 de perfil clamp y 3/3 de rutas; compilación Python OK.

## Pendiente y punto de reanudación

Ahora sí están incluidas las abrazaderas como envolventes conservadoras en
ambos barridos calculados. No hay todavía mallas de abrazaderas registradas
con transformación física verificada. La incertidumbre relevante queda
localizada en la relación abrazadera–muñeca/antebrazo propio y en los límites
de error supuestos. Faltan también equivalencia de interpolación real, escena
externa y envolvente de seguimiento/parada. El URDF no aporta geometría en
head_base, head_yaw y bases de brazo: no se afirma cobertura física completa
de esos enlaces. No se usan los éxitos anteriores para rellenar esos datos.

No se modifican montajes, trayectoria final, bloqueos ni configuración del
robot. `physical_authorized=false`, conexiones al robot=0, comandos=0.
