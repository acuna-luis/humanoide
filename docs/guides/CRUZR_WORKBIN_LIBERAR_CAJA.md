# Liberar una caja con las abrazaderas

Utiliza [cruzr_blue_workbin_open_only.sh](../../scripts/cruzr_blue_workbin_open_only.sh)
desde la carpeta del proyecto. Repite la apertura del fabricante ejecutada y
confirmada físicamente el 09-09-2026 tras `ClampBoxImperfect`.

## Qué hace

Separa cada abrazadera **5 cm hacia fuera en unos 2 segundos**. No baja la
caja previamente, no navega ni vuelve a HOME. La caja puede caer o bascular.
Los brazos quedan abiertos junto a ella. Es una recuperación manual desde
el agarre frontal workbin; no sirve desde PICO ni desde cualquier postura.

## Cómo usarlo

1. Detén otros scripts y mandos, incluido PICO. Comprueba que el robot esté
   estable, con las ruedas bloqueadas y el cargador desconectado.
2. Deja libres ambos recorridos de brazos y abrazaderas. La caja debe estar
   vacía y apoyada de forma estable, o debes aceptar su caída con toda la zona
   despejada. Nadie debe sujetarla con las manos ni situarse debajo. Mantén
   una persona junto al paro durante la apertura.
3. Comprueba el estado, sin movimiento:

   ```bash
   ./scripts/cruzr_blue_workbin_open_only.sh --check
   ```

4. Si corresponde esta recuperación y la zona está preparada, ejecuta:

   ```bash
   ./scripts/cruzr_blue_workbin_open_only.sh --run
   ```

   Cuando lo pida, escribe exactamente **`ABRIR ABRAZADERAS`** y pulsa Enter.
   Después de la confirmación se repiten los controles técnicos; pueden tardar
   alrededor de un minuto antes de que empiece la apertura.
5. Comprueba que la caja haya quedado estable y las abrazaderas libres. El
   éxito de Motion no sustituye esa comprobación física.

No necesitas seleccionar un mapa. El script utiliza la conexión disponible
a Motion, incluida la ruta Wi-Fi configurada. Sin argumentos equivale a
`--check`. `--run` exige una terminal interactiva; no admite `--yes` ni `--fast`.

## Si se detiene

- `OPEN_ONLY_NO_ACTION`: el registro ya contiene un intento de esta apertura.
  No la repite, incluso si aquel intento falló. Comprueba el resultado físico;
  no borres el registro para forzar otra apertura.
- `OPEN_ONLY_BLOCKED` o fallo de preflight: falta un requisito, hay otro
  publicador, cambió la tarea o se detectó un evento de fuerza/autocolisión.
  No uses un comando directo para saltarlo.
- Fallo o timeout durante la apertura: el resultado puede ser incierto.
  No hay reintento, apertura adicional ni HOME automáticos. Si existe movimiento
  peligroso, usa el paro y solicita recuperación presencial.

Cada batería debe cumplir el mínimo vigente del ciclo (20 % al publicar esta
guía). El script también verifica paros, cargador, actuadores, consignas,
servidor y ausencia de acción en curso. El historial restringe el contexto,
pero no certifica la postura física ni detecta personas, apoyos o dedos.

La tarea se instala sólo si falta, conservando la primitiva vendor y sin
reiniciar Motion. Un archivo existente con otro hash bloquea la instalación.
La liberación manual no convierte el agarre fallido en válido para transporte:
`--resume-held` y `--deposit-held` mantienen su verificación de agarre.

## Volver a HOME después de liberar

Tras confirmar caja estable y abrazaderas vacías y libres, utiliza:

```bash
./scripts/cruzr_recover_to_home.sh --check
./scripts/cruzr_recover_to_home.sh --run
```

Ejecuta --run sólo si --check pasa y el recorrido físico está despejado.
El recuperador reconoce la apertura aislada terminada con éxito; no basta
con haberla iniciado. Retrocede **0,50 m** y después recoge brazos/cuerpo a HOME.
Exige **1,50 m libres detrás**, recorrido completo de brazos despejado, caja
estable fuera del recorrido, cargador/Ethernet desconectados, ningún otro mando
y una persona junto al paro. Escribe `RECUPERAR CICLO DE CAJA A HOME` cuando
lo solicite. No añadas un retroceso previo. Si falla después de retroceder,
no repitas toda la secuencia sin revisar dónde quedó el robot.

La comprobación del 09-09 posterior a esta integración se detuvo por batería
19,9 % (<20 %). Primero cargar; el HOME de esta recuperación sigue pendiente.
