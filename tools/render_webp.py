#!/usr/bin/env python3
"""Render the generated MONO / INVADERS SVG as animated WebP."""
import argparse
import bisect
import io
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import cairosvg
from PIL import Image
NS = '{http://www.w3.org/2000/svg}'
ET.register_namespace('', NS[1:-1])
FPS = 60

def convert(svg, output):
    root = ET.fromstring(svg)
    tracks, durations = [], set()
    for node in list(root.iter()):
        for anim in list(node):
            if anim.tag not in (NS+'animate', NS+'animateTransform'):
                continue
            a = anim.attrib
            durations.add(float(a['dur'].removesuffix('s')))
            key = a['attributeName']
            times = [float(t) for t in a['keyTimes'].split(';')]
            values = [tuple(map(float,v.split())) for v in a['values'].split(';')]
            mode = a.get('calcMode','linear')
            transform = anim.tag == NS+'animateTransform'
            if (len(times)!=len(values) or times[0]!=0 or times[-1]!=1 or any(b<c for c,b in zip(times,times[1:])) or mode not in ('linear','discrete') or key not in ('opacity','transform') or (transform and a.get('type')!='translate')):
                raise ValueError('Unsupported animation track')
            tracks.append((node,key,times,values,mode,transform))
            node.remove(anim)
    if len(durations)!=1:
        raise ValueError('Expected one shared animation duration')
    duration=durations.pop()
    if not 0<duration<=120:
        raise ValueError('Unexpected animation duration')
    w,h=int(root.attrib['width']),int(root.attrib['height'])
    frames=round(duration*FPS)
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        target=Path(tmp)/'animation.webp'
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}','-framerate',str(FPS),'-i','pipe:0','-an','-c:v','libwebp_anim','-lossless','1','-compression_level','3','-loop','0','-y',str(target)]
        with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
            try:
                for frame in range(frames):
                    fraction=frame/frames
                    for node,key,times,values,mode,transform in tracks:
                        i=max(0,min(len(times)-1,bisect.bisect_right(times,fraction)-1))
                        v=values[i]
                        if mode=='linear' and i+1<len(times) and times[i+1]>times[i]:
                            u=(fraction-times[i])/(times[i+1]-times[i]); v=tuple(a+(b-a)*u for a,b in zip(v,values[i+1]))
                        node.set(key,'translate('+' '.join(f'{x:.6f}' for x in v)+')' if transform else f'{v[0]:.6f}')
                    png=cairosvg.svg2png(bytestring=ET.tostring(root))
                    with Image.open(io.BytesIO(png)) as im:
                        rgba=im.convert('RGBA'); bg=Image.new('RGB',rgba.size,'#101010'); bg.paste(rgba,mask=rgba.getchannel('A')); proc.stdin.write(bg.tobytes())
                proc.stdin.close()
                if proc.wait()!=0: raise RuntimeError('WebP encoder failed')
            except BaseException:
                proc.kill(); proc.wait(); raise
        with Image.open(target) as im:
            if im.size!=(w,h) or not im.is_animated or im.info.get('loop')!=0: raise ValueError('Invalid animated WebP')
            elapsed=0
            for i in range(im.n_frames):
                im.seek(i); im.load(); elapsed+=im.info.get('duration',0)
            if abs(elapsed/1000-duration)>.10: raise ValueError(f'Unexpected duration: {elapsed}ms vs {duration}s')
            print(f'WebP: {im.n_frames} frames, {elapsed} ms, {target.stat().st_size} bytes')
        target.replace(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); convert(a.input.read_text(),a.output)
