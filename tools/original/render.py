#!/usr/bin/env python3
"""MONO / INVADERS — independent SVG contribution arcade."""
import argparse
import datetime as dt
import math
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# The original MONO / INVADERS calendar client, not the REMAKE engine.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_invaders import get_calendar, parse, sample

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
WIDTH, HEIGHT = 904, 278
GRID_X, GRID_Y, STEP, CELL = 28, 69, 16, 12
SHIP_Y, FOOTER_Y = 190, 239
LEFT, RIGHT = 24, WIDTH - 24
DEFAULT_SPEED = 220.0
BULLET_SPEED = 420.0
COLORS = {"NONE":"#292929","FIRST_QUARTILE":"#666666",
          "SECOND_QUARTILE":"#999999","THIRD_QUARTILE":"#c0c0c0",
          "FOURTH_QUARTILE":"#f1f1f1"}

def node(parent, tag, **attrs):
    return ET.SubElement(parent, "{"+NS+"}"+tag,
                         {k.replace("_","-"):str(v) for k,v in attrs.items()})

def text(parent, x, y, content, size=11, color="#a9a9a9", **attrs):
    e = node(parent,"text",x=x,y=y,font_size=size,fill=color,
             font_family="monospace",**attrs)
    e.text = str(content)
    return e

def clock(parent, tag, attr, values, times, duration, mode="linear", **attrs):
    if len(values)!=len(times) or times[0]!=0 or times[-1]!=duration:
        raise ValueError("Invalid timeline endpoints")
    if any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError("Timeline must be strictly increasing")
    return node(parent,tag,attributeName=attr,values=";".join(map(str,values)),
                keyTimes=";".join(f"{t/duration:.9f}" for t in times),
                dur=f"{duration:.6f}s",repeatCount="indefinite",calcMode=mode,**attrs)

def visible(parent, start, end, duration):
    if not 0<=start<end<=duration: raise ValueError("Invalid visibility window")
    times=[0.0]; values=[1 if start==0 else 0]
    if start>0: times.append(start); values.append(1)
    if end<duration: times.append(end); values.append(0)
    times.append(duration); values.append(values[-1])
    parent.set("opacity",str(values[0]))
    if len(times)>2: clock(parent,"animate","opacity",values,times,duration,"discrete")

def calendar_data(calendar):
    days,ncols=parse(calendar)
    # Rolling GitHub calendars may include partial boundary weeks.
    start=max(0,ncols-53); offset=max(0,53-ncols)
    return [(c-start+offset,r,d,count,level) for c,r,d,count,level in days if c>=start]

def render(calendar, speed=DEFAULT_SPEED, demo=False):
    if not math.isfinite(speed) or not 120<=speed<=300:
        raise ValueError("Speed must be between 120 and 300 px/s")
    days=calendar_data(calendar)
    active=[d for d in days if d[3]>0]
    half=(RIGHT-LEFT)/speed
    duration=2*half
    root=ET.Element("{"+NS+"}svg",{"viewBox":f"0 0 {WIDTH} {HEIGHT}",
        "width":str(WIDTH),"height":str(HEIGHT),"role":"img",
        "aria-labelledby":"title desc"})
    node(root,"title",id="title").text="MONO / INVADERS — Contribution Arcade"
    total=sum(d[3] for d in active)
    node(root,"desc",id="desc").text=("Demo data. " if demo else "GitHub contribution calendar. ")+f"{len(active)} active days, {total} contributions. Continuous sweep with synchronized projectiles."
    # Retro arcade presentation: static vector art only.
    node(root,"rect",x=0.5,y=0.5,width=WIDTH-1,height=HEIGHT-1,rx=10,fill="#090909",stroke="#454545")
    node(root,"path",id="retro-frame",d="M18 5H886L899 18V260L886 273H18L5 260V18Z",fill="none",stroke="#bdbdbd",stroke_width=1.5)
    node(root,"path",d="M20 10H884L894 20V258L884 268H20L10 258V20Z",fill="none",stroke="#555",stroke_width=1)
    node(root,"path",d="M9 36V18L18 9H40 M864 9H886L895 18V36 M9 242V260L18 269H40 M864 269H886L895 260V242",fill="none",stroke="#ededed",stroke_width=2)
    # Hand-built bitmap lettering, independent of installed fonts.
    glyphs={
        "M":["10001","11011","10101","10101","10001","10001","10001"],
        "O":["01110","10001","10001","10001","10001","10001","01110"],
        "N":["10001","11001","10101","10011","10001","10001","10001"],
        "I":["11111","00100","00100","00100","00100","00100","11111"],
        "V":["10001","10001","10001","10001","10001","01010","00100"],
        "A":["01110","10001","10001","11111","10001","10001","10001"],
        "D":["11110","10001","10001","10001","10001","10001","11110"],
        "E":["11111","10000","10000","11110","10000","10000","11111"],
        "R":["11110","10001","10001","11110","10100","10010","10001"],
        "S":["01111","10000","10000","01110","00001","00001","11110"],
        "/":["00001","00001","00010","00100","01000","10000","10000"],
        " ":["00000"]*7,
    }
    title="MONO / INVADERS"
    unit=3; advance=6*unit
    title_x=(WIDTH-(len(title)*advance-unit))/2
    pixels=[]
    for i,ch in enumerate(title):
        for row,line in enumerate(glyphs[ch]):
            for col,pixel in enumerate(line):
                if pixel=="1":
                    px=title_x+i*advance+col*unit; py=15+row*unit
                    pixels.append(f"M{px} {py}h{unit}v{unit}h-{unit}z")
    node(root,"path",id="retro-title",d=" ".join(pixels),fill="#f1f1f1")
    # Mirrored invader badges and speed lines evoke a classic arcade marquee.
    invader="M-5 -5h2v2h6v-2h2v3h2v3h2v5h-3v-3h-2v4h-3v-2h-2v2h-3v-4h-2v3h-3v-5h2v-3h2z"
    node(root,"path",id="mono-emblem",d=invader,transform="translate(78 25) scale(1.5)",fill="#e5e5e5")
    node(root,"path",d=invader,transform="translate(826 25) scale(1.5)",fill="#e5e5e5")
    for px in (78,826):
        node(root,"path",d="M-4 0h2v2h-2z M2 0h2v2h-2z",transform=f"translate({px} 25) scale(1.5)",fill="#111")
    node(root,"path",d="M105 20H300 M105 25H287 M105 30H274 M604 20H799 M617 25H799 M630 30H799",stroke="#777",stroke_width=1,fill="none")
    node(root,"path",d="M22 43H882",stroke="#555",fill="none")
    # Contribution field keeps its actual calendar geometry.
    node(root,"path",d="M26 64H878L884 70V176L878 182H26L20 176V70Z",fill="#101010",stroke="#555",stroke_width=1)
    # Static lunar silhouettes and sparse stars, confined to the playfield.
    node(root,"path",id="retro-landscape",d="M20 231V217L35 208L49 193L59 198L70 211L85 205L100 216L115 211L129 221L143 216L170 231Z M884 231V219L870 209L851 193L837 204L828 216L811 208L799 220L783 213L766 224L750 219L731 231Z",fill="#191919")
    node(root,"path",d="M20 231V217L35 208L49 193L59 198L70 211L85 205L100 216L115 211L129 221L143 216L170 231 M884 219L870 209L851 193L837 204L828 216L811 208L799 220L783 213L766 224L750 219L731 231",stroke="#585858",stroke_width=1,fill="none")
    node(root,"path",d="M49 193L44 211L62 219 M85 205L91 216 M851 193L858 211L840 221 M811 208L802 221",stroke="#333",fill="none")
    stars=[]
    for px,py in ((190,196),(241,212),(294,188),(342,221),(390,201),(448,187),(506,216),(557,192),(607,224),(655,202),(708,188),(780,197),(112,190)):
        stars.append(f"M{px-2} {py}h4v1h-4z M{px} {py-2}h1v5h-1z")
    node(root,"path",d=" ".join(stars),fill="#777")
    node(root,"path",d="M24 232H880",stroke="#777",stroke_dasharray="2 4",fill="none")
    # Classic arcade HUD with angular score and statistics panels.
    node(root,"path",d="M21 239H211L223 255L211 267H21L12 255Z M625 239H883L892 255L883 267H625L613 255Z",fill="#121212",stroke="#888")
    node(root,"path",d="M228 250H365 M228 255H365 M539 250H608 M539 255H608",stroke="#555",fill="none")
    x=lambda c:GRID_X+c*STEP
    y=lambda r:GRID_Y+r*STEP
    cx=lambda c:x(c)+CELL/2
    # One static path for the entire grid; rounded cells maintain the visual rhythm.
    grid=[]
    for c in range(53):
        for r in range(7):
            a,b=x(c),y(r)
            grid.append(f"M{a+2} {b}h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2v-8a2 2 0 0 1 2 -2z")
    node(root,"path",id="calendar-grid",d=" ".join(grid),fill=COLORS["NONE"])
    last_month=None; last_col=-10
    for c,r,date,count,level in days:
        key=(date.year,date.month)
        if key!=last_month and c-last_col>=2:
            text(root,x(c),58,date.strftime("%b").upper(),10,"#d0d0d0")
            last_month=key; last_col=c
    # A projectile launches exactly as the ship crosses each occupied column.
    # It moves independently after launch, so the ship never waits for impact.
    hits={}
    for c in sorted({d[0] for d in active}):
        launch=(cx(c)-LEFT)/speed
        targets=[d for d in active if d[0]==c]
        top=min(y(d[1])+6 for d in targets)
        for _,r,_,count,level in targets:
            impact=launch+(SHIP_Y-(y(r)+6))/BULLET_SPEED
            hits[c,r]=impact
            tile=node(root,"g",transform=f"translate({cx(c)} {y(r)+6})")
            node(tile,"rect",x=-6,y=-6,width=12,height=12,rx=2,fill=COLORS[level])
            # Nine-by-seven original bitmap sprite, with distinct eyes and legs.
            sprite=("010000010","001000100","011111110","110111011",
                    "111111111","101111101","001000100")
            pixels=[]
            for row,line in enumerate(sprite):
                for col,pixel in enumerate(line):
                    if pixel=="1":
                        pixels.append(f"M{col-4.5} {row-3.5}h1v1h-1z")
            node(tile,"path",id=f"enemy-{c}-{r}",d=" ".join(pixels),
                 fill="#151515" if level in ("THIRD_QUARTILE","FOURTH_QUARTILE") else "#f1f1f1")
            # Two tiny edge highlights make the enemy cell read as an arcade tile.
            node(tile,"path",d="M-5 -4V-5H-3 M3 5H5V3",fill="none",
                 stroke="#fff",stroke_opacity=".35",stroke_width=".6")
            visible(tile,0,impact,duration)
            # Compact, fading pixel fragments; not a filter or an external resource.
            blast=node(root,"g",transform=f"translate({cx(c)} {y(r)+6})")
            # One impact group: white core, branching pixel lightning and debris.
            node(blast,"path",d="M-2 -2h4v4h-4z M-1 -10h2v5h-2z M-1 5h2v5h-2z M-10 -1h5v2h-5z M5 -1h5v2h-5z",fill="#fff")
            node(blast,"path",d="M-3 -3L-7 -6H-5L-9 -10 M3 -3L7 -6H5L9 -10 M-3 3L-7 6H-5L-9 10 M3 3L7 6H5L9 10",stroke="#aaa",stroke_width="1.2",fill="none")
            node(blast,"path",d="M-9 -6h2v2h-2z M7 4h2v2h-2z M-6 8h2v2h-2z M6 -9h2v2h-2z",fill="#e5e5e5")
            end=impact+0.18
            clock(blast,"animate","opacity",[0,0,1,.55,0,0],[0,impact-0.001,impact,impact+0.055,end,duration],duration)
        end=launch+(SHIP_Y-top)/BULLET_SPEED
        bolt=node(root,"g",opacity=0)
        # A layered pulse with a sharp white core and stepped ion trail.
        bx=cx(c)
        node(bolt,"path",d=f"M{bx-4} 1h2v-6h4v6h2v9h-2v5h-4v-5h-2z",fill="#555")
        node(bolt,"path",d=f"M{bx-1.5} -7h3v14h-3z M{bx-.5} 7h1v9h-1z",fill="#fff")
        node(bolt,"path",d=f"M{bx-5} 4h2v4h-2z M{bx+3} 4h2v4h-2z M{bx-2} 19h1v3h-1z M{bx+1} 19h1v3h-1z",fill="#aaa")
        # Muzzle lightning is a single short-lived static shape, synchronized to launch.
        flash=node(root,"g",transform=f"translate({bx} {SHIP_Y})",opacity=0)
        node(flash,"path",d="M-2 -3H2V-9H4L0 -15L-4 -9H-2Z M-5 -2L-10 -7H-6L-8 -12 M5 -2L10 -7H6L8 -12",fill="#eee",stroke="#eee",stroke_width=".5")
        clock(flash,"animate","opacity",[0,0,1,0,0],[0,launch-0.001,launch,launch+0.045,duration],duration)
        visible(bolt,launch,end+0.008,duration)
        clock(bolt,"animateTransform","transform",[f"0 {SHIP_Y}",f"0 {SHIP_Y}",f"0 {top}",f"0 {top}"],
              [0,launch,end,duration],duration,type="translate")
    # Original pixel fighter: broad wings, stepped hull and twin thrusters.
    ship=node(root,"g",id="player-ship",transform=f"translate({LEFT} 0)")
    node(ship,"path",id="fighter-hull",d="M-3 190H3V195H6V200H9V205H13V201H17V196H21V216H17V221H11V217H6V223H-6V217H-11V221H-17V216H-21V196H-17V201H-13V205H-9V200H-6V195H-3Z",fill="#eeeeee")
    node(ship,"path",d="M-21 201H-17V211H-13V217H-17V216H-21Z M21 201H17V211H13V217H17V216H21Z M-3 190H0V200H-3Z",fill="#929292")
    node(ship,"path",d="M-3 199H3V203H5V212H-5V203H-3Z",fill="#333")
    node(ship,"rect",x=-2,y=202,width=4,height=5,fill="#bcbcbc")
    node(ship,"path",d="M-12 220h4v5h-4z M8 220h4v5h-4z",fill="#aaa")
    clock(ship,"animateTransform","transform",[f"{LEFT} 0",f"{RIGHT} 0",f"{LEFT} 0"],
          [0,half,duration],duration,type="translate")
    # Real contribution count, not health or fabricated game points.
    events={}
    for c,r,_,count,_ in active: events[hits[c,r]]=events.get(hits[c,r],0)+count
    times=[0]+sorted(events)+[duration]; points=0
    for i in range(len(times)-1):
        points+=events.get(times[i],0)
        counter=text(root,28,260,f"SCORE {points:04d}",15,"#ededed",font_weight="bold",letter_spacing=".5")
        visible(counter,times[i],times[i+1],duration)
    text(root,WIDTH-28,260,f"{len(active)} ACTIVE DAYS / {total} CONTRIBUTIONS",10,"#d0d0d0",text_anchor="end")
    legend=node(root,"g",id="activity-legend")
    text(legend,WIDTH/2-48,261,"LOW",9,"#a9a9a9",text_anchor="end")
    for i, color in enumerate(COLORS.values()):
        node(legend,"rect",x=WIDTH/2-38+i*14,y=251,width=10,height=10,rx=2,fill=color)
    text(legend,WIDTH/2+39,261,"HIGH",9,"#a9a9a9")
    return ET.tostring(root,encoding="unicode")+"\n"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--speed",type=float,default=DEFAULT_SPEED)
    p.add_argument("--demo",action="store_true")
    p.add_argument("--login",default="matheuscgxlina")
    a=p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})",a.login): p.error("Invalid login")
    svg=render(sample() if a.demo else get_calendar(a.login),a.speed,a.demo)
    ET.fromstring(svg)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=a.output.parent,delete=False) as f:
        f.write(svg); tmp=Path(f.name)
    try: os.replace(tmp,a.output)
    finally: tmp.unlink(missing_ok=True)
    print("Generated independent MONO / INVADERS SVG.")

if __name__=="__main__": main()
