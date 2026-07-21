/* XLPS2-Alpha CFW — static byte ring buffer (L2)
 *
 * Used for incoming RS485 Modbus frames and OTA data chunks (which may be
 * >= 1024B, ADR-005 CHUNK_SIZE / P0-2). No malloc; capacity fixed at compile
 * time. SPSC-safe for one producer (ISR/DMA) and one consumer (task). */
#ifndef SVC_RINGBUF_H
#define SVC_RINGBUF_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint8_t* buf;
    uint16_t capacity;
    volatile uint16_t head;   /* producer index */
    volatile uint16_t tail;   /* consumer index */
} ringbuf_t;

void    ringbuf_init(ringbuf_t* rb, uint8_t* buf, uint16_t capacity);
bool    ringbuf_push(ringbuf_t* rb, uint8_t b);
uint16_t ringbuf_push_n(ringbuf_t* rb, const uint8_t* data, uint16_t n);
bool    ringbuf_pop(ringbuf_t* rb, uint8_t* b);
uint16_t ringbuf_pop_n(ringbuf_t* rb, uint8_t* data, uint16_t n);
uint16_t ringbuf_available(const ringbuf_t* rb);
uint16_t ringbuf_free(const ringbuf_t* rb);
bool    ringbuf_is_empty(const ringbuf_t* rb);
bool    ringbuf_is_full(const ringbuf_t* rb);

#ifdef __cplusplus
}
#endif
#endif /* SVC_RINGBUF_H */
