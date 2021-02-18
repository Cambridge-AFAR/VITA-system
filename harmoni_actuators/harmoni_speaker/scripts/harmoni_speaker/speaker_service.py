#!/usr/bin/env python3

# Common Imports
import rospy, rospkg, roslib

from harmoni_common_lib.constants import State, ActuatorNameSpace
from harmoni_common_lib.service_server import HarmoniServiceServer
from harmoni_common_lib.service_manager import HarmoniServiceManager
import harmoni_common_lib.helper_functions as hf


# Specific Imports
from audio_common_msgs.msg import AudioData
import numpy as np

# import wget
import contextlib
import ast
import wave
import os


class SpeakerService(HarmoniServiceManager):
    """This is a class representation of a harmoni_speaker service
    (HarmoniServiceManager). It is essentially an extended combination of the
    :class:`harmoni_common_lib.service_server.HarmoniServiceServer`
    and :class:`harmoni_common_lib.service_manager.HarmoniServiceManager` classes

    :param name: Name of the current service
    :type name: str
    :param param: input parameters of the configuration.yaml file
    :type param: from yaml
    """

    def __init__(self, name):
        """Constructor method: Initialization of variables and lex parameters + setting up"""
        super().__init__(name)
        self.audio_publisher = rospy.Publisher(
            "/audio/audio",
            AudioData,
            queue_size=1,
        )
        self.state = State.INIT
        self.rospack = rospkg.RosPack()
        return

    def do(self, data):
        """Publishes audio to the "/audio/audio" topic for the sound_play module

        Converts input audio from bytes or a local/network path to an audio msg.

        Args:
            data (str): This could be a string of:
                            - audio data
                            - path of local wav file
                            - link of wav audio file you want to download and heard from
        """
        duration = 0
        self.state = State.REQUEST
        self.actuation_completed = False
        try:
            if type(data) == str:
                if ".wav" in data:
                    data = self.file_path_to_audio_data(data)
                    duration = data["duration"]
                else:
                    data = ast.literal_eval(data)
            data = data["audio_data"]
            rospy.loginfo("Writing data for speaker")
            rospy.loginfo(f"length of data is {len(data)}")
            self.audio_publisher.publish(data)
            rospy.sleep(duration)
            self.state = State.SUCCESS
            self.actuation_completed = True
        except IOError:
            rospy.logwarn("Speaker failed: Audio appears too busy")
            self.state = State.FAILED
            self.actuation_completed = True
        return {"response": self.state}

    def file_path_to_audio_data(self, path):
        """Returns audio data from a local path or internet link
        TODO: Add wget to docker image

        Args:
            path (string): string of:
                            - local folder path
                            - link of audio file you want to listen to

        Returns:
            json: return an object with two fields:
                        - audio_data: string
                        - duration: int (duration of the file)
        """
        file_handle = path
        if "http" in path:
            url = path
            print("Beginning file download with wget module")
            file_handle = (
                self.rospack.get_path("harmoni_speaker") + "/temp_data/test.wav"
            )
            # wget.download(url, file_handle)
        data = np.fromfile(file_handle, np.uint8)[24:]  # Loading wav file
        data = data.astype(np.uint8).tostring()
        with contextlib.closing(wave.open(file_handle, "r")) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
            rospy.loginfo(f"The audio lasts {duration} seconds")
        if "http" in path:
            os.remove(file_handle)
        return {"audio_data": data, "duration": duration}


def main():
    service_name = ActuatorNameSpace.speaker.name
    name = rospy.get_param("/name_" + service_name + "/")
    test_id = rospy.get_param("/test_id_" + service_name + "/")
    try:
        rospy.init_node(service_name)
        service = hf.get_service_server_instance_id(service_name, test_id)
        s = SpeakerService(service)
        service_server = HarmoniServiceServer(name=service, service_manager=s)
        service_server.start_sending_feedback()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass


if __name__ == "__main__":
    main()
