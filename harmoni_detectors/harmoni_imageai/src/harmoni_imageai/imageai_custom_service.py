#!/usr/bin/env python3

# Common Imports
import rospy
import roslib

from harmoni_common_lib.constants import State
from harmoni_common_lib.service_server import HarmoniServiceServer
from harmoni_common_lib.service_manager import HarmoniServiceManager
import harmoni_common_lib.helper_functions as hf

# Specific Imports
from harmoni_common_lib.constants import State, DetectorNameSpace, SensorNameSpace
from sensor_msgs.msg import Image
from imageai.Detection import VideoObjectDetection
from imageai.Detection.Custom import CustomVideoObjectDetection
import numpy as np
import os
import io
import cv2
from six.moves import queue

class ImageAICustomService(HarmoniServiceManager):
    """
    ImageAICustom service
    """

    def __init__(self, name, param):
        super().__init__(name)
        """ Initialization of variables and imageai parameters """
        self.subscriber_id = param["subscriber_id"]
        self.model_name = param["model_name"]
        self.json_name = param["json_name"]
        self.frame_per_second = param["frame_per_second"]
        self.frame_detection_interval = param["frame_detection_interval"]
        self.output_file_name = param["output_file_name"]
        self.minimum_percentage_probability = param["minimum_percentage_probability"]
        self.return_detected_frame = param["return_detected_frame"]
    
        self.service_id = hf.get_child_id(self.name)
        self.result_msg = ""

        self._buff = queue.Queue()
        self.closed = False

        self.data = b""

        """Setup publishers and subscribers"""
        rospy.Subscriber(
            SensorNameSpace.camera.value + self.subscriber_id,
            Image,
            self.callback,
        )

        self.text_pub = rospy.Publisher(
            DetectorNameSpace.imageai.value + self.service_id, String, queue_size=10
        )

        rospy.Subscriber(
            DetectorNameSpace.imageai.value + self.service_id,
            String,
            self.imageai_callback,
        )

        """Setup the imageai service as server """
        self.state = State.INIT
        return

    def pause_back(self, data):
        rospy.loginfo(f"pausing for data: {len(data.data)}")
        self.pause()
        rospy.sleep(int(len(data.data) / 30000))  # TODO calibrate this guess
        self.state = State.START
        return

    #TODO
    def callback(self, data):
        """ Callback function subscribing to the camera topic"""

        if self.state == State.START:
            # rospy.loginfo("Add data to buffer")
            self._buff.put(data.data)
            # rospy.loginfo("Items in buffer: "+ str(self._buff.qsize()))

        # else:
            # rospy.loginfo("Not Transcribing data")

    
    def imageai_callback(self, data):
        """ Callback function subscribing to the camera topic"""
        self.response_received = True


    #TODO
    def request(self, data):

        rospy.loginfo("Start the %s request" % self.name)
        #self.state = State.REQUEST
        #self.state = State.START
        self.response_received = False
        try:
            # Transcribes data coming from microphone 

            audio_generator = self.generator()
            self.requests = (
                speech.StreamingRecognizeRequest(audio_content=content)
                for content in audio_generator
            )
            responses = self.client.streaming_recognize(self.streaming_config, self.requests)
            self.listen_print_untill_result_is_final(responses)
        
            r = rospy.Rate(1)
            while not self.response_received:
                r.sleep()

            self.state = State.SUCCESS
            self.result_msg = self.stt_response
            self.response_received = False

        except rospy.ServiceException:
            self.start = State.FAILED
            rospy.loginfo("Service call failed")
            self.response_received = True
            self.result_msg = ""
        print("Le risposte sono: ")
        print(self.state)
        print(self.result_msg)
        return {"response": self.state, "message": self.result_msg}

    #TODO
    def start(self, rate=""):
        try:
            rospy.loginfo("Start the %s service" % self.name)
            if self.state == State.INIT:
                self.state = State.START
            
            else:
                self.state = State.START

        except Exception:
            rospy.loginfo("Killed the %s service" % self.name)
        return

    #TODO
    def stop(self):
        rospy.loginfo("Stop the %s service" % self.name)
        try:            
            # Signal the STT input data generator to terminate so that the client's
            # streaming_recognize method will not block the process termination.
            self.closed = True
            self._buff.put(None)

            self.state = State.SUCCESS
        except Exception:
            self.state = State.FAILED
        return

    def pause(self):
        rospy.loginfo("Pause the %s service" % self.name)
        self.state = State.SUCCESS
        return

def main():
    """Set names, collect params, and give service to server"""

    service_name = DetectorNameSpace.imageai.name  # "imageai"
    instance_id = rospy.get_param("instance_id")  # "default"
    service_id = f"{service_name}_{instance_id}"
    try:
        rospy.init_node(service_name, log_level=rospy.DEBUG)

        # stt/default_param/[all your params]
        params = rospy.get_param(service_name + "/" + instance_id + "_param/")

        s = ImageAIService(service_id, params)

        service_server = HarmoniServiceServer(name=service_id, service_manager=s)

        s.start()

        # Streaming audio from mic
        service_server.start_sending_feedback()
        rospy.spin()
        
    except rospy.ROSInterruptException:
        pass

if __name__ == "__main__":
    main()