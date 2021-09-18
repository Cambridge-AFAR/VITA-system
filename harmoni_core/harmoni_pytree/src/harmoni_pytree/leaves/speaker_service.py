#!/usr/bin/env python3

# Common Imports
import rospy, rospkg, roslib

from harmoni_common_lib.constants import *
from harmoni_common_lib.service_server import HarmoniServiceServer
from harmoni_common_lib.service_manager import HarmoniServiceManager
from harmoni_common_lib.action_client import HarmoniActionClient
from actionlib_msgs.msg import GoalStatus
import harmoni_common_lib.helper_functions as hf
from harmoni_speaker.speaker_service import SpeakerService

# Specific Imports
from audio_common_msgs.msg import AudioData
from harmoni_common_lib.constants import ActuatorNameSpace, ActionType, State
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
from collections import deque 
import soundfile as sf
import numpy as np
import boto3
import re
import json
import ast
import sys
import time

# import wget
import contextlib
import ast
import wave
import os

#py_tree
import py_trees

class SpeakerServicePytree(py_trees.behaviour.Behaviour):

    #TODO change all the print in console py_tree
    """
    the boolean "mode" changes the functioning of the Behaviour:
    true: we use the leaf as both client and server (inner module)
    false: we use the leaf as client that makes request to the server
    """
    #TTS is an actuators

    def __init__(self, name = "SpeakerServicePytree"):
        self.name = name
        self.mode = False
        self.speaker_service = None
        self.result_data = None
        self.service_client_speaker = None
        self.client_result = None
        self.audio_data = None

        # here there is the inizialization of the blackboards
        self.blackboards = []
        #do we need a blackboard here?
        self.blackboard_tts = self.attach_blackboard_client(name=self.name, namespace=ActuatorNameSpace.tts.name)
        self.blackboard_tts.register_key("result_data", access=py_trees.common.Access.READ)
        self.blackboard_tts.register_key("result_message", access=py_trees.common.Access.READ)

        #TODO: usa queste bb che sono le nuove
        self.blackboard_tts = self.attach_blackboard_client(name=self.name, namespace=ActuatorNameSpace.tts.name)
        self.blackboard_tts.register_key("result", access=py_trees.common.Access.READ)
        self.blackboard_speaker = self.attach_blackboard_client(name=self.name, namespace=ActuatorNameSpace.speaker.name)
        self.blackboard_speaker.register_key("state", access=py_trees.common.Access.WRITE)
        #per external speaker, secondo noi questo funzionamento deve appartenere ad un'altra foglia
        self.blackboard_speaker = self.attach_blackboard_client(name=self.name, namespace=PyTreeNameSpace.scene.name)
        self.blackboard_speaker.register_key("sound", access=py_trees.common.Access.READ)

        super(SpeakerServicePytree, self).__init__(name)
        self.logger.debug("%s.__init__()" % (self.__class__.__name__))

    def setup(self,**additional_parameters):
        """
        In order to select the mode after that the tree is created 
        an additional_parameters parameter is used:
        this parameter is a dictionary that contains couples like   
        name_of_the_leaf --> boolean mode
        """
        for parameter in additional_parameters:
            print(parameter, additional_parameters[parameter])  
            if(parameter ==ActuatorNameSpace.speaker.name):
                self.mode = additional_parameters[parameter]  

        #service_name = ActuatorNameSpace.speaker.name
        #instance_id = rospy.get_param("/instance_id")
        #service_id = f"{service_name}_{instance_id}"

        #self.speaker_service = SpeakerService(service_id)
        #rospy.init_node(self.server_name , log_level=rospy.INFO)
    
        if(not self.mode):
            self.service_client_speaker = HarmoniActionClient(self.name)
            self.client_result = deque()
            self.server_name = "speaker_default"
            self.service_client_speaker.setup_client(self.server_name, 
                                                self._result_callback,
                                                self._feedback_callback)
            self.logger.debug("Behavior %s interface action clients have been set up!" % (self.server_name))
        
        self.logger.debug("%s.setup()" % (self.__class__.__name__))

    def initialise(self):
        """
        
        """   
        self.logger.debug("%s.initialise()" % (self.__class__.__name__))
    
    def update(self):
        """
        
        """
        #TODO check INVALID
        if(self.mode):
            if self.blackboard_tts.result_message == State.SUCCESS:
                self.audio_data = self.blackboard_tts.result_data
                self.result_data = self.speaker_service.do(self.audio_data)
                new_status = py_trees.common.Status.SUCCESS
            else:
                #either the state is "RUNNING" or "FAILURE" so in both cases we will do:
                new_status = self.blackboard_tts.result_message
        else:
            if self.blackboard_tts.result_message == State.SUCCESS:
                #have I already done the request? check for this
                if self.service_client_speaker.get_state() == GoalStatus.LOST:
                    self.audio_data = self.blackboard_tts.result_data
                    self.logger.debug(f"Sending goal to {self.speaker_service}")
                    self.service_client_speaker.send_goal(
                        action_goal = ActionType["DO"].value,
                        optional_data = self.audio_data,
                        wait=False,
                    )
                    self.logger.debug(f"Goal sent to {self.speaker_service}")
                    new_status = py_trees.common.Status.RUNNING
                else:
                    if len(self.client_result) > 0:
                        #if we reach this point we have the result(s) 
                        #so we can make the leaf terminate
                        self.result_data = self.client_result.popleft()["data"]
                        new_status = py_trees.common.Status.SUCCESS
                    else:
                        #if we are here it means that we dont have the result yet, so
                        #do we have to wait or something went wrong?
                        #not sure about the followings lines, see row 408 of sequential_pattern.py
                        if(self.speaker_service.state == State.FAILED):
                            self.blackboard_tts.result_message = State.FAILED
                            new_status = py_trees.common.Status.FAILURE
                        else:
                            new_status = py_trees.common.Status.RUNNING
            else:
                #the state is either "RUNNING" or "FAILURE" so we have to do in both cases:
                new_status = self.blackboard_tts.result_message
            
        self.logger.debug("%s.update()[%s]--->[%s]" % (self.__class__.__name__, self.status, new_status))
        return new_status

        

    def terminate(self, new_status):
        """
        When is this called?
           Whenever your behaviour switches to a non-running state.
            - SUCCESS || FAILURE : your behaviour's work cycle has finished
            - INVALID : a higher priority branch has interrupted, or shutting down
        """
        if(new_status == py_trees.common.Status.INVALID):
            #TODO 
            #do the code for handling interuptions
            if(self.mode):
                pass
            else:
                pass
        else:
            #do the code for the termination of the leaf (SUCCESS || FAILURE)
            self.client_result = deque()

        self.logger.debug("%s.terminate()[%s->%s]" % (self.__class__.__name__, self.status, new_status))

    def _result_callback(self, result):
        """ Recieve and store result with timestamp """
        self.logger.debug("The result of the request has been received")
        self.logger.debug(
            f"The result callback message from {result['service']} was {len(result['message'])} long"
        )
        self.client_result.append(
            {"data": result["message"]}
        )
        # TODO add handling of errors and continue=False
        return

    def _feedback_callback(self, feedback):
        """ Feedback is currently just logged """
        self.logger.debug("The feedback recieved is %s." % feedback)
        # Check if the state is end, stop the behavior pattern
        # if feedback["state"] == State.END:
        #    self.end_pattern = True
        return
