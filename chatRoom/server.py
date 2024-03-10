import json
import logging
import os
import socket
import struct
import traceback
from concurrent.futures import ThreadPoolExecutor
import common  # 导入写在lib里面的公共模块,代码在上面
import re

# 进行开启服务器等一系列操作
s = socket.socket()
ip_host = ('0.0.0.0', 8888)
s.bind(ip_host)
s.listen()
# 创建一个列表,用来保存客户端及其信息
c_list = []


def broadcast_user_list():
    # 获取当前所有用户的名字列表
    user_list = [client['name'] for client in c_list]
    # 创建一个包含用户列表的字典
    dic = {'user_list': user_list, 'command': 'update_user_list'}
    # 广播给所有连接的客户端
    for client in c_list:
        common.send_dic(client['client'], dic)


def get_send_msg(c, addr, c_list):
    try:
        while True:
            dic = common.get_dic(c)
            print(dic)
            if dic['msg'] == 'end':
                # 用户请求断开连接
                for i in c_list:
                    if i['addr'] == addr:
                        c_list.remove(i)
                broadcast_user_list()
                exit_msg = f"User {name} exit."
                for i in c_list:
                    common.send_dic(i['client'], {'msg': exit_msg, 'name': 'Server', 'private': False})
                break

            elif dic['msg'] == 'sendfile':
                frecipient_name = dic['recipient']
                fsender_name = dic['name']
                file_path = receive_file(c, addr)
                frecipient_found = False

                for i in c_list:
                    if i['name'] == frecipient_name:
                        frecipient_found = True
                        _client = i['client']
                        _dic = {'command': 'sendfile', 'recipient': frecipient_name, 'sender': fsender_name,
                                'path': file_path, 'filename': os.path.basename(file_path)}
                        common.send_dic(_client, _dic)

                        sp = ThreadPoolExecutor()
                        sp.submit(send_file, _client, file_path)
                        # send_file(_client, file_path)
                        break
                if not frecipient_found:
                    # 指定的接收者不存在
                    warning_msg = f"User {frecipient_name} not found."
                    common.send_dic(c, {'msg': warning_msg, 'name': 'Server', 'private': True})

            elif dic['msg'] == 'withdraw':
                for i in c_list:
                    _client_ = i['client']
                    _dic_ = {'command': 'withdraw'}

                    common.send_dic(_client_, _dic_)

            elif 'private' in dic and dic['private'] == True and 'recipient' in dic:
                # 处理私聊消息
                recipient_name = dic['recipient']
                sender_name = dic['name']

                if recipient_name == sender_name:
                    # 发送者尝试给自己发送私聊消息
                    warning_msg = "Cannot send a private message to yourself."
                    common.send_dic(c, {'msg': warning_msg, 'name': 'Server', 'private': True})
                    continue

                recipient_found = False
                for i in c_list:
                    if i['name'] == recipient_name:
                        recipient_found = True
                        # 找到接收者并发送私聊消息

                        common.send_dic(i['client'], dic)
                        break

                if not recipient_found:
                    # 指定的接收者不存在
                    warning_msg = f"User {recipient_name} not found."
                    common.send_dic(c, {'msg': warning_msg, 'name': 'Server', 'private': True})
            else:
                # 群聊消息
                print(c_list)
                for i in c_list:
                    if i['addr'] != addr:
                        common.send_dic(i['client'], dic)
                        print(f"{dic}\n2")
    except Exception as e:
        logging.error(traceback.format_exc())
        pass


def send_file(c_client, file_path):
    try:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        file_info = {'filename': file_name, 'filesize': file_size}
        file_info_json = json.dumps(file_info)

        # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # c.connect((server_host, server_port))

        # 发送文件信息的长度和文件信息
        c_client.sendall(str(len(file_info_json)).encode('utf-8').ljust(10, b'\x00'))
        c_client.sendall(file_info_json.encode('utf-8'))

        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                c_client.sendall(chunk)
        print(f"Sent {file_name}")
    except Exception as e:
        print(f"Failed to send file: {e}")


def receive_file(connection, address):
    # 接收文件信息的长度
    info_length_str = connection.recv(10).decode('utf-8').rstrip('\x00')
    info_length = int(info_length_str)

    print(1)

    # 接收文件信息
    file_info_json = connection.recv(info_length).decode('utf-8')
    file_info = json.loads(file_info_json)
    file_name = file_info['filename']
    file_size = file_info['filesize']

    # 准备接收文件内容
    new_filename = os.path.join('/home/jude/chatRoom/sever_files', file_name)
    print(new_filename)
    with open(new_filename, 'wb') as file:
        remaining = file_size
        while remaining:
            chunk_size = 4096 if remaining >= 4096 else remaining
            chunk = connection.recv(chunk_size)
            if not chunk: break  # 连接关闭
            file.write(chunk)
            remaining -= len(chunk)
        # print(f"Received {file_name} from {address}.")

    return new_filename


while True:
    # 用线程池,进行多次连接
    print('客户端等待连接')
    c, addr = s.accept()
    print('%s连接了服务器' % addr[1])
    name = c.recv(1024).decode('utf-8')  # 进行第一次接受,接受客户端的名字,为私聊的功能做准备
    c_dic = {'addr': addr, 'client': c, 'name': name}  # 将客户端的信息保存在字典中
    c_list.append(c_dic)  # 将字典加入列表
    broadcast_user_list()  # 每当新用户加入时，更新所有客户端的用户列表
    for i in c_list:
        common.send_dic(i['client'], {'msg': f"welcome {c_dic['name']}", 'name': 'Server', 'private': False})
    t = ThreadPoolExecutor()
    t.submit(get_send_msg, c, addr, c_list)
