#!/usr/bin/env python3
"""
Check the first 50 lines of metadata_scraper.py to see the class structure.
"""

with open('metadata_scraper.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=" * 60)
print("FIRST 50 LINES OF metadata_scraper.py")
print("=" * 60)

for i, line in enumerate(lines[:50], 1):
    # Show line number and indentation
    indent_level = len(line) - len(line.lstrip())
    print(f"{i:3d} [{indent_level:2d}] {line.rstrip()}")

print("\n" + "=" * 60)
