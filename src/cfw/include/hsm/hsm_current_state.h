/* XLPS2-Alpha CFW — current_state codec (ADR-003)
 *
 *   current_state = (region << 14) | (top_state << 8) | sub_state
 *   0xFFFF = 未初始化
 *
 * Host-testable, no HAL dependency. The decode MUST stay byte-identical with
 * HMI contract/types.ts `decodeCurrentState()` and OTA schema.py.
 */
#ifndef HSM_CURRENT_STATE_H
#define HSM_CURRENT_STATE_H

#include <stdint.h>
#include <stdbool.h>
#include "hsm_states.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CFW_STATE_UNINIT 0xFFFFu

/* Encode the three hierarchy components into the single telemetry field. */
uint16_t cfw_state_encode(uint8_t region, uint8_t top_state, uint8_t sub_state);

/* Decode the three hierarchy components from the telemetry field. */
void cfw_state_decode(uint16_t v, uint8_t *region, uint8_t *top_state, uint8_t *sub_state);

/* A valid encoded state is never the uninit sentinel and has region <= 2. */
bool cfw_state_is_valid(uint16_t v);

#ifdef __cplusplus
}
#endif
#endif /* HSM_CURRENT_STATE_H */
