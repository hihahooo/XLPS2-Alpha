/* XLPS2-Alpha CFW — self-learning ambient-light interference filter (L2)
 *
 * Core: cross-verify photoelectric (hard trigger) vs laser (RS485 distance).
 * Single-route anomaly => interference (continue per ADR-006). Ambient-light
 * baseline is learned to adapt the debounce threshold so "开箱即用" survives
 * site-to-site light differences without code changes. */
#ifndef SVC_FILTER_H
#define SVC_FILTER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    FILT_CLEAR       = 0,
    FILT_OBSTACLE    = 1,
    FILT_INTERFERENCE= 2
} filt_verdict_t;

typedef struct {
    int32_t  ambient_avg;    /* EMA of ambient light 0..100 (%) */
    int32_t  ambient_var;    /* scaled running variance */
    uint16_t learn_count;
    bool     learned;
} filt_ctx_t;

#define FILT_AMBIENT_LEARN_GOAL 32u
#define FILT_AMBIENT_HIGH       70   /* % threshold above which single-route anomaly is interference */

void filt_init(filt_ctx_t* f);

/* Update learned ambient baseline (call when environment is known clear). */
void filt_learn_ambient(filt_ctx_t* f, uint8_t ambient_pct);

/* Classify current sensing: photoelectric blocked?, laser hard-triggered?,
 * laser distance (mm, ignored if <0). Returns the four-level verdict. */
filt_verdict_t filt_classify(filt_ctx_t* f,
                             bool pe_blocked,
                             bool laser_triggered,
                             int32_t laser_dist_mm);

#ifdef __cplusplus
}
#endif
#endif /* SVC_FILTER_H */
