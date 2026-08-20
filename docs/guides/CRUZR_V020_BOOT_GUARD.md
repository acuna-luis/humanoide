# Cruzr S2 v0.2.0 boot-readiness guard

## Purpose

After the offline v0.2.0 upgrade, the Vision computer can start Control Center
before the Motion computer has published its x86 self-check services. Control
Center then records `Service not available`, finishes self-check with
`passed=false`, enters `Fault`, shows a red face circle and leaves the head in
its lowered boot pose.

The guard installed on the Vision computer addresses only this confirmed race.
It does not modify the UBTECH images, uDoke configuration, Docker Compose,
maps, calibration, `HW_TYPE`, end-effector configuration or VLA state.

## Behaviour

At every Vision-computer boot, the guard:

1. waits for the Vision ROS and Control Center containers;
2. waits for Control Center to publish its version and verifies that the
   installed system is exactly v0.2.0;
3. waits for the Motion computer's x86 self-check services and motion actions;
4. reads the latest Control Center state;
5. exits without changes if the state is already `JoystickMode`;
6. proceeds only when the state is exactly `Fault` and both emergency stops and
   the charger report `0`;
7. restarts only `walker-system.control_center-1`;
8. requires self-check success, `StartMotion` success and `JoystickMode`;
9. sends the official `cruzr/move_head_home` task after rechecking the safety
   inputs.

The service has finite timeouts and performs at most one recovery per boot. It
does not retry indefinitely and does not bypass a failed safety input.

## Files installed on Vision

- `/usr/local/sbin/cruzr-v020-boot-guard`
- `/etc/systemd/system/cruzr-v020-boot-guard.service`
- `/usr/local/share/doc/cruzr-v020-boot-guard.md`

## Status and logs

```bash
sudo systemctl status cruzr-v020-boot-guard.service
sudo journalctl -u cruzr-v020-boot-guard.service -b --no-pager
sudo /usr/local/sbin/cruzr-v020-boot-guard --check
```

`--check` is read-only: it does not restart a container or command movement.

## Rollback

```bash
sudo systemctl disable --now cruzr-v020-boot-guard.service
sudo rm /etc/systemd/system/cruzr-v020-boot-guard.service
sudo rm /usr/local/sbin/cruzr-v020-boot-guard
sudo rm /usr/local/share/doc/cruzr-v020-boot-guard.md
sudo systemctl daemon-reload
```

Disable and review this workaround before applying a future UBTECH system
upgrade. Versions other than v0.2.0 are skipped automatically.
