import pathlib, json
m = json.loads(pathlib.Path("runs/demo/metrics.json").read_text())
inf = m["inference_ms"]
rep = {
  "inference p50 28.7 ms / p95 31.8 ms": f"inference p50 {inf['p50']:.1f} ms / p95 {inf['p95']:.1f} ms",
}
p = pathlib.Path("docs/architecture.svg"); s = p.read_text(encoding="utf-8")
for a,b in rep.items(): s = s.replace(a,b)
p.write_text(s, encoding="utf-8")
print("svg updated:", rep)
