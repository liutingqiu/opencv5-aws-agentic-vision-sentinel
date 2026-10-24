import shutil, pathlib, os

src = pathlib.Path("D:/zaku-new/tmp/ox5")
out = pathlib.Path("D:/zaku-new/tmp/pkg")
if out.exists():
    shutil.rmtree(out)
root = out / "opencv5-sentinel"
root.mkdir(parents=True, exist_ok=True)
for name in ["sentinel", "scripts", "tests", "docs", "data", "README.md", "requirements.txt", "index.html", ".gitignore"]:
    s = src / name
    if s.is_dir():
        shutil.copytree(s, root / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    elif s.exists():
        shutil.copy2(s, root / name)
for junk in ["docs/demo.mp4", "docs/technical-report.html", "data/dispatches.json"]:
    p = root / junk
    if p.exists():
        p.unlink()
zip_path = shutil.make_archive("D:/zaku-new/tmp/opencv5-sentinel-src", "zip", out)
print(zip_path, os.path.getsize(zip_path))
