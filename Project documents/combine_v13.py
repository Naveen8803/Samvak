"""
combine_v13.py — Master builder: runs all parts in a SHARED namespace.
Usage: python "E:\sam\Project documents\combine_v13.py"
"""
import os, sys

BASE = r"E:\sam\Project documents"

def load(filename):
    path = os.path.join(BASE, filename)
    with open(path, encoding="utf-8") as f:
        return compile(f.read(), path, "exec")

# All parts share ONE namespace so doc/helpers defined in p1 are visible in p2-p4
ns = {"__file__": os.path.join(BASE, "combine_v13.py")}

print("=" * 60)
print("Samvak Review Document Builder V13")
print("=" * 60)

print("\n[1/4] Front Matter + Chapters 1-4 ...")
exec(load("build_final_v13.py"), ns)

print("\n[2/4] Chapter 5 - System Design + Diagrams ...")
exec(load("build_final_v13_p2.py"), ns)

print("\n[3/4] Chapter 6 - Code & Implementation ...")
exec(load("build_final_v13_p3.py"), ns)

print("\n[4/4] Chapters 7-10 - Testing, Conclusion, Future, References ...")
exec(load("build_final_v13_p4.py"), ns)

print("\nDone!")
