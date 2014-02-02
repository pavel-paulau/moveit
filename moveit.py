import json
import sys
from collections import defaultdict


HOTSPOT_THRESHOLD = 10


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

def find_hot_spots(events, total_time):
    prev = prev_event = None
    for event, ts in events:
        if event == 'updateFastForwardMap':
            continue
        if prev:
            delta = 100 * (ts - prev) / total_time
            if delta > HOTSPOT_THRESHOLD:
                yield (prev_event, event, delta)
        prev = ts
        prev_event = event


def analyze_events(data):
    for bucket, vbuckets in data.items():
        timings = []
        hotspots = defaultdict(list)
        for vbucket, events in vbuckets.items():
            total_time = calc_total_time(events)
            if not total_time:
                continue
            timings.append((vbucket, total_time))

            for hotspot in find_hot_spots(events, total_time):
                hotspots[vbucket].append(hotspot)
        try:
            report(bucket, timings, hotspots)
        except IOError:
            pass


def report(bucket, timings, hotspots):
    mean = sum(total for vbucket, total in timings) / len(timings)
    _max = max(total for vbucket, total in timings)
    _min = min(total for vbucket, total in timings)

    summary = '{}: {} movements, mean: {:.1f}s, max: {:.1f}s, min: {:.1f}s'
    vb_summary = '{:>8}: {:.1f}s'
    hotspot = '{}{} -> {}: {:.1f}%'

    print(summary.format(bucket, len(timings), mean, _max, _min))
    for vbucket, total_time in timings:
        print(vb_summary.format(vbucket, total_time))
        for prev_event, event, delta in hotspots[vbucket]:
            print(hotspot.format(''.rjust(10), prev_event, event, delta))


def main():
    fname = sys.argv[1]
    raw_data = read_data(fname=fname)
    data = parse_events(data=raw_data)
    analyze_events(data)


if __name__ == '__main__':
    main()
