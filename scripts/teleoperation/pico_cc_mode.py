#!/usr/bin/env python3
"""Read Control Center work mode through its web RPC.

Uses Vision rosbridge, never the PC controller WebSocket. This CLI only reads status. The call() function requires caller-controlled scope.
"""
import argparse
import json
from pathlib import Path
import uuid
import websocket


def call(method, params):
    session='pico_v4_'+uuid.uuid4().hex[:12]
    ws=websocket.create_connection('ws://192.168.11.3:9090/',timeout=8)
    outgoing='/cc/api/out/'+session
    incoming='/cc/api/in/'+session
    def send(data):ws.send(json.dumps(data))
    def publish(topic,data):send(dict(op='publish',topic=topic,msg={'data':json.dumps(data)}))
    def receive():
        while True:
            packet=json.loads(ws.recv())
            if packet.get('topic')==outgoing:
                return json.loads(packet['msg']['data'])
    try:
        send(dict(op='subscribe',topic=outgoing,type='std_msgs/msg/String'))
        for topic in ('/cc/api/connect',incoming):
            send(dict(op='advertise',topic=topic,type='std_msgs/msg/String'))
        publish('/cc/api/connect',dict(api_id='ubt.walker.local_web',auth={'token':''},
            session=session,proto_version='1.0.0'))
        while True:
            message=receive()
            if message.get('method')=='cc.api.accept':break
            if message.get('method')=='cc.api.reject':raise RuntimeError('CC rejected session')
        publish(incoming,dict(jsonrpc='2.0',id=1,method=method,params=params))
        while True:
            message=receive()
            if message.get('id')==1:return message
    finally:
        try:publish(incoming,dict(jsonrpc='2.0',id=2,method='cc.api.disconnect',params={}))
        finally:ws.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',required=True,type=Path)
    args=p.parse_args()
    method='cc.api.status.get'
    params={'list':['workMode']}
    result=call(method,params)
    name='cc-status-work-mode.json'
    target=args.evidence/name
    if target.exists():
        target=args.evidence/(target.stem+'-'+uuid.uuid4().hex[:8]+'.json')
    target.write_text(json.dumps(dict(method=method,params=params,response=result),indent=2))
    print(json.dumps(result))
    return 1 if 'error' in result else 0


if __name__=='__main__':
    raise SystemExit(main())
