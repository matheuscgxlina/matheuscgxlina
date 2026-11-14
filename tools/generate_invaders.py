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
    columns=sorted({d[0] for d in active}, reverse=True)
    # One volley per active week. The beam clears that week's active cells.
    step=max(.48,min(1.8,24/max(1,len(columns))))
    duration=round(3.2+len(columns)*step,3)
    events={c:1.1+i*step for i,c in enumerate(columns)}
    x=lambda c: 24+c*16
    y=lambda r: 69+r*16
    width=904; height=255
    root=ET.Element('{'+NS+'}svg',{'viewBox':f'0 0 {width} {height}','width':str(width),'height':str(height),'role':'img','aria-labelledby':'title desc'})
    element(root,'title',id='title').text='MONO / INVADERS — contribution arcade'
    element(root,'desc',id='desc').text=('Illustrative demo calendar. ' if demo else 'GitHub contribution calendar. ')+f'{len(active)} active days; {sum(d[3] for d in active)} contributions in displayed cells. A ship clears active weeks in a repeating animation.'
    element(root,'rect',width=width,height=height,rx=10,fill='#101010',stroke='#383838')
    label(root,24,25,'MONO / INVADERS',16,'#f2f2f2',font_weight='bold')
    label(root,880,25,'DEMO / SAMPLE DATA' if demo else 'CONTRIBUTION ARCADE',11,text_anchor='end')
    element(root,'path',d='M24 36 H880 M24 207 H880',stroke='#3b3b3b',fill='none')
    # Month boundaries are derived from the actual dates, not hard-coded.
    months=set(); last_month_col=-10
    for c,r,date,count,level in days:
        key=(date.year,date.month)
        if key not in months and c-last_month_col>=2:
            label(root,x(c),57,date.strftime('%b').upper(),10); last_month_col=c
        months.add(key)
        element(root,'rect',x=x(c),y=y(r),width=12,height=12,rx=2,fill=COLORS['NONE'])
        if count:
            tile=element(root,'rect',x=x(c),y=y(r),width=12,height=12,rx=2,fill=COLORS[level]); hit=events[c]
            animate(tile,'opacity',[1,0,0],[0,hit,duration],duration)
            blast=element(root,'g',opacity=0,stroke='#fff',stroke_width=1.2,fill='none')
            cx,cy=x(c)+6,y(r)+6
            element(blast,'path',d=f'M{cx-8} {cy-8} l4 4 m8 8 l4 4 M{cx+8} {cy-8} l-4 4 m-8 8 l-4 4')
            animate(blast,'opacity',[0,1,0,0],[0,hit,hit+.16,duration],duration)
    ship=element(root,'g',transform='translate(450 0)')
    element(ship,'path',d='M-19 191 H-12 V184 H-5 V176 H5 V184 H12 V191 H19 V198 H-19 Z',fill='#f1f1f1')
    element(ship,'rect',x=-6,y=198,width=12,height=3,fill='#898989')
    if columns:
        positions=['450 0']; times=[0]
        for c in columns:
            hit=events[c]; positions.extend([f'{x(c)+6} 0',f'{x(c)+6} 0']); times.extend([hit-.20,hit+.18])
        positions.append(positions[-1]); times.append(duration)
        element(ship,'animateTransform',attributeName='transform',type='translate',values=';'.join(positions),keyTimes=';'.join(f'{t/duration:.7f}' for t in times),dur=f'{duration}s',repeatCount='indefinite',calcMode='linear')
    for c in columns:
        hit=events[c]; cx=x(c)+6; top=min(y(d[1])+6 for d in active if d[0]==c)
        beam=element(root,'g',opacity=0)
        element(beam,'line',x1=cx,y1=175,x2=cx,y2=top,stroke='#fff',stroke_width=2)
        element(beam,'line',x1=cx,y1=175,x2=cx,y2=top,stroke='#bcbcbc',stroke_width=6,opacity=.2)
        animate(beam,'opacity',[0,1,0,0],[0,hit-.16,hit+.06,duration],duration)
    points=0
    # Counter labels have disjoint visibility intervals and reset on each loop.
    for i in range(len(columns)+1):
        if i: points+=sum(d[3] for d in active if d[0]==columns[i-1])
        start=0 if i==0 else events[columns[i-1]]
        end=duration if i==len(columns) else events[columns[i]]
        counter=label(root,24,232,f'SCORE {points:04d}',14,'#f1f1f1',opacity=1 if i==0 else 0,font_weight='bold')
        if i==0 and end<duration: animate(counter,'opacity',[1,0,0],[0,end,duration],duration)
        elif i and end<duration: animate(counter,'opacity',[0,1,0,0],[0,start,end,duration],duration)
        elif i: animate(counter,'opacity',[0,1,1],[0,start,duration],duration)
    label(root,880,232,f'{len(active)} ACTIVE DAYS  /  {sum(d[3] for d in active)} CONTRIBUTIONS',11,text_anchor='end')
    if not active: label(root,450,170,'AWAITING FIRST CONTRIBUTION',12,text_anchor='middle')
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
