/* XLPS2-Alpha CFW — STM32 ILaser (RS485 laser, value cached by Modbus RX)
 * Raw distance/status are populated by the Modbus RTU task (comm/modbus),
 * keeping the L1 interface register-free for callers. */
#include "hal/hal.h"

static int32_t            g_dist = -1;                 /* <0 == invalid */
static hal_laser_status_t g_st   = LASER_DEV_ERROR;

/* Called by the Modbus RX path when a laser frame is parsed. */
void hal_laser_stm32_feed(int32_t dist_mm, hal_laser_status_t st)
{ g_dist = dist_mm; g_st = st; }

static cfw_err_t l_dist(void* d, int32_t* distance_mm) { (void)d; *distance_mm = g_dist; return CFW_OK; }
static cfw_err_t l_st(void* d, hal_laser_status_t* st) { (void)d; *st = g_st; return CFW_OK; }

static const hal_laser_ops_t L_OPS = { l_dist, l_st };
static hal_laser_t L_INST = { NULL, &L_OPS };

const hal_laser_t* hal_laser_stm32(void) { return &L_INST; }
