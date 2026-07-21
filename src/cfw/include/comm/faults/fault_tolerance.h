/* XLPS2-Alpha CFW — four-level fault tolerance (ADR-006, L3/L4 behavior)
 *
 * 一级 CHECK_DIST    soft debounce of ranging readings
 * 二级 NUDGE_RETRY   micro nudge + re-detect
 * 四级 CROSS_VERIFY  cross-verify BEFORE stopping (dual-route proof)
 * 三级 SLOW_STOP/ESTOP graded stop / global e-stop
 *
 * Cross-verify compares laser_distance_mm (RS485) vs laser_triggered (hard
 * trigger); consistent => real obstacle/clear; single-route anomaly =>
 * interference, continue + record cross_verify_fault_ch.
 *
 * No HAL dependency (host-testable). SSOT: docs/contract/adr-006-fault-tolerance.md
 */
#ifndef COMM_FAULT_TOLERANCE_H
#define COMM_FAULT_TOLERANCE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ADR-006 four levels (NOTE: level number != execution order) */
typedef enum {
    FT_L1_CHECK_DIST   = 1,
    FT_L2_NUDGE_RETRY  = 2,
    FT_L4_CROSS_VERIFY = 4,
    FT_L3_SLOW_STOP    = 3,
    FT_ESTOP           = 5
} ft_level_t;

typedef enum {
    CV_OBSTACLE     = 0,
    CV_CLEAR        = 1,
    CV_INTERFERENCE = 2
} cv_verdict_t;

typedef struct {
    int32_t laser_distance_mm;  /* RS485 laser, <0 == invalid */
    bool    laser_triggered;    /* hard photoelectric trigger */
    uint8_t ambient_pct;        /* ambient light (self-learning input) */
} ft_sense_t;

typedef struct {
    uint16_t nudge_retry_index;     /* ADR-001 nudge_retry_index */
    uint16_t cross_verify_fault_ch; /* ADR-001/006 cross_verify_fault_ch */
    uint8_t  fault_level;           /* 1..4 (telemetry fault_level) */
    uint16_t fault_code;
    bool     estop;
    uint8_t  check_dist_count;      /* L1 consecutive obstacle reads */
} ft_state_t;

typedef enum {
    FT_ACT_CONTINUE = 0,
    FT_ACT_NUDGE    = 1,
    FT_ACT_STOP     = 2,
    FT_ACT_ESTOP    = 3
} ft_action_t;

#define FT_CV_NEAR_MM      150     /* distance below which laser counts as "obstacle" */
#define FT_CHECK_DIST_DEBOUNCE 3  /* L1: consecutive reads to confirm */
#define FT_NUDGE_MAX_RETRY 3      /* L2: max micro nudges before escalate */

void      ft_state_init(ft_state_t* st);

/* CROSS_VERIFY primitive (ADR-006, level 4). */
cv_verdict_t ft_cross_verify(const ft_sense_t* s);

/* L1 soft debounce: returns true once obstacle confirmed across debounce window. */
bool ft_check_dist(ft_state_t* st, bool obstacle_now);

/* Full evaluator: given current sensing + state, returns recommended action
 * and updates counters/levels (L1->L2->L4->L3 sequencing is driven by caller). */
ft_action_t ft_evaluate(ft_state_t* st, const ft_sense_t* s);

#ifdef __cplusplus
}
#endif
#endif /* COMM_FAULT_TOLERANCE_H */
