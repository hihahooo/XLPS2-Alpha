/* XLPS2-Alpha CFW — central types (SSOT: config/data_dictionary.json, 33 fields)
 *
 * `cfw_telemetry_t` is a 1:1 mirror of the 33-field unified data dictionary.
 * Field order matches docs/contract/data-dictionary.md. Any change here MUST
 * be reflected in config/data_dictionary.json and pass tests/test_cross_module.py.
 *
 * NOTE (ADR-006): task dispatch registers (task_id / task_target_pos_mm /
 * task_axis) and OTA transport-private fields (seq/CRC/...) are intentionally
 * NOT part of the 33-field telemetry contract — they live in the Modbus
 * register map / FLAG sector, not in cfw_telemetry_t.
 */
#ifndef CFW_TYPES_H
#define CFW_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include "common/cfw_config.h"
#include "hsm/hsm_states.h"
#include "hsm/hsm_current_state.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CFW_STR_VER_LEN 32u

/* ---- enum telemetry fields (mirror data dictionary enums) ---- */
typedef enum {
    TASK_ST_IDLE      = 0,
    TASK_ST_QUEUED    = 1,
    TASK_ST_DISPATCHED= 2,
    TASK_ST_RUNNING   = 3,
    TASK_ST_PAUSED    = 4,
    TASK_ST_DONE      = 5,
    TASK_ST_FAILED    = 6,
    TASK_ST_CANCELED  = 7
} cfw_task_status_t;

typedef enum {
    LASER_OK       = 0,
    LASER_TRIGGERED= 1,
    LASER_ERROR    = 2
} cfw_laser_status_t;

typedef enum {
    PE_CLEAR    = 0,
    PE_OBSTACLE = 1,
    PE_UNKNOWN  = 2
} cfw_photoelectric_t;

typedef enum {
    SLOT_A = 0,
    SLOT_B = 1
} cfw_ota_slot_t;

typedef enum {
    OTA_ST_IDLE       = 0,
    OTA_ST_DOWNLOADING= 1,
    OTA_ST_FLASHING   = 2,
    OTA_ST_VERIFYING  = 3,
    OTA_ST_ACTIVE     = 4,
    OTA_ST_ROLLBACK   = 5
} cfw_ota_state_t;

typedef enum {
    OTA_RES_OK       = 0,
    OTA_RES_FAIL     = 1,
    OTA_RES_ROLLBACK = 2
} cfw_ota_result_t;

typedef enum {
    CMD_NONE          = 0,
    CMD_TASK_START    = 1,
    CMD_TASK_PAUSE    = 2,
    CMD_TASK_RESUME   = 3,
    CMD_TASK_CANCEL   = 4,
    CMD_FACTORY_RESET = 5,
    CMD_CHARGE        = 6
} cfw_command_in_t;

/* ---- 33-field unified telemetry (SSOT) ---- */
typedef struct {
    uint16_t current_state;            /* 1  ADR-003 */
    int32_t  position_mm;              /* 2 */
    int16_t  speed_mm_s;               /* 3 */
    uint8_t  battery_soc;              /* 4 */
    uint32_t track_id;                 /* 5  0=无码匿名 */
    cfw_task_status_t task_status;     /* 6  禁 task_state 别名 */
    uint8_t  task_progress_pct;        /* 7 */
    uint16_t fault_code;               /* 8 */
    uint8_t  fault_level;              /* 9  1-4 (ADR-006) */
    float    motor_current_a;          /* 10 */
    int8_t   motor_temp_c;             /* 11 */
    int32_t  encoder_position;         /* 12 */
    cfw_laser_status_t laser_status;   /* 13 */
    cfw_photoelectric_t photoelectric_state; /* 14 */
    cfw_ota_slot_t ota_active_slot;    /* 15 */
    cfw_ota_state_t ota_state;         /* 16 */
    uint8_t  ota_progress_pct;         /* 17 */
    char     ota_target_version[CFW_STR_VER_LEN]; /* 18 */
    cfw_ota_result_t ota_result;       /* 19 */
    char     fw_version[CFW_STR_VER_LEN];        /* 20 */
    char     smdl_version[CFW_STR_VER_LEN];      /* 21 */
    uint32_t param_revision;           /* 22 ADR-007 */
    uint32_t smdl_revision;            /* 23 */
    uint16_t interference_count;       /* 24 */
    uint16_t diag_code;                /* 25 */
    uint32_t audit_seq;                /* 26 */
    uint8_t  top_state;                /* 27 decode of current_state */
    uint8_t  sub_state;                /* 28 */
    uint8_t  region;                   /* 29 0/1/2 */
    bool     is_safe;                  /* 30 */
    cfw_command_in_t command_in;       /* 31 */
    uint32_t heartbeat_ts;             /* 32 */
    uint32_t uptime_s;                 /* 33 */
} cfw_telemetry_t;

/* ---- ADR-004 task dispatch (Modbus FC=0x10, base 0x2000) ----
 * Internal control registers; NOT part of the 33-field telemetry contract. */
typedef enum {
    TASK_TYPE_PICK  = 1,
    TASK_TYPE_PLACE = 2,
    TASK_TYPE_MOVE  = 3,
    TASK_TYPE_LIFT  = 4,
    TASK_TYPE_HOME  = 5
} cfw_task_type_t;

#define TASK_AXIS_WALK 1u   /* D_00 行走伺服 */
#define TASK_AXIS_LIFT 2u   /* D_01 顶升伺服 */

typedef struct {
    uint32_t        task_id;
    cfw_task_type_t task_type;
    int32_t         task_target_pos_mm;  /* 相对真0点 */
    uint8_t         task_axis;           /* 1=D_00, 2=D_01 */
    uint16_t        crc16;              /* Modbus RTU CRC */
} cfw_task_dispatch_t;

/* ---- Event bus types ---- */
typedef uint16_t evt_sub_id_t;   /* subscription handle (P0-1 fix target) */
#define EVT_SUB_ID_INVALID ((evt_sub_id_t)0xFFFFu)

typedef enum {
    EV_BOOT_DONE = 0,
    EV_TASK_RECEIVED,        /* payload: cfw_task_dispatch_t */
    EV_TASK_START,
    EV_TASK_PAUSE,
    EV_TASK_RESUME,
    EV_TASK_CANCEL,
    EV_ZERO_FOUND,
    EV_TRACK_IDENTIFIED,     /* payload: track_id (0=anonymous) */
    EV_ARRIVED,
    EV_SPEED_REACHED,      /* kinematics: reached cruise speed */
    EV_TARGET_NEAR,        /* kinematics: entered deceleration zone */
    EV_LOAD_DONE,
    EV_UNLOAD_DONE,
    EV_LOW_BATTERY,
    EV_BATTERY_OK,
    EV_CHARGE_START,
    EV_CHARGE_DONE,
    EV_OBSTACLE_DETECTED,
    EV_OBSTACLE_CLEAR,
    EV_WARNING,
    EV_WARNING_CLEAR,
    EV_ESTOP,                /* safety region global capture */
    EV_ESTOP_RESET,
    EV_FAULT,                /* payload: fault_level/code */
    EV_NUDGE_DONE,
    EV_CROSS_VERIFY_RESULT,  /* payload: cfw_cross_verify_t */
    EV_STATE_CHANGED,        /* payload: region + encoded state */
    EV_PARAM_SET,            /* payload: param key/value */
    EV_FACTORY_RESET,
    EV_OTA_CMD,              /* payload: target_version/slot */
    EV_OTA_DATA,             /* payload: chunk (seq + data, >=1024B capable) */
    EV_OTA_PROGRESS,
    EV_OTA_RESULT,
    EV_COUNT
} cfw_event_type_t;

#ifdef __cplusplus
}
#endif
#endif /* CFW_TYPES_H */
