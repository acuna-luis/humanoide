# Recorrido histórico con envolventes ampliadas — 07-09-2026

## Resultado

**No se autoriza movimiento.** Se ha muestreado el candidato histórico de
brazos, no el arranque real del incidente ni un estado actual del robot.
Las envolventes no se solapan con el cuerpo modelado, brazo contrario ni entre
sí en las muestras. **Sí se solapan con el propio brazo**, especialmente con
la AABB de `L/R_wrist_pitch_link`; por ello no hay resultado global libre.
Solapamiento de envolventes no equivale a contacto entre las piezas reales.

Con la hipótesis más amplia (75 mm de error radial del centro + 10 mm de
reserva geométrica, ambos supuestos no verificados), radio 204,411 mm:

| Comparación | Menor separación calculada en muestras | Interpretación |
|---|---:|---|
| Abrazadera izquierda–cuerpo | 23,757 mm | Separación condicional del modelo |
| Abrazadera derecha–cuerpo | 15,550 mm | Separación condicional del modelo |
| Izquierda–brazo contrario | 364,119 mm | Separación condicional del modelo |
| Derecha–brazo contrario | 364,001 mm | Separación condicional del modelo |
| Abrazadera–abrazadera | 250,166 mm | Separación condicional del modelo |
| Abrazadera–propio brazo | Solapamiento en ambos lados | Inconcluso; no aprobar recorrido |

Los cuatro radios ensayados (139,411 / 154,411 / 179,411 / 204,411 mm) presentan
esa misma clasificación global. La peor superposición con muñeca se encuentra
en el tramo staging→waypoint A; no es la fecha, trayectoria ni profundidad
física del contacto ocurrido. No se excluyó `wrist_pitch` para eliminar el aviso.

## Recorrido y alcance exacto

Secuencia: cero sintético → staging → waypoint A → READY B → waypoint A →
staging → cero sintético. Las catorce posiciones históricas se leen de
`20260903T093145_E6.0A/p14-ready-recovery-contract.json` y se asignan por nombres
en orden checkpoint, no por orden MetaMove. Todos los demás joints se fijan
explícitamente a cero sintético, incluida cabeza/cintura/elevador: no se afirma
que sea la postura observada ni la configuración instalada.

Se ensayan tres órdenes: ambos brazos sincronizados, izquierdo completo antes
del derecho en cada tramo, y derecho antes del izquierdo. Interpolación lineal
articular por fracción de segmento, **sin duración ni equivalencia Motion**.
No cubren todos los desfases posibles ni el escalonamiento observado de los
cinco grupos del HOME interno.

Primera resolución: 101 muestras por segmento, 3.030 muestras incluyendo
extremos repetidos. Segunda: 201, 6.030 muestras. Mismos mínimos globales y
clasificación observados a la precisión reportada. **Duplicar muestras no es
una demostración de volumen barrido continuo entre ellas.**

## Cobertura y exclusiones

- Se probaron 26 links de cuerpo con geometría, siete links disponibles de cada
  brazo/sensor y distancia entre las dos esferas de abrazadera.
- Los links `L/R_shoulder_pitch_link` no contienen geometría de colisión propia
  en este URDF. Se declaran como cobertura pendiente; no se considera el hombro
  libre por omisión ni se afirma que la pieza física esté totalmente ausente
  de mallas vecinas.
- Muñeca roll y sensor del mismo lado se separan como referencias de fijación,
  no como una ACM aprobada ni validación de holgura de esa unión.
- PGC/fingers no representan las abrazaderas instaladas y no se usan como sus
  mallas. Los brazos frente al cuerpo y entre sí sin las esferas, el entorno,
  caja/mesa, flexión, frenado y errores reales no están cualificados aquí.
- No se modifican radios ni se selecciona perfil operativo para obtener PASS.

## Evidencia y continuación

Analizador local `scripts/audit_clamp_pessimistic_path.py`, cuatro tests nuevos
de orden de joints, secuencia/retorno, interpolación e interacción de dos radios.
Suite de regresión v5 correcta. No red, ROS, publicación, despliegue ni movimiento.

En `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/`:

- `20260907_clamp_pessimistic_path.json`: 101 muestras/segmento.
- `20260907_clamp_pessimistic_path_201.json`: 201; hashes de fuentes y estados
  articulares de los mínimos por tramo/categoría/perfil.
- `20260907_requalification_regressions_v5.json`: suite local ampliada.

El siguiente refinamiento debe resolver el solapamiento útil–propio brazo
mediante geometría más precisa con incertidumbre acotada o evidencia local
de la relación mecánica; no mediante desactivar el par ni asumir contacto
permitido. Las cotas ampliadas ya aportan un filtro cuerpo/brazo contrario,
pero por sí solas no cierran la seguridad del conjunto ni HOME de arranque.
