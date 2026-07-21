/* XLPS2-Alpha CFW — L4 task motion FSM helpers */
#include "app/task_fsm.h"
#include "hal/hal.h"
#include "svc/kinematics.h"

#define MFLAG_CRUISE 0x01u
#define MFLAG_NEAR   0x02u

void task_fsm_begin(cfw_runtime_t* rt, int32_t target_mm)
{
    rt->motion_target_mm = target_mm;
    rt->motion_active    = true;
    rt->motion_flags     = 0;
    rt->profile.v_max_mm_s = 300;
    rt->profile.a_mm_s2    = 200;
}

void task_fsm_stop(cfw_runtime_t* rt)
{
    rt->motion_active = false;
    hal_motor_set_velocity(hal_motor_stm32(), HAL_AXIS_WALK, 0);
}

void task_fsm_tick(cfw_runtime_t* rt)
{
    if (!rt->motion_active) return;
    const hal_motor_t* m = hal_motor_stm32();

    int32_t pos = rt->telem.position_mm;
    int16_t v = kin_step_velocity(pos, rt->motion_target_mm, rt->telem.speed_mm_s, &rt->profile);
    hal_motor_set_velocity(m, HAL_AXIS_WALK, v);
    rt->telem.speed_mm_s = v;

    int32_t d = rt->motion_target_mm - pos; if (d < 0) d = -d;

    if (!(rt->motion_flags & MFLAG_CRUISE) &&
        v >= (int16_t)(rt->profile.v_max_mm_s - 5)) {
        rt->motion_flags |= MFLAG_CRUISE;
        evt_publish(&rt->evt, EV_SPEED_REACHED, NULL, 0);
    }
    if (!(rt->motion_flags & MFLAG_NEAR) &&
        d <= kin_stop_dist(v, rt->profile.a_mm_s2)) {
        rt->motion_flags |= MFLAG_NEAR;
        evt_publish(&rt->evt, EV_TARGET_NEAR, NULL, 0);
    }
    if (d <= 3) {                       /* arrived at target */
        rt->motion_active = false;
        hal_motor_set_velocity(m, HAL_AXIS_WALK, 0);
        evt_publish(&rt->evt, EV_ARRIVED, NULL, 0);
    }
}
