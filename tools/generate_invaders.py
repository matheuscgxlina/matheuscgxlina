#!/usr/bin/env python3
"""Render the GitHub contribution calendar as a self-contained animated SVG."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
QUERY = '''query($login: String!) {
  user(login: $login) { contributionsCollection { contributionCalendar {
    totalContributions weeks { contributionDays { date weekday contributionCount contributionLevel } }
  } } }
}'''
COLORS = {'NONE':'#262626', 'FIRST_QUARTILE':'#666666', 'SECOND_QUARTILE':'#999999', 'THIRD_QUARTILE':'#c0c0c0', 'FOURTH_QUARTILE':'#f1f1f1'}

def get_calendar(login):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise ValueError('GITHUB_TOKEN is required for the live calendar.')
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': QUERY, 'variables': {'login': login}}).encode(), headers={'Authorization': 'Bearer '+token, 'Content-Type':'application/json', 'User-Agent':'mono-invaders-profile'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    if data.get('errors') or not data.get('data',{}).get('user'):
        raise ValueError('GitHub did not return a usable contribution calendar.')
    return data['data']['user']['contributionsCollection']['contributionCalendar']

def parse(calendar):
    weeks = calendar['weeks']
    if not isinstance(weeks, list) or not 1 <= len(weeks) <= 54:
        raise ValueError('Unexpected calendar size.')
    days, seen = [], set()
    for col, week in enumerate(weeks):
        rows = set()
        for day in week['contributionDays']:
            date = dt.date.fromisoformat(day['date'])
            row, count, level = day['weekday'], day['contributionCount'], day['contributionLevel']
            if type(row) is not int or not 0 <= row <= 6 or row in rows or date in seen or type(count) is not int or count < 0 or level not in COLORS or (count == 0) != (level == 'NONE'):
                raise ValueError('Invalid contribution day.')
            if (date.weekday()+1)%7 != row:
                raise ValueError('Unexpected weekday.')
            rows.add(row); seen.add(date)
            days.append((col,row,date,count,level))
    if not days:
        raise ValueError('Empty calendar response.')
    return days, len(weeks)

def element(parent, tag, **attrs):
    return ET.SubElement(parent, '{'+NS+'}'+tag, {k.replace('_','-'):str(v) for k,v in attrs.items()})

def label(parent,x,y,value,size=12,fill='#aaa',**attrs):
    e=element(parent,'text',x=x,y=y,font_size=size,fill=fill,font_family='monospace',**attrs); e.text=str(value); return e

def animate(parent, attr, values, times, duration, mode='discrete'):
    # Every element shares the same repeating clock.
    return element(parent,'animate',attributeName=attr,values=';'.join(map(str,values)),keyTimes=';'.join(f'{v/duration:.7f}' for v in times),dur=f'{duration}s',repeatCount='indefinite',calcMode=mode)

def render(calendar, demo=False):
    days,ncols=parse(calendar)
    active=[d for d in days if d[3]>0]
    columns=sorted({d[0] for d in active})
    x=lambda c: 24+c*16
    y=lambda r: 69+r*16
    center=lambda c: x(c)+6
    # Sweep left to right. A projectile crosses the actual occupied cells of
    # each active week; then the ship returns to its starting point.
    left,right=center(0),center(ncols-1)
    width=max(904,right+30); height=274
    positions=[f'{left} 0']; times=[0.0]; clock=0.0; prev=left
    shots={}; hits={}
    for c in columns:
        cx=center(c)
        clock+=max(.065,abs(cx-prev)/360)
        positions.append(f'{cx} 0'); times.append(clock)
        launch=clock+.035
        targets=sorted((d for d in active if d[0]==c),key=lambda d:-d[1])
        # The bolt travels vertically through the calendar, bottom to top.
        for d in targets:
            hits[(c,d[1])]=launch+(206-(y(d[1])+6))/560
        finish=max(hits[(c,d[1])] for d in targets)+.13
        shots[c]=(launch,finish,min(y(d[1])+6 for d in targets))
        clock=finish+.025
        positions.append(f'{cx} 0'); times.append(clock); prev=cx
    clock+=max(.08,abs(right-prev)/360)
    positions.append(f'{right} 0'); times.append(clock)
    clock+=.12; positions.append(f'{right} 0'); times.append(clock)
    clock+=max(.15,abs(right-left)/450)
    positions.append(f'{left} 0'); times.append(clock)
    duration=round(clock+.12,6)
    positions.append(f'{left} 0'); times.append(duration)
    root=ET.Element('{'+NS+'}svg',{'viewBox':f'0 0 {width} {height}','width':str(width),'height':str(height),'role':'img','aria-labelledby':'title desc'})
    element(root,'title',id='title').text='MONO / INVADERS — contribution arcade'
    total=sum(d[3] for d in active)
    element(root,'desc',id='desc').text=('Illustrative demo calendar. ' if demo else 'GitHub contribution calendar. ')+f'{len(active)} active days; {total} contributions in displayed cells. A ship clears active days in a repeating animation.'
    element(root,'rect',width=width,height=height,rx=10,fill='#101010',stroke='#383838')
    label(root,24,26,'MONO / INVADERS',17,'#f2f2f2',font_weight='bold')
    label(root,width-24,26,'DEMO / SAMPLE DATA' if demo else 'CONTRIBUTION ARCADE',11,text_anchor='end')
    element(root,'path',d=f'M24 38 H{width-24} M24 233 H{width-24}',stroke='#3b3b3b',fill='none')
    months=set(); last_month_col=-10
    for c,r,date,count,level in days:
        key=(date.year,date.month)
        if key not in months and c-last_month_col>=2:
            label(root,x(c),57,date.strftime('%b').upper(),10); last_month_col=c
        months.add(key)
        element(root,'rect',x=x(c),y=y(r),width=12,height=12,rx=2,fill=COLORS['NONE'])
        if not count: continue
        cx,cy=center(c),y(r)+6; hit=hits[(c,r)]
        # Pixel alien inside the original calendar cell; intensity reflects the real level.
        tile=element(root,'g',transform=f'translate({cx} {cy})')
        element(tile,'rect',x=-6,y=-6,width=12,height=12,rx=2,fill=COLORS[level])
        element(tile,'path',d='M-4 -4 H-3 V-2 H3 V-4 H4 V-1 H5 V3 H3 V5 H1 V3 H-1 V5 H-3 V3 H-5 V-1 H-4 Z',fill='#fff' if level in ('FIRST_QUARTILE','SECOND_QUARTILE') else '#181818')
        eye='#242424' if level in ('FIRST_QUARTILE','SECOND_QUARTILE') else '#eee'
        for ex in (-3,2): element(tile,'rect',x=ex,y=0,width=1.5,height=1.5,fill=eye)
        animate(tile,'opacity',[1,0,0],[0,hit,duration],duration)
        blast=element(root,'g',opacity=0,stroke='#eee',stroke_width=1.4,fill='none')
        element(blast,'path',d=f'M{cx-9} {cy} h4 m10 0 h4 M{cx} {cy-9} v4 m0 10 v4 M{cx-7} {cy-7} l3 3 m8 8 l3 3 M{cx+7} {cy-7} l-3 3 m-8 8 l-3 3')
        animate(blast,'opacity',[0,1,.35,0,0],[0,hit,hit+.05,hit+.12,duration],duration)
    # Compact symmetrical pixel fighter, rendered on a 2px grid.
    ship=element(root,'g',id='player-ship',transform=f'translate({left} 0)')
    # Explicit pixel coordinates keep the outline sharp at README scale.
    sprite=[".......#.......", "......###......", "......###......", ".....#####.....", "..#..#####..#..", "..#.#######.#..", ".#############.", "###############", "##.#########.##", "....###.###....", ".....#...#....."]
    for row,line in enumerate(sprite):
        for col,pixel in enumerate(line):
            if pixel=='#':
                element(ship,'rect',x=-15+col*2,y=200+row*2,width=2,height=2,fill='#ededed')
    element(ship,'rect',x=-1,y=208,width=2,height=6,fill='#777')
    plume=element(ship,'g')
    for px in (-5,5):
        element(plume,'rect',x=px-1,y=222,width=2,height=4,fill='#aaa')
    animate(plume,'opacity',[.4,1,.4],[0,duration/2,duration],duration,mode='linear')
    element(ship,'animateTransform',attributeName='transform',type='translate',values=';'.join(positions),keyTimes=';'.join(f'{t/duration:.7f}' for t in times),dur=f'{duration}s',repeatCount='indefinite',calcMode='linear')
    for c,(launch,finish,top) in shots.items():
        cx=center(c); impact=launch+(206-top)/560
        bolt=element(root,'g',opacity=0)
        element(bolt,'rect',x=cx-1.5,y=-5,width=3,height=12,rx=1,fill='#fff')
        element(bolt,'rect',x=cx-2.5,y=7,width=5,height=9,rx=2,fill='#aaa',opacity=.55)
        animate(bolt,'opacity',[0,1,0,0],[0,launch,impact+.015,duration],duration)
        element(bolt,'animateTransform',attributeName='transform',type='translate',values=f'0 206;0 206;0 {top};0 {top}',keyTimes=';'.join(f'{t/duration:.7f}' for t in [0,launch,impact,duration]),dur=f'{duration}s',repeatCount='indefinite',calcMode='linear')
    points=0
    ordered=sorted(active,key=lambda d:hits[(d[0],d[1])])
    for i in range(len(ordered)+1):
        if i: points+=ordered[i-1][3]
        start=0 if i==0 else hits[(ordered[i-1][0],ordered[i-1][1])]
        end=duration if i==len(ordered) else hits[(ordered[i][0],ordered[i][1])]
        counter=label(root,24,255,f'SCORE {points:04d}',14,'#f1f1f1',opacity=1 if i==0 else 0,font_weight='bold')
        if i==0 and end<duration: animate(counter,'opacity',[1,0,0],[0,end,duration],duration)
        elif i and end<duration: animate(counter,'opacity',[0,1,0,0],[0,start,end,duration],duration)
        elif i: animate(counter,'opacity',[0,1,1],[0,start,duration],duration)
    label(root,width-24,255,f'{len(active)} ACTIVE DAYS  /  {total} CONTRIBUTIONS',11,text_anchor='end')
    if not active: label(root,width/2,191,'AWAITING FIRST CONTRIBUTION',11,text_anchor='middle')
    return ET.tostring(root,encoding='unicode')+'\n'

def sample():
    start=dt.date(2025,11,16); weeks=[]
    for c in range(52):
        ds=[]
        for r in range(7):
            n=(c*13+r*7)%5+1 if (c*17+r*11)%19==0 else 0
            level=['NONE','FIRST_QUARTILE','SECOND_QUARTILE','THIRD_QUARTILE','FOURTH_QUARTILE','FOURTH_QUARTILE'][n]
            ds.append({'date':str(start+dt.timedelta(days=c*7+r)),'weekday':r,'contributionCount':n,'contributionLevel':level})
        weeks.append({'contributionDays':ds})
    return {'weeks':weeks}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--login',default='matheuscgxlina'); p.add_argument('--output',type=Path,required=True); p.add_argument('--demo',action='store_true'); p.add_argument('--input',type=Path,help='Local calendar JSON for testing'); args=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})',args.login): p.error('Invalid login.')
    try:
        data=sample() if args.demo else json.loads(args.input.read_text()) if args.input else get_calendar(args.login)
        svg=render(data,demo=args.demo or bool(args.input))
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(svg,encoding='utf-8')
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(f'Generation failed ({type(e).__name__}); previous asset preserved.',file=sys.stderr); return 1
    print('Generated contribution animation.'); return 0
if __name__=='__main__': raise SystemExit(main())
