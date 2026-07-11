# Hub Vision And Congestion

Hub congestion does not need a new detector. It uses the package detector plus tracker memory.

```text
YOLO package detections -> ByteTrack IDs -> zone membership -> dwell and queue metrics -> overflow forecast
```

Zones are simple polygons: inbound, queue, sorting, loading, and outbound. Every frame checks each tracked package centroid against those polygons. If a package stays in a zone too long, dwell risk rises. If queue count crosses a threshold, congestion rises. Forecasting combines current queue, dwell, incoming trucks, and processing rate.
