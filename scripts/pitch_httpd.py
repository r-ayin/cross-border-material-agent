#!/usr/bin/env python3
"""Range-capable threaded static server for pitch pages (Safari/players need 206)."""
import http.server, os, re, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ALIASES = {
    '/assets/run-20260928/product_video_v7_T01_bedroom.mp4': '/assets/run-20260928/product_video_v7_15s_clean.mp4',
    '/assets/run-20260928/product_video_dance15_tier1.mp4': '/assets/run-20260928/product_video_v7_15s_clean.mp4',
}

class RangeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        p = self.translate_path(self.path)
        rel = '/' + self.path.lstrip('/')
        for old, new in ALIASES.items():
            if rel.split('?')[0] == old:
                self.send_response(301)
                self.send_header('Location', new.rsplit('/', 1)[-1])
                self.send_header('Content-Length', '0')
                self.end_headers()
                return None
        if False: pass
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, 'not found')
            return None
        size = os.fstat(f.fileno()).st_size
        m = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range') or '')
        if not m or (m.group(1) == '' and m.group(2) == ''):
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(path))
            self.send_header('Content-Length', str(size))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            return f
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
        end = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
        if start > end or start >= size:
            f.close()
            self.send_error(416, 'range not satisfiable')
            return None
        f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        return f

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, *a):
        pass

if __name__ == '__main__':
    port = int(sys.argv[1]); directory = sys.argv[2]
    os.chdir(directory)
    ThreadingHTTPServer(('0.0.0.0', port), RangeHandler).serve_forever()
