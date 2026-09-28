#!/usr/bin/env python3
"""Local product preview with byte ranges for reliable video seeking."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        rel = unquote(urlsplit(self.path).path).lstrip('/') or 'workbench.html'
        root = Path(self.directory).resolve()
        path = (root/rel).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            self.send_error(404)
            return None
        size = path.stat().st_size
        begin, end, status = 0, size - 1, 200
        header = self.headers.get('Range')
        if header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
            try:
                if not match or not any(match.groups()):
                    raise ValueError
                left,right = match.groups()
                if left:
                    begin=int(left);end=min(int(right),end) if right else end
                else:
                    suffix=int(right)
                    if suffix<=0:raise ValueError
                    begin=max(0,size-suffix)
                if begin>end or begin>=size:raise ValueError
                status=206
            except ValueError:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers()
                return None
        stream=path.open('rb')
        stream.seek(begin)
        self.send_response(status)
        self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Content-Length',str(max(0,end-begin+1)))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Cache-Control','no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        if status==206:self.send_header('Content-Range',f'bytes {begin}-{end}/{size}')
        self.end_headers()
        self.remaining=max(0,end-begin+1)
        return stream

    def copyfile(self,source,outputfile):
        try:
            remaining=self.remaining
            while remaining:
                block=source.read(min(256*1024,remaining))
                if not block:break
                outputfile.write(block);remaining-=len(block)
        except (BrokenPipeError,ConnectionResetError):
            pass


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=18766)
    p.add_argument('--directory',default=str(Path(__file__).resolve().parents[1]/'frontend'))
    args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=args.directory))
    print(f'http://127.0.0.1:{args.port}/workbench.html',flush=True)
    server.serve_forever()
