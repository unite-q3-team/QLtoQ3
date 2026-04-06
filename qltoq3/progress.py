"""tqdm coworker slots + pool shutdown."""

import sys
import threading

from tqdm import tqdm

from .colors import Colors
from .l10n import tr


def format_elapsed(sec: float) -> str:
    s = int(max(0, sec))
    h, r = divmod(s, 3600)
    m, s2 = divmod(r, 60)
    if h:
        return f"{h}:{m:02d}:{s2:02d}"
    return f"{m}:{s2:02d}"


LOG_LOCK = threading.RLock()
THREAD_LOCAL = threading.local()
POS_COUNTER = 0
SLOT_CAP = 96


class BspcWait:
    __slots__ = ("_lock", "_n", "_pbar")

    def __init__(self, main_pbar):
        self._lock = threading.Lock()
        self._n = 0
        self._pbar = main_pbar

    def inc(self):
        with self._lock:
            self._n += 1
            self._touch()

    def dec(self):
        with self._lock:
            self._n = max(0, self._n - 1)
            self._touch()

    def _touch(self):
        if not self._pbar:
            return
        with tqdm.get_lock():
            self._pbar.set_postfix_str(tr("prog.bspc_queue", n=self._n))
            self._pbar.refresh()


def set_slot_cap(n: int) -> None:
    global SLOT_CAP
    SLOT_CAP = max(1, min(512, int(n)))


def reset_pos_counter() -> None:
    global POS_COUNTER
    with LOG_LOCK:
        POS_COUNTER = 0


def get_thread_pos():
    global POS_COUNTER
    if not hasattr(THREAD_LOCAL, "pos"):
        with LOG_LOCK:
            POS_COUNTER += 1
            THREAD_LOCAL.pos = ((POS_COUNTER - 1) % SLOT_CAP) + 1
    return THREAD_LOCAL.pos


PHASE_MAP_W = 22

WORKER_BAR_FMT = "{desc} | {n_fmt}/{total_fmt} |{bar:9}| {percentage:3.0f}% {postfix}"


def set_worker_state(slot_pbars, pos, state):
    del slot_pbars, pos, state


def slot_bars(num_slots, disable=False):
    slots = {}
    for pos in range(num_slots, 0, -1):
        slots[pos] = tqdm(
            total=1,
            initial=1,
            desc=f"  {Colors.DARK_GRAY}{tr('prog.coworker_idle', n=pos)}{Colors.ENDC}",
            bar_format="{desc}",
            position=pos,
            leave=True,
            mininterval=0.15,
            file=sys.stdout,
            disable=disable,
        )
    return slots


def slot_idle(inner, position, slot_pbars=None):
    inner.reset(total=1)
    inner.n = 1
    inner.bar_format = "{desc}"
    inner.set_description_str(
        f"  {Colors.DARK_GRAY}{tr('prog.coworker_idle', n=position)}{Colors.ENDC}"
    )
    inner.set_postfix_str("")
    inner.refresh()
    if slot_pbars is not None:
        set_worker_state(slot_pbars, position, "idle")


def pool_x(executor):
    if executor is None:
        return
    kw = {"wait": False}
    if sys.version_info >= (3, 9):
        kw["cancel_futures"] = True
    try:
        executor.shutdown(**kw)
    except Exception:
        pass


def close_bars(slot_pbars, pbar, num_workers):
    for _pos in range(num_workers, 0, -1):
        try:
            slot_pbars[_pos].close()
        except Exception:
            pass
    try:
        pbar.close()
    except Exception:
        pass
