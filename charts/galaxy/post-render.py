#!/usr/bin/env python3
"""Helm post-renderer: úprava manifestů galaxy-helm, aby prošly PodSecurity "restricted".

Chart nastavuje bezpečnostní kontext jen na úrovni podu a bez
allowPrivilegeEscalation / capabilities / seccompProfile / runAsNonRoot.
Init kontejner `*-wait-postgres` je navíc natvrdo root a dělá chown.

Použití:  helm ... --post-renderer python3 --post-renderer-args charts/galaxy/post-render.py
Čte manifesty ze stdin, zapisuje upravené na stdout. Vyžaduje PyYAML.
"""
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


def fix_pod(ps):
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
            if csc.get("runAsUser") == 0:
                csc["runAsUser"] = UID
            if csc.get("runAsGroup") == 0:
                csc["runAsGroup"] = UID
            # wait-postgres dělal chown jako root; bez rootu to nejde a oprávnění řeší fsGroup
            if str(c.get("name", "")).endswith("-wait-postgres"):
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
            fix_pod(ps)
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False, default_flow_style=False, width=1000000)


if __name__ == "__main__":
    main()
