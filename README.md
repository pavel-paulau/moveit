Prerequisites
-------------

* Python 2.7/3.3
* pip

Installation
-------------

    pip install moveit

Usage
-----

    moveit master_events.log | head
    bucket-1: 768 movements, mean: 194.0s, max: 478.5s, min: 6.3s
          43: 242.9s
              checkpointWaitingStarted -> checkpointWaitingEnded: 52.3%
              checkpointWaitingStarted -> checkpointWaitingEnded: 46.3%
          44: 234.0s
              checkpointWaitingStarted -> checkpointWaitingEnded: 44.5%
              checkpointWaitingStarted -> checkpointWaitingEnded: 54.0%
          45: 147.8s
              checkpointWaitingStarted -> checkpointWaitingEnded: 88.7%
          46: 134.0s
