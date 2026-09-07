# Cotas ampliadas: sensibilidad local, no aprobación física

El operador pide avanzar sin depender de respuesta de UBTECH usando cotas
pesimistas. Se implementa exploración offline; no se supone que una cifra
elegida por ser grande sea un límite demostrado de todo error real.

## Ensayo ejecutado

- Modelo nominal reportado: 82×100×130 mm; esfera de radio 119,411 mm.
- Centro de cálculo: origen sixforce del URDF. Error radial supuesto variable,
  no una medición de la unión real.
- Postura artificial: todos los joints no fijos explícitamente a cero. No es
  captura viva, reconstrucción del incidente ni ejecución de HOME.
- Se usan AABB mundiales envolventes de 26 links del cuerpo sin prefijo L_/R_.
  No incluyen brazos, sensores/manos L/R ni cajas, mesa, personas o entorno.

| Error de centro supuesto | Reserva geométrica supuesta | Radio | Mínimo L | Mínimo R |
|---|---|---|---|---|
| 10 mm | 10 mm | 139,411 mm | 88,757 mm | 80,550 mm |
| 25 mm | 10 mm | 154,411 mm | 73,757 mm | 65,550 mm |
| 50 mm | 10 mm | 179,411 mm | 48,757 mm | 40,550 mm |
| 75 mm | 10 mm | 204,411 mm | 23,757 mm | 15,550 mm |

Los mínimos corresponden a `lifter_pitch_2_link`. Son separaciones calculadas
entre esfera y AABB del modelo, no medidas físicas. No se eligió un perfil
operativo. No se validó la incertidumbre de las mallas, error de seguimiento,
flexión, parada o equivalencia del interpolador Motion.

**Conclusión limitada:** merece continuar el análisis offline; la ampliación
de geometría no hace fallar esta comprobación estática cuerpo-útil. No autoriza
movimiento. Un resultado libre sólo sería una separación condicional en esa
postura, bajo todas las hipótesis; un solapamiento de AABB/esfera tampoco
demostraría por sí solo una colisión de las piezas reales.

## Reproducibilidad y siguiente trabajo

`scripts/audit_clamp_pessimistic_screen.py` lee archivos locales y guarda
hashes de contrato, URDF, ZIP, analizador y helper FK. Salida exclusiva:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_pessimistic_screen.json`.
Tres tests verifican distancia punto-AABB e inválidos. No se contactó al robot.

Sigue pendiente comprobar recorridos completos con secuencias/interpolación
explícitas, interacción de brazos y entorno, y fundamentar los límites usados.
La eventual respuesta del proveedor puede aportar evidencia, pero no es la
única vía: una verificación local trazable de esas hipótesis también sirve.
No relajar o desplazar cotas únicamente para obtener un resultado favorable.
