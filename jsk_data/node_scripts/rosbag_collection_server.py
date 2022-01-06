#!/usr/bin/env python

import argparse
import uuid
import os
import os.path as osp
import subprocess
import signal
import time

import rospkg
import rospy
import dynamic_reconfigure.server
from std_srvs.srv import Trigger
from std_srvs.srv import TriggerResponse

from jsk_data.cfg import DataCollectionServerConfig

def create_rosbag_command(topic_names, save_dir, filename, postfix_style='empty'):
    if postfix_style == 'time':
        postfix = '-' + time.strftime("%Y%m%d%H%M%S")
    elif postfix_style == 'uuid':
        postfix = '-' + str(uuid.uuid4())[-6:]
    else:
        assert postfix_style == 'empty'
        postfix == ''
    filename_raw, ext = os.path.splitext(filename)

    filename = os.path.join(save_dir,
            '{0}{1}{2}'.format(filename_raw, postfix, ext))

    cmd_rosbag = ['rosbag', 'record']
    cmd_rosbag.extend(topic_names)
    cmd_rosbag.extend(['--output-name', filename])
    rospy.loginfo('subprocess cmd: {}'.format(cmd_rosbag))
    return cmd_rosbag

class RosbagCollectionServer(object):
    """Server to collect data.

      <rosparam>
        save_dir: ~/.ros
        fname: sequence.bag
        postfix_style: empty
        topics:
          - name: /camera/rgb/image_raw
          - name: /camera/depth/image_raw
      </rosparam>

    """
    def __init__(self):
        dynamic_reconfigure.server.Server(
            DataCollectionServerConfig, self.reconfig_cb)
        self.fname = rospy.get_param('~fname', 'sequence.bag')
        self.topics = rospy.get_param('~topics', [])
        self.process = None

        self.start_server = rospy.Service(
            '~start_request', Trigger, self.start_service_cb)
        self.end_server = rospy.Service(
            '~end_request', Trigger, self.end_service_cb)

    def reconfig_cb(self, config, level):
        self.save_dir = osp.expanduser(config['save_dir'])
        if not osp.exists(self.save_dir):
            os.makedirs(self.save_dir)
        return config

    def start_service_cb(self, req):
        if self.process is not None:
            rospy.logwarn('A process {} is already running.'.format(self.process.pid))
            return TriggerResponse(success=False)
        cmd = create_rosbag_command(self.topics, self.save_dir, self.fname)
        self.process = subprocess.Popen(cmd)
        return TriggerResponse(success=True)

    def end_service_cb(self, req):
        if self.process is None:
            rospy.logwarn('There is no process to kill')
            return TriggerResponse(success=False)

        os.kill(self.process.pid, signal.SIGKILL)
        self.process = None
        return TriggerResponse(success=True)

if __name__=='__main__':
    rospy.init_node('rosbag_collection_server')
    server = RosbagCollectionServer()
    rospy.spin()
