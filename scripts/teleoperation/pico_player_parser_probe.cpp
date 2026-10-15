// Diagnostic-only interposer: stop BEFORE ROSA initialization, hence before
// any action client, file loading or robot commands in the pinned player.
// Never load this library for an actual replay. No vendor binary is changed.
#include <cstdio>
#include <cstdlib>

extern "C" void blocked_rosa_init()
    asm("_ZN4rosa4initEiPKPKcSt10shared_ptrINS_8ArgumentEE");

extern "C" void blocked_rosa_init() {
    std::fputs("PICO_PLAYER_PARSE_OK_ROSA_INIT_BLOCKED\n", stderr);
    std::fflush(stderr);
    std::_Exit(86);
}
