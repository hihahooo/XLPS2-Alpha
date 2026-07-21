/* XLPS2-Alpha CFW — ring buffer implementation (P0-2: >=1024B capable) */
#include "svc/ringbuf.h"

void ringbuf_init(ringbuf_t* rb, uint8_t* buf, uint16_t capacity)
{
    rb->buf = buf;
    rb->capacity = capacity;
    rb->head = 0;
    rb->tail = 0;
}

static uint16_t adv(uint16_t i, uint16_t cap) { return (i + 1u) % cap; }

bool ringbuf_push(ringbuf_t* rb, uint8_t b)
{
    uint16_t next = adv(rb->head, rb->capacity);
    if (next == rb->tail) return false; /* full */
    rb->buf[rb->head] = b;
    rb->head = next;
    return true;
}

uint16_t ringbuf_push_n(ringbuf_t* rb, const uint8_t* data, uint16_t n)
{
    uint16_t written = 0;
    for (uint16_t i = 0; i < n; i++) {
        if (!ringbuf_push(rb, data[i])) break;
        written++;
    }
    return written;
}

bool ringbuf_pop(ringbuf_t* rb, uint8_t* b)
{
    if (rb->head == rb->tail) return false; /* empty */
    *b = rb->buf[rb->tail];
    rb->tail = adv(rb->tail, rb->capacity);
    return true;
}

uint16_t ringbuf_pop_n(ringbuf_t* rb, uint8_t* data, uint16_t n)
{
    uint16_t read = 0;
    for (uint16_t i = 0; i < n; i++) {
        if (!ringbuf_pop(rb, &data[i])) break;
        read++;
    }
    return read;
}

uint16_t ringbuf_available(const ringbuf_t* rb)
{
    int32_t a = (int32_t)rb->head - (int32_t)rb->tail;
    if (a < 0) a += rb->capacity;
    return (uint16_t)a;
}

uint16_t ringbuf_free(const ringbuf_t* rb)
{
    return (uint16_t)(rb->capacity - ringbuf_available(rb) - 1u);
}

bool ringbuf_is_empty(const ringbuf_t* rb) { return rb->head == rb->tail; }
bool ringbuf_is_full(const ringbuf_t* rb)  { return adv(rb->head, rb->capacity) == rb->tail; }
