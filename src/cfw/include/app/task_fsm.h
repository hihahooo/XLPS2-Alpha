/* XLPS2-Alpha CFW — L4 task motion FSM helpers (driven by kinematics + HSM) */
#ifndef APP_TASK_FSM_H
#define APP_TASK_FSM_H

#include "cfw.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Begin a motion toward target_mm (relative true-zero). Sets up the active
 * profile; the per-tick velocity command happens in task_fsm_tick(). */
void task_fsm_begin(cfw_runtime_t* rt, int32_t target_mm);

/* Stop any active motion (commands zero velocity). */
void task_fsm_stop(cfw_runtime_t* rt);

/* One motion-control tick: compute velocity via kinematics, command the walk
 * servo, and publish EV_SPEED_REACHED / EV_TARGET_NEAR / EV_ARRIVED on edges. */
void task_fsm_tick(cfw_runtime_t* rt);

#ifdef __cplusplus
}
#endif
#endif /* APP_TASK_FSM_H */
