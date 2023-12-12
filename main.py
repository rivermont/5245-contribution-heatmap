#!/usr/bin/env python3
"""
Will Bennett
https://github.com/rivermont/py-calendar-heatmap
"""

from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from numpy import linspace
from csv import DictReader
from colour import Color
from lxml import html
import requests
import json


def ingest_ebird(filename='./MyEBirdData.csv'):
    """Open eBird personal data export file,
    and return a data structure with the number of checklists submitted on each date.

    Will return all dates there is data for, not just the last year."""
    print('Loading eBird data...')

    ids = set()
    dates = {}

    try:
        with open(filename, 'r') as f:
            reader = DictReader(f)
            for row in reader:
                id_ = row['Submission ID']
                if id_ not in ids:
                    ids.add(id_)
                    try:
                        dates[row['Date']]['count'] += 1
                    except KeyError:
                        dates[row['Date']] = {'count': 1}

    except FileNotFoundError:
        print(f"eBird data file '{filename}' not found.")

    return dates


def ingest_github(username):
    """Get GitHub contributions from the last year from the user's GitHub profile page.

    Includes contributions in private repositories if the user has enabled that on github.com."""
    print('Loading GitHub data...')

    dates = {}
    url = f'https://github.com/{username}'

    response = requests.get(url).content
    root = html.fromstring(response)

    for i in root.cssselect('.ContributionCalendar-day'):
        try:
            dates[i.attrib['data-date']] = {'count': int(i.attrib['data-level'])}
        except KeyError:
            pass

    return dates


def ingest_inat(username):
    """Get iNaturalist observations for username from the last year using the iNat API.

    Each page contains 200 observations, so pages are requested until we have reached the end of results."""
    print('Loading iNat data...')

    t = datetime.now()
    t = str(int(t.strftime('%Y')) - 1) + t.strftime('-%m-%d')
    dates = {}
    page = 0

    while True:
        page += 1
        url = f'https://api.inaturalist.org/v1/observations?user_id={username}&per_page=200&page={page}&d1={t}'

        response = requests.get(url).content
        content = json.loads(response)

        for i in content['results']:
            try:
                dates[i['observed_on_details']['date']]['count'] += 1
            except KeyError:
                dates[i['observed_on_details']['date']] = {'count': 1}

        if page * 200 >= int(content['total_results']):  # end of results
            break

    return dates


def ingest_osm(username):
    """Retrieve changesets for username from the OpenStreetMap API v0.6.

    Each page contains 100 changesets, so pages are requested at decreasing date ranges until 365 days have been checked."""
    print('Loading OSM data...')

    t = datetime.now()
    t0 = str(int(t.strftime('%Y')) - 1) + t.strftime('-%m-%d')
    t1 = t.strftime("%Y-%m-%dT%H:%M:%S%z")
    dates = {}

    while True:
        url = f'https://api.openstreetmap.org/api/0.6/changesets?display_name={username}&time={t0},{t1}'
        response = requests.get(url).content
        root = ET.fromstring(response)

        for i in root:
            x = i.attrib['created_at']
            try:
                dates[x[:10]]['count'] += 1
            except KeyError:
                dates[x[:10]] = {'count': 1}

        if len(dates) > 366: break  # stop requesting data after a year ago

        try:
            if t1 == root[-1].attrib['created_at']: break  # if it's the last page
        except IndexError:  # empty page (so also the last page)
            break

        t1 = root[-1].attrib['created_at']  # get time of oldest changeset on page

    return dates


def build_cal(data):
    """Construct an svg heatmap calendar from dataset with the following format:
        data = {'2000-01-01': {'count': 1}, ...}"""
    t = datetime.now()  # date of today
    w = int(t.strftime('%w'))  # weekday of today

    days = {}

    x = 624
    y = w * 10
    if w: y += w * 2

    # construct empty dataset of the last year
    for i in range(0, 365):  # TODO handle leap years?
        s = t - timedelta(days=i)  # date of loop
        d = s.strftime('%Y-%m-%d')  # str date of loop

        days[d] = {'date': d, 'contribs': 0, 'color': '#ffaaaa', 'y': y, 'x': x}

        if y:
            if y == 10:
                y -= 10
            else:
                y -= 12
        else:
            y = 72
            x -= 12

    del x, y, t, s

    # add contributions to empty dataset
    for d in data:
        for x in data[d]:
            try:
                days[d]['contribs'] += int(data[d][x])
            except KeyError:
                pass  # date not in the last year

    del data

    # get range of contrib values
    contribs = set([days[x]['contribs'] for x in days])
    contribs = sorted(contribs)

    # number of color classes, diminishing returns around 25
    classes = 25

    # contrib value range
    range_ = linspace(1, contribs[-1], classes)

    # color range
    top = Color('#c6e48b')
    colors = list(top.range_to('#1b6228', classes))

    ranges = {}
    for i in range(classes):
        ranges[range_[i]] = colors[i]

    # calculate color value for each day and add to dict
    for i in days:
        for x in ranges:
            if x <= days[i]['contribs']:
                days[i]['color'] = ranges[x]

    # generate svg code
    out = ''
    out += '<svg xmlns="http://www.w3.org/2000/svg" width="634" height="82">\n'

    for c in days:
        o = f"""<rect fill="{'%s' % days[c]['color']}" width="10" height="10" y="{days[c]['y']}" x="{days[c]['x']}"><title>{days[c]['date']}: {days[c]['contribs']}</title></rect>"""
        out += o + "\n"

    out += '</svg>'

    return out


def main(savefile, ebird=None, git=None, osm=None, inat=None):
    e = {}
    if ebird:
        e.update(ingest_ebird())

    g = {}
    if git:
        g.update(ingest_github(git))

    i = {}
    if inat:
        i.update(ingest_inat(inat))

    o = {}
    if osm:
        o.update(ingest_osm(osm))

    data = {}
    for a in (e, g, i, o):
        for x in a:
            try:
                data[x]['count'] += a[x]['count']
            except KeyError:
                data[x] = {'count': a[x]['count']}

    print('Building calendar...')
    with open(savefile, 'w+') as f:
        f.write(build_cal(data))

    print(f'Saved to {savefile}')


if __name__ == '__main__':
    # example with all sources
    main('calendar.svg', ebird=True, git='rivermont', osm='rivermont', inat='rivermont')

    # examples with single source
    main('rose.svg', inat='annkatrinrose')  # Dr. Rose in Biology Dept
    main('git.svg', git='bhousel')  # full-time developer
