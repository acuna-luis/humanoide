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
   it reads the current persistent ROSA log and therefore does not depend on
   Docker JSON logs surviving an unclean power cut;
3. waits for the Motion computer's x86 self-check services and motion actions;
   because DDS may advertise stale names before the x86 server is functional,
   readiness requires three successful lightweight `file_presence_check`
   responses separated by 15 seconds;
4. requires two successful rounds of real image samples from all six cameras
   used by the vendor self-check;
5. reads the latest Control Center state and classifies the original failure;
6. exits without changes if the state is already `JoystickMode`, or if it is
   safely waiting in `WaitEStopRelease` for a person to release the physical
   E-stop;
7. proceeds only when the state is exactly `Fault`, the log matches the known
   v0.2.0 readiness race, power/servo/overcurrent checks passed and both
   emergency stops and the charger report `0`;
8. restarts only `walker-system.control_center-1`;
9. waits for a new container start timestamp and a new persistent log before
   evaluating recovery, preventing stale `Fault` data from the old process;
10. requires self-check success, `StartMotion` success and `JoystickMode`;
11. sends the official `cruzr/move_head_home` task after rechecking the safety
   inputs.

The service has finite timeouts and performs at most one recovery per boot. It
does not retry indefinitely and does not bypass a failed safety input.

Do not use the internal `KEY1` as a standalone normal shutdown control. Use the
approved shutdown sequence for the robot; an abrupt body-computer power cut can
corrupt Docker JSON logs and interrupt filesystem writes.

After an emergency stop during normal operation, releasing the E-stop does not
necessarily restore Motion. On 2026-09-03 this unit remained in
`WaitStartMotion` with zero manipulation action servers. A single press of the
external rear Power/Start button was logged as `Power click` and only announced
the battery level; it did not generate `ButtonStartMotion`. Section 5.3.3 of the
vendor manual prescribes powering off and restarting the complete robot after
an emergency stop. Do not repeat the Power-button press or invoke `StartMotion`
over ROS as an improvised recovery; perform the supervised full power cycle.

That supervised restart was completed on the same date with the E-stop held.
Control Center correctly entered `WaitEStopRelease`; after the operator
released it, self-check and `StartMotion` passed and the terminal state was
`JoystickMode`. The first guard revision did not recognize
`WaitEStopRelease`, timed out with `CONTROL_STATE=unknown` and performed no
recovery. The current revision treats this state as a safe terminal defer:
`--run` records `NO_ACTION=waiting_for_physical_estop_release` and exits
without restarting a container or commanding the head.

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
