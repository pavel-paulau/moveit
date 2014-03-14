#!/usr/bin/env python
import argparse
import json
from collections import defaultdict


def read_data(fname):
    raw_data = defaultdict(list)
    with open(fname) as fh:
        for line in fh.readlines():
            event = json.loads(line.strip())
            if event['type'] == 'rebalanceStart':  # only last rebalance events
                raw_data = defaultdict(list)
            if event.get('bucket') not in (None, 'undefined'):
                raw_data[event['bucket']].append(event)
    return raw_data


def parse_events(data):
    _data = defaultdict(dict)
    for bucket, events in data.items():
        _data[bucket] = defaultdict(list)
        for event in sorted(events, key=lambda event: event['ts']):
            vbucket = event.get('vbucket')
            if vbucket:
                _data[bucket][vbucket].append((event['type'], event['ts']))
    return _data


def calc_total_time(events):
    done = start = None
    for event, ts in events:
        if event == 'vbucketMoveDone':
            done = ts
        elif event == 'vbucketMoveStart':
            start = ts
    if done and start:
        return done - start


def find_hot_spots(events, total_time, threshold):
    prev = prev_event = None
    for event, ts in events:
        if event == 'updateFastForwardMap':
            continue
        if prev:
            delta = 100 * (ts - prev) / total_time
            if delta > threshold:
                yield (prev_event, event, delta)
        prev = ts
        prev_event = event


def analyze_events(data, threshold):
    for bucket, vbuckets in data.items():
        timings = []
        hotspots = defaultdict(list)
        for vbucket, events in vbuckets.items():
            total_time = calc_total_time(events)
            if not total_time:
                continue
            timings.append((vbucket, total_time))

            for hotspot in find_hot_spots(events, total_time, threshold):
                hotspots[vbucket].append(hotspot)
        try:
            report(bucket, timings, hotspots)
        except IOError:
            pass


def report(bucket, timings, hotspots):
    mean = sum(total for vbucket, total in timings) / len(timings)
    _max = max(total for vbucket, total in timings)
    _min = min(total for vbucket, total in timings)

    summary = '{{:>{}}}: {{}} movements, ' \
        'mean: {{:.1f}}s, max: {{:.1f}}s, min: {{:.1f}}s'.format(len(bucket))
    vb_summary = '{{:>{}}}: {{:.1f}}s'.format(len(bucket))
    hotspot = '{}{{}} -> {{}}: {{:.1f}}%'.format(''.rjust(len(bucket) + 2))

    print(summary.format(bucket, len(timings), mean, _max, _min))
    for vbucket, total_time in timings:
        print(vb_summary.format(vbucket, total_time))
        for prev_event, event, delta in hotspots[vbucket]:
            print(hotspot.format(prev_event, event, delta))


def main():
    parser = argparse.ArgumentParser(prog='moveit')
    parser.add_argument('-t', dest='threshold', type=float, default=0,
                        help='hotspot threshold in %%')
    parser.add_argument('filename', type=str, help='path to master events log')

    args = parser.parse_args()
    if not 0 <= args.threshold <= 100:
        parser.error('threshold must be in 0 to 100 range')

    raw_data = read_data(fname=args.filename)
    data = parse_events(data=raw_data)
    analyze_events(data, args.threshold)


if __name__ == '__main__':
    main()
