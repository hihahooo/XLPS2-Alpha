#!/usr/bin/env python3
"""Equivalence harness: mirrors the C HAL-independent core algorithms exactly,
so they can be validated in this sandbox (no C toolchain present). The C tests
in test_*.c are the authoritative suite and run under gcc in CI. This mirrors:
  - ADR-003 current_state codec
  - HSM engine (regions, nesting, history, guards, self-transition)
  - event bus P0-1 (unsubscribe by sub_id) and P0-2 (payload >= 1024B)
  - ADR-006 cross-verify
"""
import sys

# ---------- ADR-003 codec ----------
def cw_encode(region, top, sub):
    return ((region & 0x3) << 14) | ((top & 0x3F) << 8) | (sub & 0xFF)
def cw_decode(v):
    return ((v >> 14) & 0x3, (v >> 8) & 0x3F, v & 0xFF)
def cw_valid(v):
    if v == 0xFFFF: return False
    r,t,s = cw_decode(v); return r < 3

# ---------- HSM engine mirror ----------
HSM_ID_INVALID = 0xFFFF
HSM_TO_HISTORY = 0xFFFE
SUB_CONTAINER = 0xFF
def HSM_ID(region, top, sub):
    return ((region & 0x3) << 12) | ((top & 0x3F) << 8) | (sub & 0xFF)
def HSM_TOP(i): return (i >> 8) & 0x3F
def HSM_SUB(i): return i & 0xFF

REGION_MAIN, REGION_ENERGY, REGION_SAFETY = 0,1,2
MAIN_BOOTING,MAIN_IDLE,MAIN_TRAVELING = 0,1,6
TRAV_ACCEL,TRAV_CRUISE = 0,1
ENERGY_POWER_NORMAL,ENERGY_CHARGING = 0,2
SUB_BUSY = 1
SUB_NONE = 0
SAFETY_ESTOP = 2
EV_BOOT_DONE,EV_LOW_BATTERY,EV_TASK_START,EV_ARRIVED,EV_OBSTACLE_DETECTED,EV_NUDGE_DONE,EV_CHARGE_DONE = 0,1,2,3,4,5,6

A  = HSM_ID(REGION_MAIN, MAIN_BOOTING, SUB_CONTAINER)
A1 = HSM_ID(REGION_MAIN, MAIN_BOOTING, SUB_BUSY)
B  = HSM_ID(REGION_MAIN, MAIN_IDLE, SUB_CONTAINER)
C  = HSM_ID(REGION_MAIN, MAIN_TRAVELING, SUB_CONTAINER)
C1 = HSM_ID(REGION_MAIN, MAIN_TRAVELING, TRAV_ACCEL)
C2 = HSM_ID(REGION_MAIN, MAIN_TRAVELING, TRAV_CRUISE)
E0  = HSM_ID(REGION_ENERGY, ENERGY_POWER_NORMAL, SUB_CONTAINER)
E0a = HSM_ID(REGION_ENERGY, ENERGY_POWER_NORMAL, SUB_BUSY)
E1  = HSM_ID(REGION_ENERGY, ENERGY_CHARGING, SUB_CONTAINER)
E1a = HSM_ID(REGION_ENERGY, ENERGY_CHARGING, SUB_BUSY)

STATES = [
    (A,  HSM_ID_INVALID, A1,  False),
    (A1, A,  HSM_ID_INVALID, False),
    (B,   HSM_ID_INVALID, HSM_ID_INVALID, False),
    (C,   HSM_ID_INVALID, C1,  False),
    (C1,  C,  HSM_ID_INVALID, False),
    (C2,  C,  HSM_ID_INVALID, False),
    (E0,  HSM_ID_INVALID, E0a, True),
    (E0a, E0,  HSM_ID_INVALID, False),
    (E1,  HSM_ID_INVALID, E1a, False),
    (E1a, E1,  HSM_ID_INVALID, False),
]
def guard_false(ctx): return False
TRANS = [
    (A,  EV_BOOT_DONE, None, B, None),
    (B,  EV_TASK_START, None, C, None),
    (C1, EV_ARRIVED, None, C2, None),
    (C2, EV_OBSTACLE_DETECTED, guard_false, C2, None),
    (C2, EV_NUDGE_DONE, None, C2, None),
    (E0, EV_LOW_BATTERY, None, E1, None),
    (E1, EV_CHARGE_DONE, None, HSM_TO_HISTORY, None),
]

class Eng:
    def __init__(self):
        self.states = STATES
        self.trans = TRANS
        self.regions = []
        self.rcount = 0
    def find(self, i):
        for s in self.states:
            if s[0]==i: return s
        return None
    def parent_of(self, i):
        s=self.find(i); return s[1] if s else HSM_ID_INVALID
    def is_anc(self, node, anc):
        c=node
        while c!=HSM_ID_INVALID:
            if c==anc: return True
            c=self.parent_of(c)
        return False
    def lca(self, a, b):
        chain=[]; c=b
        while c!=HSM_ID_INVALID and len(chain)<200:
            chain.append(c); c=self.parent_of(c)
        c=a
        while c!=HSM_ID_INVALID:
            if c in chain: return c
            c=self.parent_of(c)
        return HSM_ID_INVALID
    def rec_hist(self, region, exited):
        s=self.find(exited)
        if s and s[3]:
            child=self.regions[region]['active']
            while child!=HSM_ID_INVALID and self.parent_of(child)!=exited:
                child=self.parent_of(child)
            self.regions[region]['history']=child
            self.regions[region]['history_set']=True
    def enter(self, region, target):
        cur=target
        while cur!=HSM_ID_INVALID:
            s=self.find(cur)
            if not s: break
            cur=s[2] if s[2]!=HSM_ID_INVALID else None
            if cur is None or cur==HSM_ID_INVALID: break
        # re-walk properly:
        cur=target
        while cur!=HSM_ID_INVALID:
            s=self.find(cur)
            if not s: break
            if s[2]!=HSM_ID_INVALID:
                cur=s[2]
            else:
                break
        self.regions[region]['active']=cur
    def exit_to(self, region, start, stop):
        cur=start
        while cur!=stop and cur!=HSM_ID_INVALID:
            self.rec_hist(region, cur)
            cur=self.parent_of(cur)
    def resolve(self, region, tgt):
        if tgt==HSM_TO_HISTORY:
            if self.regions[region]['history_set']:
                return self.regions[region]['history']
            return self.regions[region]['initial']
        return tgt
    def add_region(self, region, initial):
        self.regions.append({'region':region,'initial':initial,'active':HSM_ID_INVALID,'history':HSM_ID_INVALID,'history_set':False})
        self.rcount+=1
    def start(self):
        for r in self.regions:
            self.enter(r['region'], r['initial'])
    def dispatch_region(self, r, ev):
        reg=self.regions[r]
        start=reg['active']
        if start==HSM_ID_INVALID: return
        src=start; hit=None
        while src!=HSM_ID_INVALID:
            for t in self.trans:
                if t[0]==src and t[1]==ev:
                    if t[2] is None or t[2](None):
                        hit=t; break
            if hit: break
            src=self.parent_of(src)
        if hit is None: return
        s=src; tgt=self.resolve(r, hit[3]); common=self.lca(s,tgt)
        self.exit_to(r, start, common)
        if hit[4]: hit[4](None)
        self.enter(r, tgt)
    def dispatch(self, ev):
        for r in range(self.rcount):
            self.dispatch_region(r, ev)
    def active(self, region):
        for reg in self.regions:
            if reg['region']==region: return reg['active']
        return HSM_ID_INVALID
    def is_in(self, region, state):
        for reg in self.regions:
            if reg['region']==region:
                cur=reg['active']
                return self.is_anc(cur, state)
        return False
    def encode_active(self, region):
        a=self.active(region)
        return cw_encode(region, HSM_TOP(a), HSM_SUB(a))

# ---------- event bus mirror ----------
class Bus:
    def __init__(self, maxsub=48, maxpayload=1024, slots=4):
        self.subs=[{'active':False,'event':None,'handle':0,'handler':None,'ctx':None} for _ in range(maxsub)]
        self.count=0; self.next_handle=1
        self.pool=[[0]*maxpayload for _ in range(slots)]
        self.busy=[0]*slots
    def subscribe(self, ev, h, ctx=None):
        for i,s in enumerate(self.subs):
            if not s['active']:
                s['active']=True; s['event']=ev; s['handler']=h; s['ctx']=ctx; s['handle']=self.next_handle
                self.next_handle=(self.next_handle+1) or 1
                if self.count<i+1: self.count=i+1
                return s['handle']
        return 0xFFFF
    def unsubscribe(self, handle):
        removed=False
        for s in self.subs:
            if s['active'] and s['handle']==handle:
                s['active']=False; s['event']=None; s['handler']=None; s['ctx']=None; s['handle']=0xFFFF
                removed=True
        return removed
    def publish(self, ev, payload=None, length=0):
        if length>1024: return False
        if length>0 and payload is None: return False
        slot=None
        for i in range(len(self.busy)):
            if self.busy[i]==0: slot=i; break
        if slot is None: return False
        if length>0: self.pool[slot][:length]=list(payload[:length])
        for s in self.subs:
            if s['active'] and s['event']==ev and s['handler']:
                s['handler'](ev, s['handle'], self.pool[slot][:length] if length>0 else None, length, s['ctx'])
        self.busy[slot]=0
        return True

# ---------- ADR-006 cross-verify mirror ----------
def cross_verify(laser_mm, triggered):
    if laser_mm<0:
        return 'OBSTACLE' if triggered else 'CLEAR'
    laser_obs = laser_mm < 150
    if laser_obs==triggered:
        return 'OBSTACLE' if laser_obs else 'CLEAR'
    return 'INTERFERENCE'

# ===================== assertions =====================
fails=0; tests=0
def ok(cond, msg):
    global fails,tests; tests+=1
    if not cond: fails+=1; print("  FAIL:", msg)

# current_state
v=cw_encode(REGION_MAIN, MAIN_TRAVELING, TRAV_CRUISE)
ok(cw_decode(v)==(REGION_MAIN,MAIN_TRAVELING,TRAV_CRUISE), "cs roundtrip")
ok(v==((REGION_MAIN<<14)|(MAIN_TRAVELING<<8)|TRAV_CRUISE), "cs bitmath")
ok(cw_valid(cw_encode(REGION_SAFETY,SAFETY_ESTOP,SUB_NONE)), "cs safety valid")
ok(not cw_valid(0xFFFF), "cs uninit invalid")
ok(not cw_valid(cw_encode(3,0,0)), "cs region overflow invalid")

# HSM
e=Eng(); e.add_region(REGION_MAIN, A); e.add_region(REGION_ENERGY, E0); e.start()
ok(e.active(REGION_MAIN)==A1, "default child A1")
ok(e.active(REGION_ENERGY)==E0a, "default child E0a")
e.dispatch(EV_LOW_BATTERY)
ok(e.active(REGION_ENERGY)==E1a, "energy E0a->E1a")
e.dispatch(EV_CHARGE_DONE)
ok(e.active(REGION_ENERGY)==E0a, "history restore E0a")
e.dispatch(EV_BOOT_DONE)
ok(e.active(REGION_MAIN)==B, "main A->B")
ok(e.active(REGION_ENERGY)==E0a, "orthogonal isolation")
e.dispatch(EV_TASK_START)
ok(e.active(REGION_MAIN)==C1, "B->C default C1")
e.dispatch(EV_ARRIVED)
ok(e.active(REGION_MAIN)==C2, "C1->C2")
e.dispatch(EV_OBSTACLE_DETECTED)
ok(e.active(REGION_MAIN)==C2, "guarded false ignored")
e.dispatch(EV_NUDGE_DONE)
ok(e.active(REGION_MAIN)==C2, "self-transition stable")
cs=e.encode_active(REGION_MAIN)
ok(cw_decode(cs)==(REGION_MAIN,MAIN_TRAVELING,TRAV_CRUISE), "encode active C2")
ok(e.is_in(REGION_MAIN, C), "is_in C")
ok(not e.is_in(REGION_MAIN, B), "not is_in B")

# event bus P0-1 / P0-2
hits_a=[0]; hits_b=[0]; last_len=[0]; payload_ok=[0]
def ha(ev, hid, p, ln, ctx):
    hits_a[0]+=1; last_len[0]=ln
    if ln==1024: payload_ok[0]=1 if (p[0]==0xAA and p[1023]==0x55) else 0
def hb(ev, hid, p, ln, ctx): hits_b[0]+=1
bus=Bus()
sa=bus.subscribe(EV_LOW_BATTERY, ha); sb=bus.subscribe(EV_LOW_BATTERY, hb)
ok(sa!=0xFFFF and sb!=0xFFFF and sa!=sb, "unique handles")
bus.publish(EV_LOW_BATTERY, None, 0)
ok(hits_a[0]==1 and hits_b[0]==1, "both delivered")
ok(bus.unsubscribe(sa), "unsub sa")
bus.publish(EV_LOW_BATTERY, None, 0)
ok(hits_a[0]==1 and hits_b[0]==2, "P0-1 only sa removed")
ok(not bus.unsubscribe(sa), "double unsub no-op")
bus.subscribe(EV_LOW_BATTERY, ha)  # new handle
bus.publish(EV_LOW_BATTERY, None, 0)
ok(hits_a[0]==2 and hits_b[0]==3, "no double-deliver after resubscribe")
big=[0xAA]+[i%256 for i in range(1,1023)]+[0x55]
payload_ok[0]=0
ok(bus.publish(EV_LOW_BATTERY, big, 1024), "P0-2 1024 publish ok")
ok(last_len[0]==1024 and payload_ok[0]==1, "P0-2 1024 intact")
ok(not bus.publish(EV_LOW_BATTERY, [0]*(1025), 1025), "P0-2 >1024 rejected")

# cross_verify
ok(cross_verify(-1, True)=='OBSTACLE', "cv invalid+trig")
ok(cross_verify(-1, False)=='CLEAR', "cv invalid+clr")
ok(cross_verify(50, True)=='OBSTACLE', "cv consistent obs")
ok(cross_verify(50, False)=='INTERFERENCE', "cv anomaly")
ok(cross_verify(500, False)=='CLEAR', "cv consistent clr")
ok(cross_verify(500, True)=='INTERFERENCE', "cv anomaly2")

print(f"[validate_py] {tests} assertions, {fails} failures")
sys.exit(1 if fails else 0)
