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
    node(root,"rect",x=0.5,y=0.5,width=WIDTH-1,height=HEIGHT-1,rx=12,fill="#101010",stroke="#454545")
    # Static, restrained instrument-panel styling. No additional animation tracks.
    node(root,"rect",x=12,y=10,width=WIDTH-24,height=28,rx=5,fill="#181818")
    node(root,"rect",x=22,y=17,width=3,height=14,fill="#ededed")
    node(root,"rect",x=20,y=45,width=WIDTH-40,height=138,rx=6,fill="#141414",stroke="#252525")
    node(root,"rect",x=20,y=185,width=WIDTH-40,height=46,rx=6,fill="#121212",stroke="#252525")
    node(root,"rect",x=12,y=244,width=WIDTH-24,height=25,rx=5,fill="#181818")
    text(root,33,29,"MONO / INVADERS",17,"#f1f1f1",font_weight="bold")
    text(root,WIDTH-24,28,"DEMO / SAMPLE DATA" if demo else "CONTRIBUTION ARCADE",10,"#bcbcbc",text_anchor="end")
    node(root,"path",d=f"M22 40 H{WIDTH-22} M22 {FOOTER_Y} H{WIDTH-22}",stroke="#353535",fill="none")
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
            text(root,x(c),59,date.strftime("%b").upper(),10,"#a0a0a0")
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
            node(tile,"path",d="M-4 -4H-3V-2H3V-4H4V-1H5V3H3V5H1V3H-1V5H-3V3H-5V-1H-4Z",
                 fill="#181818" if level in ("THIRD_QUARTILE","FOURTH_QUARTILE") else "#eee")
            visible(tile,0,impact,duration)
            # Compact, fading pixel fragments; not a filter or an external resource.
            blast=node(root,"g",transform=f"translate({cx(c)} {y(r)+6})")
            node(blast,"path",d="M-9 -1h4v2h-4z M5 -1h4v2h-4z M-1 -9h2v4h-2z M-1 5h2v4h-2z",
                 fill="#eee")
            end=impact+0.16
            clock(blast,"animate","opacity",[0,0,1,0,0],[0,impact-0.001,impact,end,duration],duration)
        end=launch+(SHIP_Y-top)/BULLET_SPEED
        bolt=node(root,"g",opacity=0)
        node(bolt,"rect",x=cx(c)-1.5,y=-5,width=3,height=10,rx=1,fill="#fff")
        node(bolt,"rect",x=cx(c)-0.5,y=5,width=1,height=9,fill="#999")
        visible(bolt,launch,end+0.008,duration)
        clock(bolt,"animateTransform","transform",[f"0 {SHIP_Y}",f"0 {SHIP_Y}",f"0 {top}",f"0 {top}"],
              [0,launch,end,duration],duration,type="translate")
    # Original MONO silhouette, angular fighter with static metallic facets.
    ship=node(root,"g",id="player-ship",transform=f"translate({LEFT} 0)")
    node(ship,"path",id="fighter-hull",d="M-3 190H3V194H6V199H9V204H13V201H17V196H21V216H15V219H9V216H5V222H-5V216H-9V219H-15V216H-21V196H-17V201H-13V204H-9V199H-6V194H-3Z",fill="#ededed")
    node(ship,"path",d="M-17 202H-13V208H-9V213H-17Z M17 202H13V208H9V213H17Z",fill="#858585")
    node(ship,"path",d="M-3 198H3V202H5V211H-5V202H-3Z",fill="#393939")
    node(ship,"rect",x=-2,y=201,width=4,height=5,fill="#bcbcbc")
    node(ship,"path",d="M-12 219h4v4h-4z M8 219h4v4h-4z",fill="#a0a0a0")
    clock(ship,"animateTransform","transform",[f"{LEFT} 0",f"{RIGHT} 0",f"{LEFT} 0"],
          [0,half,duration],duration,type="translate")
    # Real contribution count, not health or fabricated game points.
    events={}
    for c,r,_,count,_ in active: events[hits[c,r]]=events.get(hits[c,r],0)+count
    times=[0]+sorted(events)+[duration]; points=0
    for i in range(len(times)-1):
        points+=events.get(times[i],0)
        counter=text(root,22,261,f"SCORE {points:04d}",14,"#ededed",font_weight="bold")
        visible(counter,times[i],times[i+1],duration)
    text(root,WIDTH-22,261,f"{len(active)} ACTIVE DAYS / {total} CONTRIBUTIONS",11,text_anchor="end")
    text(root,WIDTH/2,261,"BY MATHEUS  /  ORIGINAL",10,"#a0a0a0",text_anchor="middle")
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
