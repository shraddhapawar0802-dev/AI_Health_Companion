import re
import subprocess
import tempfile
import os

with open("templates/index.html", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r"<script(?:\s+[^>]*)?>(.*?)</script>", html, flags=re.DOTALL)
print(f"Found {len(scripts)} script tags in index.html.")

all_valid = True
for idx, script in enumerate(scripts):
    # skip external scripts or empty ones
    if not script.strip():
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(script)
        tmp_name = tmp.name
    try:
        res = subprocess.run(["node", "--check", tmp_name], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Script tag {idx+1} has SYNTAX ERROR:")
            print(res.stderr)
            all_valid = False
        else:
            print(f"Script tag {idx+1} syntax is 100% CLEAN.")
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

if all_valid:
    print("\nALL JAVASCRIPT SYNTAX IN INDEX.HTML IS 100% VALID AND CLEAN!")
