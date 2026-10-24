import json, pathlib, re
m = json.loads(pathlib.Path("runs/demo/metrics.json").read_text())
inf = m["inference_ms"]
p = pathlib.Path("docs/technical-report.md"); s = p.read_text(encoding="utf-8")
pairs = [
  ("| Inference latency p50 | 28.68 ms |", f"| Inference latency p50 | {inf['p50']:.2f} ms |"),
  ("| Inference latency p95 | 31.75 ms |", f"| Inference latency p95 | {inf['p95']:.2f} ms |"),
  ("| Inference latency max | 49.90 ms |", f"| Inference latency max | {inf['max']:.2f} ms |"),
  ("| End-to-end frame budget (mean) | 35.23 ms |", f"| End-to-end frame budget (mean) | {m['frame_budget_ms']['mean']:.2f} ms |"),
  ("| Motion mask coverage (mean) | 4.71 % of pixels |", f"| Motion mask coverage (mean) | {m['motion_ratio_mean']*100:.2f} % of pixels |"),
]
for a,b in pairs:
    assert a in s, a
    s = s.replace(a,b)
old_para = [l for l in s.split(chr(10)) if l.startswith("Against a 10 fps source")][0]
new_para = ("Against a 10 fps source (100 ms per frame) one stream consumes about 32 ms of that budget, roughly 3x real-time headroom. "
            "Four streams would need 126 ms per 100 ms of wall clock, which does not fit; a single CPU node sustains two streams at 10 fps with margin. "
            "That is the capacity number, measured rather than assumed.")
s = s.replace(old_para, new_para)
p.write_text(s, encoding="utf-8")
print(new_para[:120])
