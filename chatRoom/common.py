import  struct, json
import threading
import tkinter

import cv2
from PIL import Image, ImageTk


def get_dic(c):
    try:
        # 首先接收数据长度
        dic_length_bytes = c.recv(8)
        if not dic_length_bytes:
            return {'msg': 'end'}
        dic_length = struct.unpack('q', dic_length_bytes)[0]

        # 接收所有数据
        data = b''
        while len(data) < dic_length:
            packet = c.recv(dic_length - len(data))
            if not packet:
                return {'msg': 'end'}
            data += packet

        dic_json = data.decode('utf-8')

        dic = json.loads(dic_json)
        return dic
    except Exception as e:
        print(f"Error during data reception: {e}")
        return {'msg': 'end'}


def send_dic(c, dic, chunk_size=4096):
    dic_json = json.dumps(dic)
    dic_json_bytes = dic_json.encode('utf-8')
    dic_json_length = len(dic_json_bytes)
    c.send(struct.pack('q', dic_json_length))

    # 分块发送数据
    for i in range(0, dic_json_length, chunk_size):
        c.send(dic_json_bytes[i:i + chunk_size])

class CameraPreviewWindow(tkinter.Toplevel):
    def __init__(self, master, camera_id):
        super().__init__(master)
        self.title("Camera Preview")
        self.camera_id = camera_id
        try:

            self.cap = cv2.VideoCapture(camera_id)

            if not self.cap.isOpened():
                raise ValueError("Camera could not be opened.")

        except ValueError as e:

            tkinter.messagebox.showerror("Error", str(e))

            self.destroy()

            return
        self.photo_label = tkinter.Label(self)
        self.photo_label.pack(fill=tkinter.BOTH, expand=True)
        self.create_widgets()
        self.start_preview()

    def create_widgets(self):
        # 创建拍照按钮
        self.take_photo_button = tkinter.Button(self, text='Take Photo', command=self.take_photo)
        self.take_photo_button.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        # 创建保存照片路径的输入框
        self.save_path_entry = tkinter.Entry(self)
        self.save_path_entry.insert(0, 'photo.jpg')
        self.save_path_entry.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        # 创建保存照片的按钮
        self.save_photo_button = tkinter.Button(self, text='Save Photo', command=self.save_photo)
        self.save_photo_button.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        # 创建关闭按钮
        self.close_button = tkinter.Button(self, text='Close', command=self.destroy)
        self.close_button.pack(side=tkinter.BOTTOM, fill=tkinter.X)

    def start_preview(self):
        # 启动预览线程
        thread = threading.Thread(target=self.preview_loop, daemon=True)
        thread.start()

    def preview_loop(self):
        try:
            while True:
                ret, frame = self.cap.read()
                if ret:
                    image_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    tk_image = ImageTk.PhotoImage(image_pil)

                    # 更新预览标签的图像
                    self.photo_label.config(image=tk_image)
                    self.photo_label.image = tk_image
                self.update_idletasks()
        except RuntimeError:
            pass  # 忽略Tkinter的线程错误

    def take_photo(self):
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            # print("Photo taken!")

    def save_photo(self):
        save_path = self.save_path_entry.get()
        if self.current_frame is not None:
            cv2.imwrite(save_path, self.current_frame)
            # print(f"Photo saved to {save_path}")

    def destroy(self):

        # 关闭摄像头

        self.cap.release()

        # 调用父类的destroy方法关闭窗口

        super().destroy()


def open_camera_preview(master):
    camera_preview_window = CameraPreviewWindow(master, 0)  # 假设使用默认摄像头
    camera_preview_window.grab_set()  # 确保窗口获得焦点
    camera_preview_window.lift()  # 将窗口提到所有窗口的前面
