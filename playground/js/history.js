// history.js — undo / redo for the whole playground state.
//
// Every change records a snapshot of the state *before* it, with a short
// human label ("Load 400 → 500 N"). Rapid edits to the same field (typing,
// dragging a slider) are merged into one step, so one Ctrl+Z undoes the
// whole drag rather than every pixel of it.

export class History {
  constructor({ limit = 200, mergeMs = 900 } = {}) {
    this.past = [];
    this.future = [];
    this.limit = limit;
    this.mergeMs = mergeMs;
    this.lastKey = null;
    this.lastAt = 0;
  }

  /** Call before applying a change. `key` identifies the field being edited. */
  record(snapshot, label, key = null) {
    const now = performance.now();
    const merge = key && key === this.lastKey && now - this.lastAt < this.mergeMs && this.past.length;
    if (merge) {
      // keep the original "before" snapshot, just refresh the label's end value
      this.past[this.past.length - 1].label = mergeLabel(this.past[this.past.length - 1].label, label);
    } else {
      this.past.push({ snapshot, label });
      if (this.past.length > this.limit) this.past.shift();
    }
    this.future.length = 0;
    this.lastKey = key;
    this.lastAt = now;
  }

  /** Break merging, e.g. after a pause or when focus leaves a field. */
  seal() { this.lastKey = null; }

  undo(current) {
    const step = this.past.pop();
    if (!step) return null;
    this.future.push({ snapshot: current, label: step.label });
    this.seal();
    return step;
  }

  redo(current) {
    const step = this.future.pop();
    if (!step) return null;
    this.past.push({ snapshot: current, label: step.label });
    this.seal();
    return step;
  }

  get canUndo() { return this.past.length > 0; }
  get canRedo() { return this.future.length > 0; }
}

// "Load 400 → 450 N" + "Load 450 → 520 N"  =>  "Load 400 → 520 N"
function mergeLabel(first, next) {
  const a = first.split(" → "), b = next.split(" → ");
  return a.length === 2 && b.length === 2 ? `${a[0]} → ${b[1]}` : next;
}
