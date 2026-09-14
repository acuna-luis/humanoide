#!/usr/bin/env python3
"""Bounded passive RGB/cloud/TF capture inside the existing ROS container."""
import base64
import json
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, PointCloud2
from shm_msgs.msg import Image2m
from tf2_ros import Buffer, TransformListener


def main():
    rclpy.init(); node=rclpy.create_node('entry_scene_passive_timestamped')
    buffer=Buffer();listener=TransformListener(buffer,node);latest={};subs=[]
    def decode(value):return bytes(value.data[:value.size]).decode(errors='strict')
    def record(kind,message):latest[kind]=(message,time.monotonic_ns())
    for kind,typ,topic in [('head',Image2m,'/sensor/camera/stereo/color/raw'),
                           ('cloud',PointCloud2,'/sensor/camera/stereo/pointcloud/raw')]:
        subs.append(node.create_subscription(typ,topic,lambda m,k=kind:record(k,m),qos_profile_sensor_data))
    subs.append(node.create_subscription(CameraInfo,'/sensor/camera/stereo/color/info',
        lambda m:record('camera',m),QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,
                                            reliability=ReliabilityPolicy.RELIABLE)))
    result=dict(physical_approval=False,movement_commands=0,installations=0)
    def stamp(message):return int(message.header.stamp.sec)*1000000000+int(message.header.stamp.nanosec)
    deadline=time.monotonic()+9
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.1)
        if len(latest)!=3:continue
        head,cloud,camera=[latest[k][0] for k in ('head','cloud','camera')]
        stamps={k:stamp(m) for k,(m,_) in latest.items()}
        if min(stamps['head'],stamps['cloud'])<=0 or abs(stamps['head']-stamps['cloud'])>50000000:continue
        frame=cloud.header.frame_id
        if decode(head.header.frame_id)!=frame or camera.header.frame_id!=frame:continue
        try:tf=buffer.lookup_transform('base_link',frame,Time(nanoseconds=stamps['cloud']))
        except Exception:continue
        result.update(source_stamps_ns=stamps,receive_monotonic_ns={k:v[1] for k,v in latest.items()},
            image_cloud_stamp_difference_ms=abs(stamps['head']-stamps['cloud'])/1e6,
            synchronization_scope='reported header timestamps only; sensor timing/calibration not certified',
            head=dict(width=head.width,height=head.height,step=head.step,encoding=decode(head.encoding),
                      frame_id=decode(head.header.frame_id),data_b64=base64.b64encode(bytes(head.data[:head.step*head.height])).decode()),
            cloud=dict(width=cloud.width,height=cloud.height,point_step=cloud.point_step,row_step=cloud.row_step,
                       is_bigendian=cloud.is_bigendian,frame_id=frame,
                       fields=[[f.name,f.offset,f.datatype,f.count] for f in cloud.fields],
                       data_b64=base64.b64encode(bytes(cloud.data)).decode()),
            camera=dict(width=camera.width,height=camera.height,frame_id=camera.header.frame_id,
                        k=list(camera.k),p=list(camera.p),r=list(camera.r),d=list(camera.d),
                        distortion_model=camera.distortion_model),
            camera_to_base=dict(parent=tf.header.frame_id,child=tf.child_frame_id,
                translation=[getattr(tf.transform.translation,k) for k in 'xyz'],
                quaternion_xyzw=[getattr(tf.transform.rotation,k) for k in 'xyzw'],
                stamp_ns=stamp(tf)))
        result['capture_complete']=True;break
    else:result.update(capture_complete=False,received_topics=list(latest),reason='NO_MATCHED_RGB_CLOUD_AND_TIMESTAMPED_TF_WITHIN_BUDGET')
    print('SNAPSHOT_JSON='+json.dumps(result));node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
