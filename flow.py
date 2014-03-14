#!/usr/bin/env python
import argparse
from collections import defaultdict, OrderedDict
from itertools import cycle

import svgwrite

from moveit import read_data


def estimate_concurrency(movements):
    timings = defaultdict(list)
    movements_per_dest = defaultdict(int)
    for dest_node, vbuckets in movements.items():
        for vbucket, ((start, src_node), (end, _)) in vbuckets.items():
            timings[dest_node].append((vbucket, src_node, start, end))
            if src_node != dest_node:
                movements_per_dest[dest_node] += 1

    concurrency_per_dest = dict()
    for dest_node, vbuckets in movements.items():
        max_concurrency = 0
        for vbucket, ((start, src_node), (end, _)) in vbuckets.items():
            concurrency = 0
            for _vbucket, _src_node, _start, _end in timings[dest_node]:
                if vbucket != _vbucket:
                    if src_node == _src_node and src_node != dest_node:
                        if _start < start < _end or _start < end < _end:
                            concurrency += 1
            max_concurrency = max(max_concurrency, concurrency)
        concurrency_per_dest[dest_node] = max_concurrency

    return concurrency_per_dest, movements_per_dest


class SvgPlotter(object):

    PALETTE = (
        "#51A351",
        "#F89406",
        "#7D1935",
        "#4A96AD",
        "#DE1B1B",
        "#E9E581",
        "#A2AB58",
        "#FFE658",
        "#118C4E",
        "#193D4F",
    )

    STROKE_COLOR = '#FFFFFF'

    MAX_WIDTH = 1300
    MAX_HEIGHT = 640.0
    Y_PADDING = 5
    X_PADDING = 50

    DEST_PADDING = 10
    RECT_R = 7

    GRID_LENGTH = 100

    LEGEND_W = 180
    LEGEND_H = 30

    def __init__(self, bucket, fname):
        self.dwg = svgwrite.Drawing(filename='{}_{}.svg'.format(bucket, fname))
        self.draw_border()
        self.draw_grid()

    def draw(self, movements, src_nodes, concurrency_per_dest,
             movements_per_dest, max_ts, min_ts):
        span_height = self.MAX_HEIGHT / len(movements_per_dest)

        scale = lambda ts: ts / (max_ts - min_ts) * self.MAX_WIDTH

        for idx, dest_node in enumerate(sorted(movements_per_dest)):
            concurrency = concurrency_per_dest[dest_node]
            mv_iter = cycle(range(concurrency))
            bar_height = span_height / concurrency

            span_offset = span_height * idx + self.Y_PADDING

            # Destination placeholder
            rect = self.dwg.rect((self.DEST_PADDING / 2, span_offset),
                                 (self.X_PADDING - self.DEST_PADDING, span_height),
                                 rx=self.RECT_R, ry=self.RECT_R,
                                 fill=self.PALETTE[src_nodes.index(dest_node)],
                                 stroke='white')
            self.dwg.add(rect)

            # Separating line
            line = self.dwg.line((self.X_PADDING, span_offset),
                                 (self.MAX_WIDTH + self.X_PADDING, span_offset),
                                 stroke='black',
                                 stroke_dasharray='5,5',
                                 shape_rendering='crispEdges')
            self.dwg.add(line)

            for vbucket, ((sts, src_node), (ets, _)) in movements[dest_node].items():
                if src_node == dest_node:
                    continue
                bar_color = self.PALETTE[src_nodes.index(src_node)]

                # Coordinates and offset
                start = scale(sts - min_ts) + self.X_PADDING
                duration = scale(ets - sts)
                bar_offset = span_offset + next(mv_iter) * bar_height

                # Movement bar
                rect = self.dwg.rect((start, bar_offset),
                                     (duration, bar_height),
                                     fill=bar_color,
                                     stroke_width=1,
                                     stroke='black',
                                     shape_rendering='crispEdges')
                self.dwg.add(rect)

            # Node address and number of movements
            rect = self.dwg.rect(
                (50, span_offset + span_height - 20),
                (140, 20),
                fill='white', stroke='black', shape_rendering='crispEdges',
            )
            self.dwg.add(rect)

            text = self.dwg.text(
                text='{}: {}'.format(dest_node, movements_per_dest[dest_node]),
                insert=[55, span_offset + span_height - 5],
            )
            self.dwg.add(text)

        self.draw_legend(max_ts, min_ts)
        self.dwg.save()

    def draw_legend(self, max_ts, min_ts):
        rect = self.dwg.rect(
            (self.X_PADDING + self.MAX_WIDTH - self.LEGEND_W, self.Y_PADDING),
            (self.LEGEND_W, self.LEGEND_H),
            fill='white', stroke='black', shape_rendering='crispEdges',
        )
        self.dwg.add(rect)

        duration = round((max_ts - min_ts) / 60, 1)
        text = self.dwg.text(
            text='Total duration: {} min'.format(duration),
            insert=[self.X_PADDING + self.MAX_WIDTH - self.LEGEND_W + 5,
                    self.Y_PADDING + 20]
        )
        self.dwg.add(text)

    def draw_border(self):
        rect = self.dwg.rect((0, 0),
                             (self.MAX_WIDTH + self.X_PADDING, self.MAX_HEIGHT + self.Y_PADDING),
                             fill='white',
                             stroke_width=0)
        self.dwg.add(rect)

        rect = self.dwg.rect((self.X_PADDING, self.Y_PADDING),
                             (self.MAX_WIDTH, self.MAX_HEIGHT),
                             fill='white',
                             stroke='black',
                             shape_rendering='crispEdges')
        self.dwg.add(rect)

    def draw_grid(self):
        for g in range(self.X_PADDING, self.MAX_WIDTH, self.GRID_LENGTH):
            line = self.dwg.line((g, self.Y_PADDING),
                                 (g, self.MAX_HEIGHT + self.Y_PADDING),
                                 stroke='black',
                                 stroke_dasharray='5,5',
                                 shape_rendering='crispEdges')
            self.dwg.add(line)


def parse_events(events):
    movements = defaultdict(OrderedDict)
    vm_map = dict()
    src_nodes = set()

    min_ts = float('inf')
    max_ts = 0

    for event in events:
        vbucket = event.get('vbucket')
        ts = event['ts']
        if event['type'] == 'vbucketMoveStart':
            min_ts = min(min_ts, ts)
            dest_node = event['chainAfter'][0].split(':')[0]
            src_node = event['chainBefore'][0].split(':')[0]

            vm_map[vbucket] = dest_node
            src_nodes.add(src_node)

            movements[dest_node][vbucket] = [[ts, src_node]]

        elif event['type'] == 'vbucketMoveDone':
            max_ts = max(max_ts, ts)
            movements[vm_map[vbucket]][vbucket].append([ts, None])

    src_nodes = sorted(src_nodes.union(movements.keys()))
    concurrency_per_dest, movements_per_dest = estimate_concurrency(movements)

    return movements, src_nodes, concurrency_per_dest, movements_per_dest, \
        max_ts, min_ts


def main():
    parser = argparse.ArgumentParser(prog='flow')
    parser.add_argument('filename', type=str, help='path to master events log')
    args = parser.parse_args()

    raw_data = read_data(args.filename)
    for bucket, events in raw_data.items():
        dwg = SvgPlotter(bucket, args.filename)
        dwg.draw(*parse_events(events))


if __name__ == '__main__':
    main()
