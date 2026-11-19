#!/usr/bin/env python3
"""previewserv.py — the site-preview static server (used by sfh-stagger on).

python -m http.server with one addition: Cache-Control: no-store on every
response. A preview door must be uncacheable — during a build session the
same URL is 404, then a file, then new bytes, and a browser that caches the
failure (Safari does) keeps serving the past. The production site gets its
caching from the real front (GitHub Pages); the rehearsal room gets none.

Usage: previewserv.py PORT [--bind ADDR] [--directory DIR]
"""
import argparse, http.server, os, sys

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", type=int)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--directory", default=os.getcwd())
    a = ap.parse_args()
    os.chdir(a.directory)
    http.server.ThreadingHTTPServer((a.bind, a.port), Handler).serve_forever()

if __name__ == "__main__":
    main()
