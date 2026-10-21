import runpy

ctx = runpy.run_path("tmp/inspect_home_deploy.py")
s, base, sha = ctx["session"], ctx["base"], ctx["sha"]
r = s.get(base + "/deployments", params={"sha": sha}, timeout=30)
r.raise_for_status()
for d in r.json():
    response = s.get(d["statuses_url"], timeout=30)
    response.raise_for_status()
    print(d["environment"], [(x["state"], x.get("description")) for x in response.json()[:1]])
