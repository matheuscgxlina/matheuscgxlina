#!/usr/bin/env python3
"""Shared GitHub GraphQL calendar client, validator and synthetic test fixture."""
import datetime as dt
import json
import os
import urllib.request

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

