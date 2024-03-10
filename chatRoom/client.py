import curses
import json
import socket
import threading
import tkinter
import logging
import traceback

import cv2
from PIL import ImageTk
import os
import common
from concurrent.futures import ThreadPoolExecutor
import re
import PIL.Image
from tkinter import filedialog

# 使用Event来控制线程
shutdown_event = threading.Event()
logging.basicConfig(filename='/home/jude/chatRoom/test.log', level=logging.DEBUG, filemode='w')

cap = None
root = None
lmain = None
btn_take_photo = None
btn_save = None
btn_quit = None


# 拍照功能
def take_photo():
    global cap
    ret, frame = cap.read()
    if ret:
        show_image(frame)


# 保存照片功能
def save_photo():
    global cap
    ret, frame = cap.read()
    if ret:
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("All files", "*.*")])
        if file_path:
            cv2.imwrite(file_path, frame)


# 显示摄像头预览
def show_camera_feed():
    global cap, lmain
    ret, frame = cap.read()
    if ret:
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        lmain.imgtk = imgtk
        lmain.configure(image=imgtk)
        lmain.after(10, show_camera_feed)  # 每10毫秒更新一次


# 显示单帧图像（用于拍照预览）
def show_image(frame):
    global root, lmain
    cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = PIL.Image.fromarray(cv2image)
    imgtk = ImageTk.PhotoImage(image=img)
    photo_label = tkinter.Label(root, image=imgtk)
    photo_label.image = imgtk
    photo_label.pack()


# Tkinter退出功能

def on_quit():
    global cap, root
    cap.release()  # 释放摄像头资源
    root.destroy()  # 关闭Tkinter窗口


# Tkinter主窗口和按钮设置

def create_tkinter_ui():
    global cap, root, lmain, btn_take_photo, btn_save, btn_quit

    cap = cv2.VideoCapture(-1)  # 打开摄像头/

    if not cap.isOpened():
        messages.append("无法打开摄像头")
        display()
        return

    root = tkinter.Tk()
    root.title("摄像头拍照与保存")
    root.geometry("640x480")  # 设置窗口大小以匹配摄像头预览
    lmain = tkinter.Label(root)
    lmain.pack()
    btn_take_photo = tkinter.Button(root, text="拍照", command=take_photo)
    btn_take_photo.pack(side="bottom", fill="x")
    btn_save = tkinter.Button(root, text="保存照片", command=save_photo)
    btn_save.pack(side="bottom", fill="x")
    btn_quit = tkinter.Button(root, text="退出", command=on_quit)
    btn_quit.pack(side="bottom", fill="x")
    # 开始实时显示摄像头预览
    show_camera_feed()
    # 进入Tkinter事件循环
    root.mainloop()


# 终端UI中调用拍照功能的函数

def terminal_ui_handler(msg):
    try:
        if msg == 'takephoto':
            # 在新线程中启动Tkinter拍照UI
            threading.Thread(target=create_tkinter_ui).start()
    except Exception as e:
        messages.append(e)
        display()


'''------------------------------------------------login and socket init-----------------------------------------------------'''


def safe_addstr(win, y, x, string, *args, **kwargs):
    """安全地向窗口添加字符串，防止超出边界"""
    maxy, maxx = win.getmaxyx()
    if y >= maxy - 1:  # 预留最后一行
        return
    if x >= maxx - 1:  # 预留最后一列
        return
    if x + len(string) >= maxx:
        string = string[:maxx - x - 1]
    win.addstr(y, x, string, *args, **kwargs)


def is_valid_ip(ip):
    # 简单的正则表达式来验证IP地址格式
    if (ip != ''):
        pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        return pattern.match(ip) is not None
    else:
        return False


def is_valid_port(port):
    # 检查端口号是否在有效范围内
    try:
        port = int(port)
        return (0 < port < 65536) or (port != '')
    except ValueError:
        return False


def draw_form(stdscr, prompt_list):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    for idx, prompt in enumerate(prompt_list):
        x = w // 2 - len(prompt) // 2
        y = h // 2 - len(prompt_list) + idx * 2
        safe_addstr(stdscr, y, x, prompt)
    stdscr.refresh()


def draw_warning(stdscr, msg):
    h, w = stdscr.getmaxyx()
    x = w // 2 - len(msg) // 2
    y = h - 3
    safe_addstr(stdscr, y, x, msg)
    stdscr.refresh()


def get_user_input(stdscr, prompt_list):
    inputs = {}
    h, w = stdscr.getmaxyx()
    for idx, prompt in enumerate(prompt_list):
        curses.echo()
        x = w // 2 - len(prompt) // 2 + len(prompt) + 1
        y = h // 2 - len(prompt_list) + idx * 2
        safe_addstr(stdscr, y, x, ": ")
        input_str = stdscr.getstr(y, x + 2, 20).decode('utf-8')
        inputs[prompt] = input_str
    curses.noecho()
    return inputs


'''------------------------------------------------win init-----------------------------------------------------'''
stdscr = curses.initscr()
# 初始化curses窗口
curses.start_color()
curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
curses.curs_set(1)

while True:
    stdscr.clear()
    prompt_list = ["IP Address", "Port", "Username"]
    draw_form(stdscr, prompt_list)
    user_inputs = get_user_input(stdscr, prompt_list)

    ip_address = user_inputs["IP Address"]
    port = user_inputs["Port"]
    name = user_inputs["Username"]

    c = socket.socket()

    if not is_valid_ip(ip_address):
        draw_warning(stdscr, "Invalid IP address. Press any key to retry...")
        stdscr.getch()
        continue

    if not is_valid_port(port):
        draw_warning(stdscr, "Invalid port number. Press any key to retry...")
        stdscr.getch()
        continue

    ip_host = (ip_address, int(port))

    try:
        # 尝试连接到服务器的逻辑
        # 如果连接失败，抛出异常
        safe_addstr(stdscr, 0, 0, "Attempting to connect...")
        stdscr.refresh()

        c.connect(ip_host)
        c.send(name.encode('utf-8'))
        break  # 连接成功，退出循环
    except Exception as e:
        draw_warning(stdscr, f"Connection failed Press any key to retry...")
        stdscr.getch()

stdscr = curses.initscr()
curses.curs_set(1)
stdscr.nodelay(0)  # 设置stdscr.getch()为阻塞模式
stdscr.timeout(-1)  # 禁用超时

height, width = stdscr.getmaxyx()
# 分割窗口
user_list_height = height - 3
user_list_width = int(width / 4)
chat_height = height - 3
chat_width = width - user_list_width
input_height = 3

user_list_win = curses.newwin(user_list_height, user_list_width, 0, 0)
chat_win = curses.newwin(chat_height, chat_width, 0, user_list_width)
input_win = curses.newwin(input_height, width, height - 3, 0)

messages = [f"welcome to chat_Room {name}"]

users = []
# 绘制用户列表
user_list_win.erase()
user_list_win.box()
user_list_win.addstr(0, int(user_list_width / 2) - 3, "Users")
for idx, user in enumerate(users):
    user_list_win.addstr(idx + 1, 1, user)
user_list_win.noutrefresh()

# 绘制聊天窗口
chat_win.erase()
chat_win.box()
chat_win.noutrefresh()

curses.curs_set(0)
for idx, msg in enumerate(messages):
    chat_win.addstr(idx + 1, 1, msg)
chat_win.noutrefresh()  # 更新聊天窗口但不立即刷新屏幕

# 注意：这里移动光标到输入窗口的操作需要在最后执行，并确保之后刷新输入窗口
input_win.move(1, 11)  # 移动光标到输入开始位置
input_win.noutrefresh()  # 标记输入窗口需要刷新，但不立即执行
curses.doupdate()  # 刷新屏幕，应用之前所有的noutrefresh()操作
# 准备输入窗口
input_win.erase()
input_win.box()
input_win.addstr(1, 1, "Send here: ")
input_win.noutrefresh()
curses.doupdate()

# 禁用echo并手动处理输入以支持删除等功能

input_win.move(1, 11)  # 移动光标到输入开始位置
input_win.refresh()

'''------------------------------------------------chat md-----------------------------------------------------'''


def send_msg(c, name):
    global msg
    private_mode = False
    recipient = ''  # private chat
    while not shutdown_event.is_set():
        curses.echo()
        if not private_mode:
            msg = input_win.getstr(1, 11, 60).decode('utf-8').strip()
            if msg.lower().startswith('sendto'):
                private_mode = True
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "Send to (username): ")
                input_win.move(1, 20)  # 将光标移动到输入框内的开始位置
                input_win.noutrefresh()
                curses.doupdate()

                recipient = input_win.getstr(1, 20, 20).decode('utf-8').strip()
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "Message: ")
                input_win.move(1, 11)  # 将光标移动到输入框内的开始位置
                input_win.noutrefresh()
                curses.doupdate()

                msg = input_win.getstr(1, 11, 60).decode('utf-8').strip()
                messages.append(f'You  (to {recipient}): {msg}')
                display()
            elif msg == 'end':
                dic = {'msg': msg, 'name': name, 'private': False}
                common.send_dic(c, dic)
                c.close()
                shutdown_event.set()
                curses.endwin()
                break
            elif msg == 'takephoto':
                terminal_ui_handler('takephoto')
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "Send here: ")
                input_win.move(1, 11)
                input_win.noutrefresh()
                curses.doupdate()
                
            elif msg == 'sendfile':
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "Send to (username): ")
                input_win.move(1, 20)  # 将光标移动到输入框内的开始位置
                input_win.noutrefresh()
                curses.doupdate()

                file_recipient = input_win.getstr(1, 20, 60).decode('utf-8').strip()
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "path: ")
                input_win.move(1, 6)  # 将光标移动到输入框内的开始位置
                input_win.noutrefresh()
                curses.doupdate()

                path = input_win.getstr(1, 6, 60).decode('utf-8').strip()
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "Send here: ")
                input_win.move(1, 11)  # 移动光标到输入开始位置
                input_win.noutrefresh()
                curses.doupdate()

                dic = {'msg': msg, 'recipient': file_recipient, 'path': path, 'name': name}
                common.send_dic(c, dic)
                try:
                    po = ThreadPoolExecutor()
                    po.submit(send_file,ip_address, port, path)
                    # send_file(ip_address, port, path)
                except Exception as e:
                    logging.error(e)
                    messages.append("File send error : {e}".format(e=e))
                    display()
                    pass
            elif msg == 'withdraw':
                dic = {'msg': msg}
                common.send_dic(c, dic)
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "Send here: ")
                input_win.move(1, 11)  # 移动光标到输入开始位置
                input_win.noutrefresh()
                curses.doupdate()
            else:
                dic = {'msg': msg, 'name': name, 'private': False}
                common.send_dic(c, dic)
                messages.append(f'You: {msg}')
                display()
                input_win.erase()
                input_win.box()
                input_win.addstr(1, 1, "Send here: ")
                input_win.move(1, 11)  # 将光标移动到输入框内的开始位置
                input_win.noutrefresh()
                curses.doupdate()
            curses.noecho()
        else:
            dic = {'msg': msg, 'name': name, 'recipient': recipient, 'private': True}
            common.send_dic(c, dic)
            private_mode = False  # 退出私聊模式
            input_win.erase()
            input_win.box()
            input_win.addstr(1, 1, "Send here: ")
            input_win.move(1, 11)  # 将光标移动到输入框内的开始位置
            input_win.noutrefresh()
            curses.doupdate()
            curses.noecho()


def get_msg(c):
    global users
    try:
        while not shutdown_event.is_set():

            dic = common.get_dic(c)

            if 'command' in dic and dic['command'] == 'update_user_list':
                users = dic['user_list']  # 更新在线用户列表
                user_list_win.erase()
                user_list_win.box()
                user_list_win.addstr(0, int(user_list_width / 2) - 3, "Users")
                for idx, user in enumerate(users):
                    user_list_win.addstr(idx + 1, 1, user)
                user_list_win.noutrefresh()
                # input_win.move(1, 11)  # 移动光标到输入开始位置
                curses.doupdate()
                # print('在线用户列表更新:', users)
                continue
            elif 'command' in dic and dic['command'] == 'sendfile':
                try:
                    logging.info('sendfile')
                    pool = ThreadPoolExecutor()
                    try:
                        pool.submit(receive_file,c, dic['recipient'])
                    except Exception as e:
                        logging.error(e)
                        pass
                    # receive_file(c, dic['recipient'])
                    save_prompt = f"Received file {dic['filename']} from {dic['sender']} has saved. "
                    messages.append(save_prompt)
                    display()
                except Exception as e:
                    logging.info(str(e))
            elif 'command' in dic and dic['command'] == 'withdraw':
                if messages:  # 检查列表是否为空
                    try:
                        messages.pop()  # 删除并返回列表的最后一个元素
                        withdraw_display()
                    except Exception as e:
                        logging.info(str(e))
            if 'private' in dic and dic['private'] == True:
                messages.append(f'{dic["name"]}(private):{dic["msg"]}')  # private message
            else:
                messages.append(f'{dic["name"]}:{dic["msg"]}')
            display()
            # input_win.move(1, 11)  # 移动光标到输入开始位置
    except Exception as e:
        logging.error(f"client {traceback.format_exc()}")
        pass


def receive_file(connection, name):
    # 接收文件信息的长度
    info_length_str = connection.recv(10).decode('utf-8').rstrip('\x00')
    info_length = int(info_length_str)

    # 接收文件信息
    file_info_json = connection.recv(info_length).decode('utf-8')
    file_info = json.loads(file_info_json)
    file_name = file_info['filename']
    file_size = file_info['filesize']

    # 准备接收文件内容
    new_filename = os.path.join(f'/home/jude/chatRoom/client_receive', file_name)

    logging.info(new_filename)
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


def send_file(server_host, server_port, file_path):
    try:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        file_info = {'filename': file_name, 'filesize': file_size}
        file_info_json = json.dumps(file_info)

        # 发送文件信息的长度和文件信息
        c.sendall(str(len(file_info_json)).encode('utf-8').ljust(10, b'\x00'))
        c.sendall(file_info_json.encode('utf-8'))
        try:
            with open(file_path, 'rb') as file:
                while True:
                    chunk = file.read(4096)
                    if not chunk:
                        break
                    c.sendall(chunk)
        except FileNotFoundError:
            messages.append("File not found")
            display()

        logging.info(f"Sent {file_name} to {server_host}:{server_port}")
    except Exception as e:
        # print(f"Failed to send file: {e}")

        logging.info(f"Failed to send file: {e}")
        pass


def display():
    for idx, msg in enumerate(messages):
        chat_win.addstr(idx + 1, 1, msg)
    chat_win.noutrefresh()  # 更新聊天窗口但不立即刷新屏幕

    # 注意：这里移动光标到输入窗口的操作需要在最后执行，并确保之后刷新输入窗口
    input_win.move(1, 11)  # 移动光标到输入开始位置
    input_win.noutrefresh()  # 标记输入窗口需要刷新，但不立即执行
    curses.doupdate()  # 刷新屏幕，应用之前所有的noutrefresh()操作

    # 确保在函数结束时，输入窗口也进行了刷新
    input_win.refresh()  # 确保输入窗口立即刷新，光标位置更新显示


def withdraw_display():
    chat_win.erase()  # 清除聊天窗口内容
    chat_win.box()  # 重新绘制窗口边框

    for idx, msg in enumerate(messages):
        chat_win.addstr(idx + 1, 1, msg)  # 重新显示更新后的消息列表

    chat_win.noutrefresh()  # 标记聊天窗口需要刷新，但不立即执行
    curses.doupdate()  # 刷新屏幕，应用之前所有的noutrefresh()操作

    # 确保在函数结束时，输入窗口也进行了刷新
    prepare_input_win()  # 准备输入窗口以供下一条消息输入


def prepare_input_win():
    input_win.erase()
    input_win.box()
    input_win.addstr(1, 1, "Send here: ")
    input_win.noutrefresh()
    # 显式地将光标移动到输入框内的开始位置
    input_win.move(1, 11)
    curses.doupdate()


prepare_input_win()

'''------------------------------------------------thread----------------------------------------------------'''

try:
    with ThreadPoolExecutor() as t:
        t.submit(send_msg, c, name)
        t.submit(get_msg, c)
except Exception as e:
    logging.error(e)
finally:
    shutdown_event.set()  # 确保设置了事件
    t.shutdown(wait=True)  # 等待所有线程结束
    curses.endwin()  # 最后恢复终端
