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
DEFAULT_SPEED = 145.0
MAX_BYTES = 100_000
BULLET_SPEED = 180.0
COLORS = {"NONE":"#202020","FIRST_QUARTILE":"#737373",
          "SECOND_QUARTILE":"#aaaaaa","THIRD_QUARTILE":"#d4d4d4",
          "FOURTH_QUARTILE":"#ffffff"}

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
                keyTimes=";".join(f"{t/duration:.7f}".rstrip("0").rstrip(".") for t in times),
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
    if not math.isfinite(speed) or not 120<=speed<=170:
        raise ValueError("Speed must be between 120 and 170 px/s")
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
    node(root,"path",d="M10 48V230 M894 48V230",fill="none",stroke="#555",stroke_width=1)
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
    node(root,"path",id="marquee-lines",d="M105 25H300 M604 25H799",stroke="#888",stroke_width=1.4,fill="none")
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
    starfield=node(root,"path",id="patrol-stars",d=" ".join(stars),fill="#777")
    if len(active)<=5:
        # One subtle ambient animation for sparse calendars; no invented activity.
        clock(starfield,"animate","opacity",[.38,1,.38],[0,duration/2,duration],duration)
    node(root,"path",d="M24 232H880",stroke="#777",stroke_dasharray="2 4",fill="none")
    # Classic arcade HUD with angular score and statistics panels.
    node(root,"path",d="M21 239H211L223 255L211 267H21L12 255Z M606 239H883L892 255L883 267H606L594 255Z",fill="#121212",stroke="#888")
    if len(active)<=5:
        text(root,297,260,"PATROL MODE" if active else "NO ACTIVITY",11,"#dedede",text_anchor="middle")
        node(root,"path",d="M539 250H589 M539 255H589",stroke="#555",fill="none")
    else:
        node(root,"path",d="M228 250H365 M228 255H365 M539 250H608 M539 255H608",stroke="#555",fill="none")
    x=lambda c:GRID_X+c*STEP
    y=lambda r:GRID_Y+r*STEP
    cx=lambda c:x(c)+CELL/2
    # Reusable vector definitions keep the whole calendar under 100 KB.
    defs=node(root,"defs")
    pattern=node(defs,"pattern",id="grid-pattern",patternUnits="userSpaceOnUse",
                 x=GRID_X,y=GRID_Y,width=STEP,height=STEP)
    node(pattern,"rect",width=CELL,height=CELL,rx=2,fill=COLORS["NONE"])
    node(root,"path",id="calendar-grid",d=f"M{GRID_X} {GRID_Y}h{52*STEP+CELL}v{6*STEP+CELL}h-{52*STEP+CELL}z",fill="url(#grid-pattern)")
    sprite=("010000010","001000100","011111110","110111011",
            "111111111","101111101","001000100")
    pixels=[]
    for row,line in enumerate(sprite):
        for col,pixel in enumerate(line):
            if pixel=="1":
                pixels.append(f"M{col-4.5} {row-3.5}h1v1h-1z")
    node(defs,"path",id="enemy-sprite",d=" ".join(pixels),fill="#151515")
    burst=node(defs,"g",id="impact-sprite")
    node(burst,"path",d="M-2 -2h4v4h-4z M-1 -10h2v5h-2z M-1 5h2v5h-2z M-10 -1h5v2h-5z M5 -1h5v2h-5z",fill="#fff")
    node(burst,"path",d="M-3 -3L-7 -6H-5L-9 -10 M3 -3L7 -6H5L9 -10 M-3 3L-7 6H-5L-9 10 M3 3L7 6H5L9 10",stroke="#aaa",stroke_width="1.2",fill="none")
    node(burst,"path",d="M-12 -6V-12H-6 M6 -12H12V-6 M12 6V12H6 M-6 12H-12V6 M-9 -6h2v2h-2z M7 4h2v2h-2z",stroke="#fff",stroke_width="1.2",fill="none")
    pulse=node(defs,"g",id="pulse-sprite")
    node(pulse,"path",d="M-4 1h2v-6h4v6h2v9h-2v5h-4v-5h-2z",fill="#777")
    node(pulse,"path",d="M-2 -9h4v18h-4z M-1 9h2v16h-2z",fill="#fff")
    node(pulse,"path",d="M-5 4h2v4h-2z M3 4h2v4h-2z M-2 19h1v3h-1z M1 19h1v3h-1z",fill="#bbb")
    # Internal SVG references only (no remote resources or JavaScript).
    def use(parent, ref, **attrs):
        return node(parent,"use",href="#"+ref,**attrs)

    # Every month stays anchored to its first represented calendar column.
    months={}
    for c,r,date,count,level in sorted(days,key=lambda d:d[2]):
        months.setdefault((date.year,date.month),(c,date))
    labels=list(months.values())
    crowded=len(labels)>1 and labels[1][0]-labels[0][0]<3
    for i,(c,date) in enumerate(labels):
        lx=cx(c)
        anchor="middle"
        if crowded and i==0: anchor="end"
        elif crowded and i==1: anchor="start"
        elif lx+11>880: anchor="end"
        text(root,lx,58,date.strftime("%b").upper(),11,"#f0f0f0",
             text_anchor=anchor,id=f"month-{date.year}-{date.month:02d}")
        node(root,"path",d=f"M{lx} 61v3",stroke="#888",fill="none")

    # Persistent data layer: five separate grayscale levels; no fabricated cells.
    for level,color in COLORS.items():
        if level=="NONE": continue
        cells=[(c,r) for c,r,date,count,lv in active if lv==level]
        if cells:
            geom=" ".join(f"M{x(c)+1} {y(r)+1}h10v10h-10z" for c,r in cells)
            node(root,"path",id="activity-"+level.lower(),d=geom,fill=color,
                 stroke=color,stroke_width="1.5",stroke_linejoin="round")

    # One clipping track per occupied column destroys its aliens from bottom up.
    # The bright contribution underneath remains visible after every hit.
    hits={}
    shots=[]
    by_row={r:[] for r in range(7)}
    for c in sorted({d[0] for d in active}):
        launch=(cx(c)-LEFT)/speed
        targets=sorted((d for d in active if d[0]==c),key=lambda d:-d[1])
        top=min(y(d[1])+6 for d in targets)
        clip=node(defs,"clipPath",id=f"cut-{c}",clipPathUnits="userSpaceOnUse")
        cutter=node(clip,"rect",x=x(c),y=GRID_Y,width=CELL,height=6*STEP+CELL)
        enemies=node(root,"g",id=f"enemies-{c}",clip_path=f"url(#cut-{c})")
        ct=[0.0]; heights=[6*STEP+CELL]
        for _,r,_,count,level in targets:
            impact=launch+(SHIP_Y-(y(r)+6))/BULLET_SPEED
            hits[c,r]=impact
            by_row[r].append((impact,cx(c)))
            use(enemies,"enemy-sprite",x=cx(c),y=y(r)+6)
            ct.append(impact); heights.append(y(r)-GRID_Y)
        ct.append(duration); heights.append(heights[-1])
        clock(cutter,"animate","height",heights,ct,duration,"discrete")
        shots.append((launch,launch+(SHIP_Y-top)/BULLET_SPEED,cx(c),top))

    # Pool overlapping projectiles into a few independent SMIL tracks.
    # Each pulse starts at the ship and reaches the actual target column.
    lanes=[]
    for shot in shots:
        launch,end,bx,top=shot
        lane=next((q for q in lanes if q[-1][1]+.10<launch),None)
        if lane is None: lane=[]; lanes.append(lane)
        lane.append(shot)
    for i,lane in enumerate(lanes):
        projectile=node(root,"g",id=f"projectile-{i}",opacity=0,
                        transform=f"translate({lane[0][2]} {SHIP_Y})")
        use(projectile,"pulse-sprite")
        vt=[0.0]; vv=[0]
        mt=[0.0]; mv=[f"{lane[0][2]} {SHIP_Y}"]
        for launch,end,bx,top in lane:
            # Hold hidden position until launch; reposition while hidden.
            before=launch-.001
            mt.extend([before,launch,end,end+.09])
            mv.extend([mv[-1],f"{bx} {SHIP_Y}",f"{bx} {top}",f"{bx} {top}"])
            vt.extend([launch,end+.09]); vv.extend([1,0])
        mt.append(duration); mv.append(mv[-1])
        vt.append(duration); vv.append(0)
        clock(projectile,"animateTransform","transform",mv,mt,duration,type="translate")
        clock(projectile,"animate","opacity",vv,vt,duration,"discrete")

    # Reuse a burst per row. Sparse calendars get a long readable flash;
    # dense calendars shorten the burst only when the next impact is imminent.
    for row,row_hits in by_row.items():
        if not row_hits: continue
        row_hits.sort()
        impact_group=node(root,"g",id=f"impact-row-{row}",opacity=0)
        use(impact_group,"impact-sprite")
        mt=[0.0]; mv=[f"{row_hits[0][1]} {y(row)+6}"]
        ot=[0.0]; ov=[0]
        for i,(impact,bx) in enumerate(row_hits):
            next_impact=row_hits[i+1][0] if i+1<len(row_hits) else duration
            end=min(impact+.42,next_impact-.002)
            hold=min(.12,(end-impact)/2)
            mt.append(impact); mv.append(f"{bx} {y(row)+6}")
            ot.extend([impact-.001,impact,impact+hold,end])
            ov.extend([0,1,1,0])
        mt.append(duration); mv.append(mv[-1])
        ot.append(duration); ov.append(0)
        clock(impact_group,"animateTransform","transform",mv,mt,duration,"discrete",type="translate")
        clock(impact_group,"animate","opacity",ov,ot,duration)

    # A single ambient scanner in sparse calendars; never scores or marks a day.
    if len(active)<=5:
        scanner=node(root,"g",id="patrol-scanner",opacity=0)
        node(scanner,"path",d="M-9 180H9 M-6 176H6",stroke="#a0a0a0",stroke_width="1",fill="none")
        clock(scanner,"animateTransform","transform",
              [f"{LEFT} 0",f"{RIGHT} 0",f"{LEFT} 0"],[0,half,duration],duration,type="translate")
        clock(scanner,"animate","opacity",[.2,.65,.2],[0,half,duration],duration)
    # Original pixel fighter: broad wings, stepped hull and twin thrusters.
    ship=node(root,"g",id="player-ship",transform=f"translate({LEFT} 0)")
    node(ship,"path",id="fighter-hull",d="M-3 190H3V195H6V200H9V205H13V201H17V196H21V216H17V221H11V217H6V223H-6V217H-11V221H-17V216H-21V196H-17V201H-13V205H-9V200H-6V195H-3Z",fill="#eeeeee")
    node(ship,"path",d="M-21 201H-17V211H-13V217H-17V216H-21Z M21 201H17V211H13V217H17V216H21Z M-3 190H0V200H-3Z",fill="#929292")
    node(ship,"path",d="M-3 199H3V203H5V212H-5V203H-3Z",fill="#333")
    node(ship,"rect",x=-2,y=202,width=4,height=5,fill="#bcbcbc")
    node(ship,"path",d="M-12 220h4v5h-4z M8 220h4v5h-4z",fill="#aaa")
    clock(ship,"animateTransform","transform",[f"{LEFT} 0",f"{RIGHT} 0",f"{LEFT} 0"],
          [0,half,duration],duration,type="translate")
    # Compact rolling digit strips: the score changes at each actual hit.
    events={}
    for c,r,_,count,_ in active: events[hits[c,r]]=events.get(hits[c,r],0)+count
    points=0; states=[(0.0,0)]
    for when in sorted(events):
        points+=events[when]; states.append((when,points))
    digits=max(4,len(str(total)))
    score=node(root,"g",id="scoreboard")
    node(score,"title").text=f"SCORE {total:0{digits}d}"
    text(score,28,260,"SCORE",15,"#ededed",font_weight="bold",letter_spacing=".5")
    clip=node(defs,"clipPath",id="score-window")
    node(clip,"rect",x=86,y=245,width=digits*10+2,height=18)
    score_digits=node(score,"g",clip_path="url(#score-window)")
    for i in range(digits):
        strip=node(score_digits,"g",id=f"score-digit-{i}")
        digit_text=node(strip,"text",x=88+i*10,y=260,font_size=15,
                        font_family="monospace",font_weight="bold",fill="#ededed")
        for value in range(10):
            node(digit_text,"tspan",x=88+i*10,y=260+18*value).text=str(value)
        ts=[0.0]; vs=["0 0"]; last=0
        for when,value in states[1:]:
            current=int(f"{value:0{digits}d}"[i])
            if current!=last:
                ts.append(when); vs.append(f"0 {-18*current}"); last=current
        if len(ts)>1:
            ts.append(duration); vs.append(vs[-1])
            clock(strip,"animateTransform","transform",vs,ts,duration,"discrete",type="translate")
    text(root,WIDTH-28,260,f"{len(active)} ACTIVE DAYS / {total} CONTRIBUTIONS",12,"#f0f0f0",text_anchor="end")
    legend=node(root,"g",id="activity-legend")
    text(legend,WIDTH/2-48,261,"LOW",11,"#e5e5e5",text_anchor="end")
    for i, color in enumerate(COLORS.values()):
        node(legend,"rect",x=WIDTH/2-38+i*14,y=251,width=11,height=11,rx=2,fill=color,stroke="#777",stroke_width=".5")
    text(legend,WIDTH/2+39,261,"HIGH",11,"#e5e5e5")
    svg=ET.tostring(root,encoding="unicode")+"\n"
    if len(svg.encode("utf-8"))>=MAX_BYTES:
        raise ValueError("SVG exceeds the 100 KB budget")
    return svg

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
