#!/usr/bin/env python3


PKG = "test_harmoni_face_detect"
# Common Imports
import unittest, rospy, roslib, sys

# Specific Imports
from actionlib_msgs.msg import GoalStatus
from harmoni_common_lib.action_client import HarmoniActionClient
from harmoni_common_lib.constants import (
    DetectorNameSpace,
    SensorNameSpace,
    ActionType,
    State,
)
from harmoni_common_msgs.msg import harmoniAction, harmoniFeedback, harmoniResult
from cv_bridge import CvBridge, CvBridgeError
from harmoni_common_lib.constants import SensorNameSpace
from harmoni_common_msgs.msg import Object2D, Object2DArray
from sensor_msgs.msg import Image

path = sys.path
using_kinetic = any([True for p in path if ("kinetic" in p)])
if using_kinetic:
    sys.path.remove("/opt/ros/kinetic/lib/python2.7/dist-packages")
    sys.path.append("/opt/ros/kinetic/lib/python2.7/dist-packages")
import cv2
# from std_msgs.msg import String
import time
import os, io



class TestFaceDetector_Common(unittest.TestCase):
    def __init__(self, *args):
        super(TestFaceDetector_Common, self).__init__(*args)
       

    def setUp(self):
        self.feedback = State.INIT
        self.result = False
        self.image = cv2.imread(rospy.get_param("test_face_detector_input"))
        rospy.init_node("test_face_detector", log_level=rospy.INFO)
        self.rate = rospy.Rate(20)
        self.cv_bridge = CvBridge()
        # provide mock camera
        self.camera_topic = SensorNameSpace.camera.value + "default"
        self.image_pub = rospy.Publisher(
            self.camera_topic,
            Image,
            queue_size=10,
        )

        self.output_sub = rospy.Subscriber(
            DetectorNameSpace.face_detect.value + "default",
            Object2DArray,
            self._detecting_callback,
        )
        print(
            "Testside-Image source: ", SensorNameSpace.camera.value + "default"
        )
        print(
            "Testside-expected detection: ",
            DetectorNameSpace.face_detect.value + "default",
        )

        # startup face_detect node
        self.server = "/harmoni/detecting/face_detect/default"
        self.client = HarmoniActionClient(self.server)
        print("***********SETTING UP CLIENT")
        self.client.setup_client(
            self.server, self._result_callback, self._feedback_callback, wait=False
        )
        rospy.sleep(3) # FIXME not sure why this is needed, but waits don't work and nothing goes through without it.
        print("DONE SETTING UP****************")
        rospy.loginfo("TestFaceDetector: Turning ON face_detect server")
        self.client.send_goal(
            action_goal=ActionType.ON, optional_data="Setup", wait=False
        )
        rospy.loginfo("TestFaceDetector: Started up. waiting for face detect startup")

        # wait for start state
        # while not rospy.is_shutdown() and self.feedback != State.START:
        #     self.rate.sleep()

        rospy.loginfo("TestFaceDetector: publishing image")

        self.image_pub.publish(self.cv_bridge.cv2_to_imgmsg(self.image, encoding="bgr8"))
        # self.image_pub.publish(self.image[:14000])

        rospy.loginfo(
            f"TestFaceDetector: image subscribed to by #{self.output_sub.get_num_connections()} connections."
        )

    def _feedback_callback(self, data):
        rospy.loginfo(f"TestFaceDetector: Feedback: {data}")
        self.feedback = data["state"]

    def _status_callback(self, data):
        rospy.loginfo(f"TestFaceDetector: Status: {data}")
        self.result = True

    def _result_callback(self, data):
        rospy.loginfo(f"TestFaceDetector: Result: {data}")
        self.result = True

    def text_received_callback(self, data):
        rospy.loginfo(f"TestFaceDetector: Text back: {data}")
        self.result = True

    def _detecting_callback(self, data):
        rospy.loginfo(f"TestFaceDetector: Detecting: {data}")
        self.result = True


class TestFaceDetector_Valid(TestFaceDetector_Common):
    def test_IO(self):
        print("TEST_IO")
        rospy.loginfo(
            "TestFaceDetector[TEST]: basic IO test to ensure data "
            + "(example image) is received and responded to. Waiting for transcription..."
        )
        while not rospy.is_shutdown() and not self.result:
            # print("waiting for result")
            self.image_pub.publish(self.cv_bridge.cv2_to_imgmsg(self.image, encoding="rgb8"))
            self.rate.sleep()
        assert self.result == True


def main():
    print("MAIN")
    # TODO combine validity tests into test suite so that setup doesn't have to run over and over.
    import rostest

    rospy.loginfo("test_facenet started")
    rospy.loginfo("TestFaceDetector: sys.argv: %s" % str(sys.argv))
    rostest.rosrun(PKG, "test_face_detector", TestFaceDetector_Valid, sys.argv)
    print("DONE")


if __name__ == "__main__":
    main()
