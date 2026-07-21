/* XLPS2-Alpha CFW — state vocabulary helpers (debug / telemetry labels) */
#include "hsm/hsm_states.h"
#include <stdio.h>

const char* cfw_region_name(uint8_t region)
{
    switch (region) {
        case REGION_MAIN:   return "MAIN";
        case REGION_ENERGY: return "ENERGY";
        case REGION_SAFETY: return "SAFETY";
        default:            return "?";
    }
}

/* Build a human-readable path "REGION.TOP.SUB" into buf (must be >= 40 bytes). */
void cfw_state_path(uint16_t encoded, char* buf, uint16_t buflen)
{
    uint8_t r, t, s;
    cfw_state_decode(encoded, &r, &t, &s);
    if (encoded == CFW_STATE_UNINIT) {
        snprintf(buf, buflen, "UNINIT");
        return;
    }
    snprintf(buf, buflen, "%s.T%d.S%d", cfw_region_name(r), (int)t, (int)s);
}
