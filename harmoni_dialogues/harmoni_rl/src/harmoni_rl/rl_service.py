#!/usr/bin/env python3

# Common Imports
import rospy
from dotenv import load_dotenv
from harmoni_common_lib.constants import *
from harmoni_common_lib.service_server import HarmoniServiceServer
from harmoni_common_lib.service_manager import HarmoniServiceManager
import harmoni_common_lib.helper_functions as hf
from std_msgs.msg import String, Bool, Float32
from harmoni_rl.rl_client import RLCore, RLActionsName, PPEnv
# Specific Imports
import os
import ast
import pandas as pandas
import numpy as np
#import d3rlpy

class RLService(HarmoniServiceManager):
    """This is a class representation of a harmoni_dialogue service
    (HarmoniServiceManager). It is essentially an extended combination of the
    :class:`harmoni_common_lib.service_server.HarmoniServiceServer` and :class:`harmoni_common_lib.service_manager.HarmoniServiceManager` classes

    :param name: Name of the current service
    :type name: str
    :param param: input parameters of the configuration.yaml file
    :type param: from yaml
    """

    def __init__(self, name, param):
        """Constructor method: Initialization of variables and lex parameters + setting up"""
        super().__init__(name)
        """ Initialization of variables and lex parameters """
        self.subscriber_id = param['subscriber_id']
        self.model_name = param['model_name']
        self.model_dir = param['model_dir']
        self.dataset = param['dataset']
        self.state = State.INIT
        self._duration_sub = rospy.Subscriber(DetectorNameSpace.stt.value + self.subscriber_id + '/duration', Float32, self._speech_duration_cb, queue_size=1)  
        self._fer_sub = rospy.Subscriber(DetectorNameSpace.fer.value + self.subscriber_id, String, self._fer_detector_cb, queue_size=1)
        self._fer_sub_baseline = rospy.Subscriber(DetectorNameSpace.fer.value + self.subscriber_id + "/baseline", String, self._fer_detector_base_cb, queue_size=1)
        self._detcustom_sub = rospy.Subscriber(DetectorNameSpace.detcustom.value + self.subscriber_id, Bool, self._detcustom_detector_cb, queue_size=1)
        self._vad_sub = rospy.Subscriber(DetectorNameSpace.vad.value + self.subscriber_id, Bool, self._vad_detector_cb, queue_size=1)
        self._stt_sub = rospy.Subscriber(DetectorNameSpace.stt.value + self.subscriber_id, String, self._stt_detector_cb, queue_size=1)
        self.vad = []
        self.detcustom = []
        self.fer = []
        self.stt = []
        self.speech_features = []
        self.fer_baseline = []
        self.stt_received = False
        self.duration = 0
        self.baseline = True
        self._setup()
        return


    def _setup(self):
        self.rl = RLCore()
        self.rl.setup(self.model_dir, self.model_name, self.dataset)
        

    def _fer_detector_cb(self, data):
        data = ast.literal_eval(data.data)
        #rospy.loginfo("==================== FER DETECTION RECEIVED")
        #if self.state == State.REQUEST:
        self.fer.append(data)
        return


    def _fer_detector_base_cb(self, data):
        data = ast.literal_eval(data.data)
        
        #if self.state == State.REQUEST:
        if self.baseline:
            rospy.loginfo("==================== FER DETECTION BASELINE RECEIVED")
            rospy.loginfo(data[0])
            rospy.loginfo(data[1])
            self.fer_baseline.append(float(data[0]))
            self.fer_baseline.append(float(data[1]))
            rospy.loginfo(self.fer_baseline)
            self.baseline = False
        return


    def _detcustom_detector_cb(self, data):
        data = data.data
        rospy.loginfo("==================== IR DETECTION RECEIVED")
        #rospy.loginfo(data)
        #if self.state == State.REQUEST:
        if data == True:
            data = 1
        else:
            data = 0
        self.detcustom.append(data)
        rospy.loginfo(data)
        return
    
    def _vad_detector_cb(self, data):
        data = data.data
        #rospy.loginfo("==================== VAD DETECTION RECEIVED")
        #rospy.loginfo(data)
        #if self.state ==  State.REQUEST:
        if data == True:
            data = 1
        else:
            data = 0
        self.vad.append(data)
        return

    def _speech_duration_cb(self, data):
        data = data.data
        rospy.loginfo("==================== DURATION DETECTION RECEIVED")
        #rospy.loginfo(data)
        #if self.state ==  State.REQUEST:
        self.duration = data
        return

    def _stt_detector_cb(self, data):
        data = data.data
        rospy.loginfo("==================== STT DETECTION RECEIVED")
        rospy.loginfo(data)
        if data:
            self.stt_received = True
        return

    def request(self, exercise):
        """[summary]

        Args:
            exercise (str): Exercise current state

        Returns:
            object: It containes information about the response received (bool) and response message (str)
                response: bool
                message: str
        """
        rospy.loginfo("Start the %s request" % self.name)
        self.state = State.REQUEST
        result = {"response": False, "message": None}
        try:
            while not self.stt_received:
                rospy.sleep(0.1)
            
            Vmax = self.fer_baseline[1]
            Vmin = self.fer_baseline[0]
            V = np.mean(self.fer)
            fer_reward = 20*(V-Vmin)/(Vmax - Vmin) -10
            vad_observation = [len(self.vad) - self.duration, self.duration]
            ir_observation = [len(self.detcustom) - np.count_nonzero(self.detcustom), np.count_nonzero(self.detcustom)]
            interaction_observation = [0]*4
            interaction_observation[int(exercise)-1] = 1
            observations = interaction_observation + vad_observation
            reward = np.exp(fer_reward)
            env = PPEnv(observations, reward)
            rospy.loginfo(self.detcustom)
            if len(self.detcustom)!=0:
                errors = int(self.detcustom.count(1))
                rospy.loginfo("The number of IRs are:" + str(errors))
            else:
                errors = 0
            if errors > 3:
                self.result_msg = "4"
            else:
                #self.result_msg = RLCore.start_training(env)
                self.result_msg = self.rl.batch_rl(observations)
                rospy.loginfo("--------------- THE ACTION WAS:" + self.result_msg)
            self.response_received = True
            self.state = State.SUCCESS
            self.vad = []
            self.detcustom = []
            self.fer = []
            self.stt = []
            self.stt_received = False
            rospy.loginfo("++++++ responded")
            rospy.loginfo(self.result_msg)
        except rospy.ServiceException:
            self.state = State.FAILED
            rospy.loginfo("Service call failed")
            self.response_received = True
            self.result_msg = ""
            self.vad = []
            self.detcustom = []
            self.fer = []
            self.stt = []
            self.stt_received = False
        return {"response": self.state, "message": self.result_msg}

def main():
    """[summary]
    Main function for starting HarmoniRLService service
    """
    service_name = DialogueNameSpace.rl.name
    instance_id = rospy.get_param("instance_id")  # "default"
    service_id = f"{service_name}_{instance_id}"
    try:
        rospy.init_node(service_name, log_level=rospy.DEBUG)
        params = rospy.get_param(service_name + "/" + instance_id + "_param/")
        s = RLService(service_id, params)
        service_server = HarmoniServiceServer(service_id, s)
        #s.request("savouring")
        print(service_name)
        print("**********************************************************************************************")
        print(service_id)

        service_server.start_sending_feedback()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass


if __name__ == "__main__":
    main()