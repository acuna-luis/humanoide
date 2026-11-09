# Ruta Wi-Fi del PC al Cruzr — PC-ROUTE-20261109

El 09-11-2026, por petición del usuario, se configuró en el PC una ruta
persistente hacia Motion y Vision por la Wi-Fi del robot. No se modificó el
robot ni se enviaron órdenes de control.

## Destino y estado anterior

NetworkManager, perfil `Cruzr S2-0669 2`, UUID
`5a526476-8ad8-4946-84e2-57f158fe0a77`, interfaz activa
`wlxd40dab0b5b8e`, DHCP. Antes `ipv4.routes` estaba vacío e
`ipv4.never-default=no`. La ruta a `192.168.11.3` usaba la puerta de enlace
corporativa; Ethernet `eno1` no tenía portadora. `ipv4.ignore-auto-dns=no`
se conserva sin modificación. No se modificó el perfil histórico
`Cruzr S2-0669 1` ni la configuración corporativa.

Respaldo privado de los campos afectados y rutas anteriores en
`../Humanoide-vla-evidence/20261109_PC_ROUTE/`. SHA-256 de
`profile-fields-before.txt`:
`007838f0aa8b74bc69e5a4e2d0f4b8737cde458e6659815c1f16c9de05bd28dd`.
Es copia selectiva de los campos, no un backup completo del perfil ni de
credenciales. Se guardaron también copias documentales anteriores.

## Receta y activación

Verificar que el UUID identifica el perfil Wi-Fi del robot y que su interfaz
está activa; adaptar UUID e interfaz si cambian. Revisar rutas existentes antes
de aplicar: no añadir otra vez si ya existe ni reemplazar rutas ajenas.
Con el perfil anterior sin ruta específica, se ejecutó:

```bash
nmcli connection modify uuid 5a526476-8ad8-4946-84e2-57f158fe0a77 \
  +ipv4.routes '192.168.11.0/24 192.168.42.2' ipv4.never-default yes
nmcli device reapply wlxd40dab0b5b8e
```

El cambio se guardó en el perfil y `reapply` lo aplicó sin reconexión. No se
ha probado tras reinicio. Depende de NetworkManager, DHCP y la puerta de enlace
del robot `192.168.42.2`; si cambia la red se debe redescubrir.

## Verificación y reversión

**VERIFICADO 09-11-2026:** `ip route get` a `.11.2` y `.11.3` selecciona
`192.168.42.2` por `wlxd40dab0b5b8e`. La ruta a `1.1.1.1` y la única ruta
predeterminada conservan `wlo1`/DSA CORPORATE. Ping a Motion y Vision: 2/2;
`curl --noproxy '*' -I http://192.168.11.3/` devolvió HTTP 200. No demuestra
que la UI completa ni la teleoperación funcionen, ni la estabilidad del enlace.
Ethernet `eno1` seguía sin portadora; prioridad al reconectar y persistencia tras
reinicio **PENDIENTES**. Evidencia de rutas posteriores en `after.txt`, SHA-256
`8a2d8deefee036190893e8791cf987a7b5b3791ff951de1f3218856d0bf0179e`.

Para revertir únicamente este cambio, previa comprobación de que no se haya
alterado la ruta desde entonces:

```bash
nmcli connection modify uuid 5a526476-8ad8-4946-84e2-57f158fe0a77 \
  -ipv4.routes '192.168.11.0/24 192.168.42.2' ipv4.never-default no
nmcli device reapply wlxd40dab0b5b8e
```

Comprobar después `ip route get 192.168.11.3` y `ip route get 1.1.1.1`.
Esta reversión vuelve al estado observado, en el que el tráfico del robot
podía salir por la red corporativa. No incluye claves ni cambios de DNS.
