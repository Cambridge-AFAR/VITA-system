# HARMONI Face Detector

The face detection module works by subscribing to an image topic and detecting faces in the received images, which are then published to another topic.

You can run this module in the `harmoni_face_detect` container.

## Usage

Requires python2.6 - python3.6. Python 3.7 and newer will require dlib compilation from source.

Also note that there may be issues if you're running with Python3 but the python2 paths are overshadowing your opencv install (e.g. $PYTHONPATH=/opt/ros/kinetic/lib/python2.7/dist-packages). One workaround is simply to prepend the python2.7 path with your own opencv path (e.g. export PYTHONPATH=/usr/bin/lib/opencv3_path:PYTHONPATH . The opencv instructions on this page may also work: https://medium.com/@beta_b0t/how-to-setup-ros-with-python-3-44a69ca36674

In the future, an easier workaround might be to just install under ROS Noetic or ROS2 which are both based on python3 out of the box.

## Parameters

These are the parameters for the face detector: 

| Parameters           | Definition | Values |
|----------------------|------------|--------|
|rate_frame               | rate frame      | int; 10     |
|up_sampling              |   up sampling or not       |  int; 0     |
|subscriber_id               |  id of the subscriber          |  str; "default"      |


## Testing



Face detector module can be tested using

```  bash
rostest harmoni_face_detect facenet.test
```
## References
[Documentation](https://harmoni20.readthedocs.io/en/latest/packages/harmoni_face_detect.html)

Based on work from https://github.com/fyr91/face_detection