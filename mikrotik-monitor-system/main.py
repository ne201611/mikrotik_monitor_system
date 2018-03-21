# coding:utf-8
from routeros import login
import requests,redis,datetime,time,configparser
from daemonize import Daemonize

def w_redis(key,value):
    r = redis.Redis(host='192.168.103.137', port=6379, db=0)
    r.set(key, value)

def r_redis(key):
    r = redis.Redis(host='192.168.103.137', port=6379, db=0)
    return r.get(key)

def send_message(message):
    content = message
    url = "http://172.31.1.145:30180/send/"
    payload = {'content': content}
    r = requests.post(url, json=payload)
    if (r.status_code != 200):
        print("消息发送失败.")

def entry():
    while 1:
        hosts_info = configparser.ConfigParser()
        hosts_info.read('hosts_info.ini')
        for nodename in hosts_info.sections():
            ip = hosts_info[nodename]['ip']
            dc = hosts_info[nodename]['dc']
            device = nodename
            username = hosts_info[nodename]['username']
            password = hosts_info[nodename]['password']
            try:
                for interface in eval(hosts_info[nodename]['interfaces']):
                    interface_name = interface
                    routeros = login(username, password, ip)
                    result = routeros.query('/ip/arp/print').equal(interface=interface_name)
                    event = {
                        # 'dt': (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M'),
                        'interface': interface_name,
                        'status': ''
                    }
                    is_success = ip + interface_name + "is_success"
                    # is_success_result = 1   #接口状态ok
                    is_noticed = ip + interface_name + "is_noticed"
                    # is_noticed_result = 0   #未发送短信通知
                    message = "数据中心:%s\n设备:%s\n线路:%s\n状态:" \
                              % (dc,nodename, event['interface'])
                    if (len(result) == 0):  #超出arp老化时间，条目不存在
                        event['status'] = "abnormal"
                        message = message + event['status']
                        w_redis(is_success,'n')
                        if (r_redis(is_noticed) == None or r_redis(is_noticed).decode('utf-8') == 'n'):
                            w_redis(is_noticed,'y')
                            send_message(message)
                    else:                   #在arp老化时间内，判断mac-address是否还在
                        is_exist = result[0].__contains__('mac-address')
                        if(is_exist == True and r_redis(is_success) != None and r_redis(is_success).decode('utf-8') == 'n'):
                            event['status'] = "ok"
                            message = message + event['status']
                            w_redis(is_success,'y')
                            w_redis(is_noticed,'n')
                            send_message(message)
                        elif(is_exist == False):
                            w_redis(is_success, 'n')
                            event['status'] = "abnormal"
                            message = message + event['status']
                            if (r_redis(is_noticed) == None or r_redis(is_noticed).decode('utf-8') == 'n'):
                                w_redis(is_noticed, 'y')
                                send_message(message)
                    routeros.close()
            except Exception as e:
                print("%s.连接失败."%(nodename))
        time.sleep(30)
def test():
    while True:
        print("hello")

if __name__ == '__main__':
    # line_names = [{
    #     'dc':'gs',
    #     'devices':[{'ip':'192.168.10.235','interfaces':['ether1-ctc',' ether4-cmcc','ether6-cnc']}]
    # }]
    # pid = "/mnt/mikrotik-monitor-system/mikrotik-monitor.pid"
    # daemon = Daemonize(app="mikrotik", pid=pid, action=entry)
    # daemon.start()
    entry()