#!/usr/bin/env python

# Importing the libraries
import rospy
import roslib
from action_server import HarmoniActionServer


class HardwareControl():

    def __init__(self, input_data):
        # Initialize variables
        self.input_data = input_data
        # Initialize server
        self.server = ActionServer()

    def setup(self, child):
        self.server.setup_server(child)
        return


class ExternalService(HarmoniActionServer):
    """An external service provider recieves some data which it will formulate
    into an API request of some cloud provider"""

    def __init__(self, name, service_manager):
        """
        Initialize web client, logical defaults, and publishers/subscribers
        Can optionally test connctivity with web services
        @name: the name of the external service, will be the name of the server
        @service_manager: service managers should have the following fuctionality:
            service_manger.test() # sends default message to server
            service_manager.request(data) # processes data and sends through API
            service_manager.reset_init() # Resets server to initial state

            service_manager.response_received = Bool # True if API returned a response
            service_manager.cont = Bool # Used if logic can dictate control flow
            service_manager.result_msg = String # 
        """
        self.name = name
        self.service_manager = service_manager

        success = self.service_manager.test()
        if success:
            rospy.loginfo("{name} has been successfully set up")
        else:
            rospy.logwarn("{name} has not been started")

        self.setup_server(name)

    def goal_received_callback(self, goal):
        """Currently not supporting sending data to external service except through optional_data"""
        super().goal_received_callback(goal)

        self.service_manager.request(goal.optional_data)  # status is in response_recieved, result in return_msg
        self.send_feedback("Processing")

        while not self.service_manager.response_received:
            if self.preemption_status():
                success = False
                rospy.Rate(10)

        if success:
            self.send_result(
                do_continue=self.service_manager.cont,
                message=self.service_manager.return_msg)
            self.service_manager.reset_init()
        return


class InternalService():
    """An Internal Service controls the behavior of a class that processes some
    data from a topic(s) and publishes it to a topic"""

    def __init__(self, name, service_manager):
        """
        Initialize, control flow of information through processing class
        @name: the name of the external service, will be the name of the server
        @service_manager: service managers should have the following fuctionality:
            service_manger.test() # sends default message to server
            service_manager.reset_init() # Resets server to initial state
            service_manager.start(rate) # Rate is communicated in optional data
            service_manager.stop()

            service_manager.status = Int # TODO Set up status class
        """
        self.name = name
        self.service_manager = service_manager

        success = self.service_manager.test()
        if success:
            rospy.loginfo("{name} has been successfully set up")
        else:
            rospy.logwarn("{name} has not been started")

        self.setup_server(name)
        while not rospy.is_shutdown:
            self.send_feedback(self.service_manager.status)
            rospy.Rate(.2)

    def goal_received_callback(self, goal):
        """Control flow through internal processing class"""
        super().goal_received_callback(goal)

        # TODO better case management here
        if goal.action_goal == "start_{self.name}":
            if goal.optional_data != "":
                self.service_manager.start(int(goal.optional_data))
            else:
                self.service_manager.start()
        elif goal.action_goal == "pause_{self.name}":
            self.service_manager.stop()
        elif goal.action_goal == "stop_{self.name}":
            self.service_manager.stop()
            self.service_manager.reset_init
        return


class HarwareReading():

    def __init__(self, data_type, topic):
        # Initialization of publisher info
        self.data_type = data_type
        self.topic = topic
        # Initialize server
        self.server = ActionServer()

    def setup(self, child):
        self.server.setup_server(child)
        return
