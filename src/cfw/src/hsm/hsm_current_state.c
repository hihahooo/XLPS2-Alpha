/* XLPS2-Alpha CFW — current_state codec implementation (ADR-003) */
#include "hsm/hsm_current_state.h"

uint16_t cfw_state_encode(uint8_t region, uint8_t top_state, uint8_t sub_state)
{
    return (uint16_t)(((uint16_t)(region   & 0x3u)  << 14) |
                      ((uint16_t)(top_state & 0x3Fu) << 8)  |
                      ((uint16_t)(sub_state & 0xFFu)));
}

void cfw_state_decode(uint16_t v, uint8_t *region, uint8_t *top_state, uint8_t *sub_state)
{
    *region    = (uint8_t)((v >> 14) & 0x3u);
    *top_state = (uint8_t)((v >> 8)  & 0x3Fu);
    *sub_state = (uint8_t)( v        & 0xFFu);
}

bool cfw_state_is_valid(uint16_t v)
{
    if (v == CFW_STATE_UNINIT) return false;
    uint8_t r, t, s;
    cfw_state_decode(v, &r, &t, &s);
    return (r < REGION_COUNT);
}
