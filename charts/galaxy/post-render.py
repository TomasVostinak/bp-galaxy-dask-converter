import re
import sys

import yaml

UID = 10001  # musí odpovídat securityContext.runAsUser v values.yaml a UID v image

def pod_spec(doc):
    kind = doc.get("kind")
    spec = doc.get("spec") or {}
    if kind == "Pod":
        return spec
    if kind == "CronJob":
        return (((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec")
    if kind in ("Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet"):
        return (spec.get("template") or {}).get("spec")
    return None

def add_default_resources(c, is_job):
    if c.get("resources"):
        return
    if is_job:
        c["resources"] = {"requests": {"cpu": "100m", "memory": "256Mi"},
                          "limits": {"cpu": "1", "memory": "1Gi"}}
    else:
        c["resources"] = {"requests": {"cpu": "25m", "memory": "64Mi"},
                          "limits": {"cpu": "500m", "memory": "256Mi"}}

def fix_nginx(ps, c):
    vols = ps.setdefault("volumes", [])
    for name in ("nginx-cache", "nginx-run"):
        if not any(v.get("name") == name for v in vols):
            vols.append({"name": name, "emptyDir": {}})
    mounts = c.setdefault("volumeMounts", [])
    for name, path in (("nginx-cache", "/var/cache/nginx"), ("nginx-run", "/var/run")):
        if not any(m.get("mountPath") == path for m in mounts):
            mounts.append({"name": name, "mountPath": path})

def fix_pod(ps, is_job):
    sc = ps.setdefault("securityContext", {}) or {}
    ps["securityContext"] = sc
    sc["runAsNonRoot"] = True
    sc["seccompProfile"] = {"type": "RuntimeDefault"}
    if not sc.get("runAsUser"):          # chybí nebo 0
        sc["runAsUser"] = UID
    if not sc.get("runAsGroup"):
        sc["runAsGroup"] = UID

    for key in ("initContainers", "containers"):
        for c in ps.get(key) or []:
            csc = c.get("securityContext") or {}
            c["securityContext"] = csc
            csc["allowPrivilegeEscalation"] = False
            csc["capabilities"] = {"drop": ["ALL"]}
            csc["runAsNonRoot"] = True
            if csc.get("runAsUser") in (None, 0):
                # kubelet jinak u image s nenumerickým uživatelem (tusd) nepozná, že není root
                csc["runAsUser"] = sc["runAsUser"]
            if csc.get("runAsGroup") == 0:
                csc["runAsGroup"] = UID
            add_default_resources(c, is_job)
            name = str(c.get("name", ""))
            if name.endswith("-nginx") and str(c.get("image", "")).startswith("nginx"):
                fix_nginx(ps, c)
            # wait-postgres dělal chown jako root; bez rootu to nejde a oprávnění řeší fsGroup
            if name.endswith("-wait-postgres"):
                cmd = c.get("command")
                if isinstance(cmd, list):
                    c["command"] = [
                        re.sub(r"(?m)^\s*chown .*\n?", "", part) if isinstance(part, str) else part
                        for part in cmd
                    ]

def main():
    docs = [d for d in yaml.safe_load_all(sys.stdin.read()) if d]
    for d in docs:
        ps = pod_spec(d)
        if ps is not None:
            fix_pod(ps, d.get("kind") in ("Job", "CronJob"))
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False, default_flow_style=False, width=1000000)

if __name__ == "__main__":
    main()
