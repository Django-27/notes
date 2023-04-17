# coding: utf-8
import copy
import os
import time
import json
import tkinter as tk
import traceback
from threading import Lock
from tkinter import messagebox
from copy import deepcopy

import numpy as np
from PIL import ImageTk, Image
import myglog as glog
from drawer_dialog import DrawerDialog
from drawer_human import DrawerHuman
from drawer_video import DrawerVideo
from cos_helper import TCOSHelper

from settings import gateway_url, public_api, clientLog_api
from auth import request_get_with_auth, async_client_log
from settings import PREVIEW_IMAGE_INFO


# config = {'player_version': 2, 'host_video_graph': {'elements': {'G1': {'P': 10, 'NC': 15, 'ND': 3, 'NE': 3}, 'G2': {'Q': 10, 'NA': 10, 'NB': 10, 'S': 10}}, 'edge': {'G1': {'G1': 1}, 'G2': {'G1': 1}}, 'rules_in_order': ['fetch_p_actual_id_queue', 'fetch_qa_video_queue', 'fetch_act_video_queue', 'get_S_following_P', 'get_next_video_in_graph']}, 'play_np': {'probability': 0.8, 'continue': 0.97, 'max_time': 999}, 'canvas_size': {'w': 1080, 'h': 1920}, 'fps': 25, 'trans_speed': 1.5, 'drawers': [{'layer': 1.5, 'type': 'DrawerCamera', 'xywh': [0, 123, 1080, 600], 'camera_index': None}, {'layer': 8, 'type': 'DrawerNoise', 'xywh': [0, 0, 1080, 1920], 'rate': 0.01, 'clock_position': [0, 0, 300, 100], 'clock_background': [128, 128, 128, 20], 'fond_day_size': 22, 'fond_cur_size': 26, 'text_color': [255, 255, 255, 255]}, {'layer': 7, 'type': 'DrawerFullScreen', 'xywh': [0, 0, 1080, 1920]}, {'layer': 6, 'type': 'DrawerDynamicMaterial', 'xywh': [0, 0, 0, 0]}, {'layer': 5, 'type': 'DrawerDialogVideo', 'xywh': [540, 753, 440, 50], 'fans_label': '粉丝', 'ass_label': '助理', 'text_font': 'assets/SOURCEHANSANSCN-MEDIUM.OTF', 'text_font_size': 29, 'label_font': 'assets/SOURCEHANSANSCN-MEDIUM.OTF', 'label_font_size': 26, 'text_line_weight': 1.5, 'label_line_weight': 1.4, 'font_color': [255, 255, 255, 255], 'label_background_color': [219, 164, 45, 255], 'text_background_color': [100, 100, 100, 160]}, {'layer': 4, 'type': 'DrawerDialog', 'xywh': [120, 783, 302, 110], 'fans_label': '粉丝', 'ass_label': '助理', 'text_font': 'assets/SOURCEHANSANSCN-MEDIUM.OTF', 'text_font_size': 29, 'label_font': 'assets/SOURCEHANSANSCN-MEDIUM.OTF', 'label_font_size': 26, 'text_line_weight': 1.5, 'label_line_weight': 1.4, 'font_color': [255, 255, 255, 255], 'label_background_color': [219, 164, 45, 255], 'text_background_color': [100, 100, 100, 80]}, {'layer': 3, 'type': 'DrawerStaticImage', 'xywh': [0, 1170, 1080, 750], 'image_path': 'assets/product.png'}, {'layer': 2, 'type': 'DrawerHuman', 'debug': False, 'xywh': [-255, 322, 1776, 1332], 'loop_sync_type': 'precise_align', 'currentRate': 1.6442307692307692}, {'layer': 1, 'type': 'DrawerVideo', 'xywh': [0, 123, 1080, 600]}, {'layer': 0, 'type': 'DrawerStaticImage', 'xywh': [0, 0, 1080, 1920], 'image_path': 'assets/live_room_background.png'}]}

config = {}  # test
g_preview_img = None


class LongPressButton(tk.Button):
    def __init__(self, *args, **kwargs):
        self.parent = kwargs.pop('parent')
        tk.Button.__init__(self, *args, **kwargs)
        self.text = kwargs.get("text")

        self.lock = Lock()
        self.pressed = False  # 按钮是否按下，亦用于长按判断
        self.pre_second = 3   # 一秒内执行次数
        self.customer_bind()

    def customer_bind(self):
        self.bind('<ButtonPress-1>', lambda name: self.on_button_down(
            event=self, name=self.text))
        self.bind('<ButtonRelease-1>', lambda name: self.on_button_up(
            event=self, name=self.text))

    def do_position_config(self, name):
        if (not self.parent) or (not hasattr(self.parent, "position_config")):
            return

        with self.lock:
            self.parent.position_config(name)

    def on_button_down(self, event, name, first=1):
        if first:
            self.pressed = True
        if self.pressed:
            if name in ["↑", "↓", "←", "→", "大", "小"]:
                self.do_position_config(name)
            self.after(1000 // self.pre_second, lambda: self.on_button_down(0, name, False))

    def on_button_up(self, event, name):
        self.pressed = False


class ConfigureFunctions:

    def __init__(self, parent):
        self.parent = parent
        self.max_width = 1080
        self.max_height = 1920
        self.canva_width, self.canva_height = PREVIEW_IMAGE_INFO
        self.resolution_base = 1080
        self.width_step = None
        self.height_step = None
        self.zoom_factor = None

        self.step = 5                   # 一次移动的5个像素
        self.time_limit = 5             # 固定时间内只能修改一次
        self.boundary_limit = 20        # 距离边界最小距离

        self.first_time = True          # 第一次不限制时间
        self.config_time = time.time()  # 比较修改时间

    def init_width_height_zoom(self, drawer_config):
        _canvas_size = (drawer_config['canvas_size']['h'], drawer_config['canvas_size']['w'], 3)
        resolution = os.environ.get("RESOLUTION") or 540
        zoom_factor = float(int(resolution) / 1080.)
        display_canvas = (int(_canvas_size[0]*zoom_factor), int(_canvas_size[1]*zoom_factor), 3)
        self.max_width = display_canvas[1]
        self.max_height = display_canvas[0]
        self.zoom_factor = zoom_factor

    def init_drawer_config_info(self, drawer_config, drawer_name, src=False):
        data = None
        if drawer_config and "drawers" in drawer_config:
            for item in drawer_config["drawers"]:
                if item["type"] == drawer_name:
                    data = copy.deepcopy(item)
                    # 与 os.environ['RESOLUTION'] 完成转换
                    if not src:
                        data['xywh'] = [int(val * self.zoom_factor) for val in item['xywh']]
                    break
        return data


class DrawerDialogVideoConfigure(ConfigureFunctions):
    name = 'DrawerDialogVideo Configure'
    short_name = 'DrawerDialogVideo'

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.init_width_height_zoom(self.parent.config_data)
        self.src_config = self.init_drawer_config_info(self.parent.config_data, self.short_name, src=True)
        self.dst_config = self.init_drawer_config_info(self.parent.config_data, self.short_name)
        self.dst_xywh = self.dst_config['xywh'] if self.dst_config and 'xywh' in self.dst_config else {}
        if self.dst_xywh[0] <= self.boundary_limit:
            self.dst_xywh[0] = self.boundary_limit + 1
            self.dst_config["xywh"][0] = self.boundary_limit + 1

        self.image_label = tk.Label(self.parent.frame_preview)
        self.image_label.config({'image': None})

        self.lalel_const = "调整评论位置："
        self.label1 = None
        self.label_var = tk.StringVar(value="")

        self.cur_pil_frame = None
        self.drawer = DrawerDialog(config=self.src_config)
        self.create_widgets()
        self.render_preview()
        self.render_label_tip()

    def render_label_tip(self):
        s = "{}[{}, {}]".format(self.lalel_const, self.dst_xywh[0], self.dst_xywh[1])
        self.label_var.set(s.ljust(20))

    def render_preview(self):
        self.drawer.update_text(qtext=None, atext=None, qa_text='你好主播')
        self.drawer.worker_process()
        self.cur_pil_frame = self.drawer.get_pil_frame()
        if self.cur_pil_frame is not None:
            global g_preview_img
            w, h = self.cur_pil_frame.size
            ww, hh = self.canva_width / self.max_width * w, self.canva_height / self.max_height * h
            g_preview_img = ImageTk.PhotoImage(self.cur_pil_frame.resize((int(ww), int(hh))))
            self.image_label.config({'image': g_preview_img})
            x = int(self.canva_width / self.max_width * self.dst_xywh[0])
            y = int(self.canva_height / self.max_height * self.dst_xywh[1])
            self.image_label.place(x=x, y=y)
            glog.info(f"更新 {self.short_name}： {self.dst_config['xywh']} -> {self.dst_xywh} ")

    def position_config(self, text):
        self.render_preview()
        if self.dst_xywh:
            x, y, w, h = self.dst_xywh
            canvas_zoom = self.canva_width / self.max_width
            image_width, image_height = self.cur_pil_frame.size
            if text == "↑":
                if (y <= self.boundary_limit) or (y - self.step <= 0):
                    return
                y -= self.step
            elif text == "↓":
                if y + image_height + self.step + self.boundary_limit >= self.max_height:
                    return
                y += self.step
            elif text == "←":
                if (x - self.step <= self.boundary_limit) or x - self.step <= 0:
                    return
                x -= self.step
            elif text == "→":
                if x + image_width + self.step + self.boundary_limit >= self.max_width:
                    return
                x += self.step
            self.dst_xywh = [x, y, w, h]
            self.render_preview()
        self.render_label_tip()

    def submit_configure(self):
        rtn = self.parent.do_config_update(
            self.dst_config, self.dst_xywh, self.zoom_factor,
            self.short_name, self.config_time, self.first_time, self.time_limit
        )
        if rtn:
            self.config_time = time.time()
        self.first_time = False

    def create_widgets(self):
        btn_up = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="↑")
        btn_up.grid(row=0, column=1)

        btn_down = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="↓")
        btn_down.grid(row=2, column=1)

        btn_left = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="←")
        btn_left.grid(row=1, column=0)

        btn_right = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="→")
        btn_right.grid(row=1, column=2)

        # label1 = tk.Label(self.parent.frame_right, text="调整模拟回答位置")
        self.label1 = tk.Label(self.parent.frame_right, textvariable=self.label_var, width=30, pady=15)
        self.label1.grid(row=3, column=0, columnspan=3)

        empty_label = tk.Label(self.parent.frame_right)
        empty_label.grid(row=4, column=0, columnspan=3)

        btn = tk.Button(self.parent.frame_right, text="提交配置", command=self.submit_configure)
        btn.grid(row=4, column=1, pady=25)


class DrawerHumanConfigure(ConfigureFunctions):
    name = 'DrawerHuman Configure'
    short_name = 'DrawerHuman'

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.step = 10  # 一次移动的10个像素
        self.time_limit = 10  # 固定时间内只能修改一次
        self.boundary_limit = 100  # 距离边界最小距离
        self.scale_step = 0.01  # 滑动条步长

        self.init_width_height_zoom(self.parent.config_data)
        self.src_config = self.init_drawer_config_info(self.parent.config_data, self.short_name, src=True)
        self.dst_config = self.init_drawer_config_info(self.parent.config_data, self.short_name)
        self.dst_xywh = self.dst_config['xywh'] if self.dst_config and 'xywh' in self.dst_config else {}

        self.image_label = tk.Label(self.parent.frame_preview)
        self.image_label.config({'image': None})
        self.image_label.place(x=0, y=0)

        self.lalel_position_const = "调整主播位置："
        self.label_position = None
        self.label_position_var = tk.StringVar(value="")

        self.label_zoom_const = "调整主播大小："
        self.label_zoom = None
        self.label_zoom_var = tk.StringVar(value="")

        self.scale = None
        self.scale_min, self.scale_max = 0.5, 2  # 缩放的范围(几倍)
        self.scale_pre_val = None
        self.cur_canvas_frame = None
        self.drawer = None
        self.create_widgets()
        self.render_preview()
        self.render_label_tip()

    def render_label_tip(self):
        s1 = "{}{}".format(self.lalel_position_const, self.dst_xywh)
        self.label_position_var.set(s1.ljust(30))

        s2 = "{}{}".format(self.label_zoom_const, str(self.scale.get()))
        self.label_zoom_var.set(s2.ljust(20))

    def render_preview(self):
        global g_preview_img
        if self.parent.player_obj and hasattr(self.parent.player_obj, "host_video"):

            flag = False
            config_info = copy.deepcopy(self.dst_config)
            if "type" in config_info and config_info["type"] == self.short_name:
                # 恢复到没有缩放之前
                config_info["xywh"] = [int(val / self.zoom_factor) for val in self.dst_xywh]
                flag = True
            if not flag:
                return
            glog.info(f"手工更新 {self.short_name} 配置信息为 {self.dst_xywh}")

            # 类初始化内部会进行缩放
            if self.drawer is None:
                self.drawer = DrawerHuman(config_info)
            if self.drawer._human_frame is None:
                next_video = self.parent.player_obj.host_video.get_nextvideo()
                if not next_video:
                    glog.error("manual config drawer human, not find next video")
                    return
                _, human_path, mask_path, *_ = next_video

                self.drawer.set_asset_path(human_path, mask_path, 0)
                self.drawer.worker_process()
            
            self.drawer.set_xywh(config_info)
            canvas = np.zeros((self.max_height, self.max_width, 3), dtype=np.uint8)
            self.drawer.draw_to_canvas(canvas)

            w, h, _ = canvas.shape
            ww, hh = self.canva_width / self.max_width * w, self.canva_height / self.max_height * h
            image = Image.fromarray(canvas[:, :, ::-1])
            g_preview_img = ImageTk.PhotoImage(image.resize(size=(int(hh), int(ww))))
            self.image_label.config({'image': g_preview_img})

    def position_config(self, text):
        self.render_label_tip()
        if self.dst_xywh:
            x, y, w, h = self.dst_xywh
            if text == "↑":
                y -= self.step
            elif text == "↓":
                y += self.step
            elif text == "←":
                x -= self.step
            elif text == "→":
                x += self.step
            elif text == "大":
                if (self.scale.get() + self.scale_step) > self.scale_max:
                    return
                val = float(float(self.scale.get()) + float(self.scale_step))
                self.scale.set(val)
                self.scale_pre_val = val
                h = int((1 + self.scale_step) * h)
                w = int((1 + self.scale_step) * w)
            elif text == "小":
                if (self.scale.get() - self.scale_step) < self.scale_min:
                    return
                val = float(float(self.scale.get()) - float(self.scale_step))
                self.scale.set(val)
                self.scale_pre_val = val
                h = int((1 - self.scale_step) * h)
                w = int((1 - self.scale_step) * w)
            self.dst_xywh = [x, y, w, h]
            self.render_preview()
        self.render_label_tip()

    def scale_change(self, value):
        x, y, w, h = self.dst_xywh
        value = float(value)
        if abs(float(value) - float(self.scale_pre_val)) < 0.0001:
            return
        h = int(h / self.scale_pre_val * value)
        w = int(w / self.scale_pre_val * value)
        self.dst_xywh = [x, y, w, h]
        self.render_preview()
        self.render_label_tip()
        self.scale_pre_val = value

    def submit_configure(self):
        rtn = self.parent.do_config_update(
            self.dst_config, self.dst_xywh, self.zoom_factor,
            self.short_name, self.config_time, self.first_time, self.time_limit
        )
        if rtn:
            self.config_time = time.time()
        self.render_preview()
        self.first_time = False

    def create_widgets(self):
        btn_up = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="↑")
        btn_up.grid(row=0, column=1)

        btn_down = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="↓")
        btn_down.grid(row=2, column=1)

        btn_left = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="←")
        btn_left.grid(row=1, column=0)

        btn_right = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="→")
        btn_right.grid(row=1, column=2)

        self.label_position = tk.Label(self.parent.frame_right, textvariable=self.label_position_var, width=30, pady=15)
        self.label_position.grid(row=3, column=0, columnspan=3)

        empty_label = tk.Label(self.parent.frame_right)
        empty_label.grid(row=4, column=0, columnspan=3)

        btn_zoom_small = LongPressButton(self.parent.frame_right, parent=self, text="小")
        btn_zoom_small.grid(row=5, column=0)
        self.scale = tk.Scale(self.parent.frame_right, from_=self.scale_min, to=self.scale_max,
                              orient=tk.HORIZONTAL, borderwidth=0, troughcolor='#7269FF',
                              width=3, sliderlength=8, showvalue=False, command=self.scale_change,
                              resolution=self.scale_step, variable=tk.IntVar())
        # 相对于短边与1080 进行比较
        val = round(float(min(self.dst_xywh[2], self.dst_xywh[3])) / self.zoom_factor / 1080, 2)
        val = min(val, self.scale_max)
        self.scale.set(val)
        self.scale_pre_val = val
        self.scale.grid(row=5, column=0, columnspan=3)
        btn_zoom_big = LongPressButton(self.parent.frame_right, parent=self, text="大")
        btn_zoom_big.grid(row=5, column=2)

        self.label_zoom = tk.Label(self.parent.frame_right,  textvariable=self.label_zoom_var, width=16)
        self.label_zoom.grid(row=6, column=0, columnspan=3)

        # btn_preview = tk.Button(self.parent.frame_right, text="预览", command=self.render_preview)
        # btn_preview.grid(row=4, column=2, pady=50)

        btn_submit = tk.Button(self.parent.frame_right, text="提交配置", command=self.submit_configure)
        btn_submit.grid(row=7, column=1, pady=25)


class DrawerVideoConfigure(ConfigureFunctions):
    name = 'DrawerVideo Configure'
    short_name = 'DrawerVideo'

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.step = 10
        self.height_limit = 59  # 高度不能小于这个限制
        self.video_height = 300
        self.video_width = 540

        self.init_width_height_zoom(self.parent.config_data)
        self.src_config = self.init_drawer_config_info(self.parent.config_data, self.short_name, src=True)
        self.dst_config = self.init_drawer_config_info(self.parent.config_data, self.short_name)
        self.dst_xywh = self.dst_config['xywh'] if self.dst_config and 'xywh' in self.dst_config else {}

        self.image_label = tk.Label(self.parent.frame_preview)
        self.image_label.config({'image': None})
        self.image_label.place(x=0, y=0)

        self.lalel_const = "调整置顶栏位置："
        self.label1 = None
        self.label_var = tk.StringVar(value="")

        self.label_zoom_const = "调整大小："
        self.label_zoom = None
        self.label_zoom_var = tk.StringVar(value="")

        self.scale = None
        self.scale_min, self.scale_max = 0.2, 1
        self.scale_step = 0.01
        self.scale_pre_val = None

        self.cur_frame = None
        self.drawer = None  # DrawerVideo(config=self.src_config)
        self.create_widget()
        self.render_preview()
        self.render_label_tip()

    def render_label_tip(self):
        s1 = "{}{}".format(self.lalel_const, self.dst_xywh)
        self.label_var.set(s1.ljust(30))

        s2 = "{}{}".format(self.label_zoom_const, str(self.scale.get()))
        self.label_zoom_var.set(s2.ljust(15))

    def render_preview(self):
        global g_preview_img
        if self.parent.player_obj and hasattr(self.parent.player_obj, "host_video"):

            flag = False
            config_info = copy.deepcopy(self.dst_config)
            if "type" in config_info and config_info["type"] == self.short_name:
                # 恢复到没有缩放之前
                config_info["xywh"] = [int(val / self.zoom_factor) for val in self.dst_xywh]
                flag = True
            if not flag:
                return
            glog.info(f"手工更新 {self.short_name} 配置信息为 {self.dst_xywh}")

            product_id = self.parent.player_obj.host_video.get_cur_product()
            if not product_id:
                glog.error("manual config drawer video, not find cur product")
                return
            product_path = ""
            if hasattr(self.parent.player_obj, '_product_background'):
                product_dict =  self.parent.player_obj._product_background
                if product_id in product_dict and product_dict[product_id]:
                    product_path = product_dict[product_id][0]
                if not product_path and product_dict:
                    for k, val in product_dict.items():
                        if val:
                            product_path = val[0]
                            break
            if product_path:
                if self.drawer is None:
                    self.drawer = DrawerVideo(config_info)
                
                self.drawer.set_xywh(config_info)
                self.drawer.set_video_path(product_path)
                self.drawer.worker_process()

                self.cur_frame = self.drawer.get_frame()
                if self.cur_frame is not None:
                    h, w, _ = self.cur_frame.shape
                    ww, hh = self.canva_width / self.max_width * w, self.canva_height / self.max_height * h
                    temp_frame = Image.fromarray(self.cur_frame[:, :, ::-1])
                    g_preview_img = ImageTk.PhotoImage(temp_frame.resize((int(ww), int(hh))))
                    self.image_label.config({'image': g_preview_img})
                    x = int(self.canva_width / self.max_width * self.dst_xywh[0])
                    y = int(self.canva_height / self.max_height * self.dst_xywh[1])
                    self.image_label.place(x=x, y=y)
            else:
                glog.info("manual config drawer video, not find valid product_path")
        else:
            glog.info("manual config drawer video, no host_video function existed")

    def position_config(self, text):
        self.render_label_tip()
        if self.dst_xywh:
            x, y, w, h = self.dst_xywh
            if text == "↑":
                if y - self.step <= 0:
                    y = 0
                else:
                    y -= self.step
            elif text == "↓":
                if y + self.step >= self.max_height:
                    y = self.max_height
                else:
                    y += self.step
            elif text == "←":
                if x - self.step <= 0:
                    x = 0
                else:
                    x -= self.step
            elif text == "→":
                if x + self.step >= self.max_width:
                    x = self.max_width
                else:
                    x += self.step
            elif text == "大":
                if (self.scale.get() + self.scale_step) > self.scale_max:
                    return
                val = float(float(self.scale.get()) + float(self.scale_step))
                w, h = self.get_big_width_and_height(val)
                if not (w or h):
                    return

                self.scale.set(val)
                self.scale_pre_val = val
            elif text == "小":
                if (self.scale.get() - self.scale_step) < self.scale_min:
                    return
                val = float(float(self.scale.get()) - float(self.scale_step))
                w, h = self.get_small_width_and_height(val)
                if not(w or h):
                    return

                self.scale.set(val)
                self.scale_pre_val = val
            if (self.max_width < x + w) or (self.max_height < y + h):
                glog.info("调整超过了限制，不满足 width:{} < {} + {} or height:{} < {} + {}".format(
                    self.max_width, x, w, self.max_height, y, h
                ))
            else:
                self.dst_xywh = [x, y, w, h]
                self.render_preview()
        self.render_label_tip()

    def get_big_width_and_height(self, val):
        x, y, w, h = self.dst_xywh
        h = int(float(val) * float(self.video_height))
        w = int(h / self.video_height * self.video_width)
        if x + w > self.max_width:
            return False, False
        if x == 0 and (w / self.max_width) > 0.95:
            w = self.video_width
            h = self.video_height
        if x == 0 and (h / self.video_height) > 0.95:
            w = self.video_width
            h = self.video_height
        return w, h

    def get_small_width_and_height(self, val):
        x, y, w, h = self.dst_xywh
        h = int(float(val) * float(self.video_height))
        if h <= self.height_limit:
            return False, False
        w = int(h / self.video_height * self.video_width)
        if x + w > self.max_width:
            return False, False
        return w, h

    def scale_change(self, value):
        x, y, w, h = self.dst_xywh
        value = float(value)
        flag = False
        if value > self.scale_pre_val:  # 增大
            w, h = self.get_big_width_and_height(value)
            if not (w or h):
                self.scale.set(self.scale_pre_val)
                return
            flag = True

        elif value < self.scale_pre_val:  # 缩小
            w, h = self.get_small_width_and_height(value)
            if not (w or h):
                self.scale.set(self.scale_pre_val)
                return
            flag = True

        if flag:
            if (self.max_width < x + w) or (self.max_height < y + h):
                glog.info("调整超过了限制，不满足 width:{} < {} + {} or height:{} < {} + {}".format(
                    self.max_width, x, w, self.max_height, y, h
                ))
                self.scale.set(self.scale_pre_val)
            else:
                self.dst_xywh = [x, y, w, h]
                self.scale_pre_val = value
                self.render_preview()
            self.render_label_tip()

    def submit_configure(self):
        rtn = self.parent.do_config_update(
            self.dst_config, self.dst_xywh, self.zoom_factor,
            self.short_name, self.config_time, self.first_time, self.time_limit
        )
        if rtn:
            self.config_time = time.time()
        self.render_preview()
        self.first_time = False

    def create_widget(self):
        btn_up = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="↑")
        btn_up.grid(row=0, column=1)

        btn_down = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="↓",)
        btn_down.grid(row=2, column=1)

        btn_left = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="←")
        btn_left.grid(row=1, column=0)

        btn_right = LongPressButton(self.parent.frame_right, parent=self, borderwidth=0, text="→")
        btn_right.grid(row=1, column=2)

        self.label1 = tk.Label(self.parent.frame_right, textvariable=self.label_var, width=30, pady=15)
        self.label1.grid(row=3, column=0, columnspan=3)

        empty_label = tk.Label(self.parent.frame_right)
        empty_label.grid(row=4, column=0, columnspan=3)

        btn_zoom_small = LongPressButton(self.parent.frame_right, parent=self, text="小")
        btn_zoom_small.grid(row=5, column=0)
        self.scale = tk.Scale(self.parent.frame_right, from_=self.scale_min, to=self.scale_max,
                              orient=tk.HORIZONTAL, borderwidth=0, troughcolor='#7269FF',
                              width=3, sliderlength=8, showvalue=False, command=self.scale_change,
                              resolution=self.scale_step, variable=tk.IntVar())
        val = round(float(self.dst_xywh[2]) / self.zoom_factor / 1080, 2)
        self.scale.set(val)
        self.scale_pre_val = val
        self.scale.grid(row=5, column=0, columnspan=3)
        btn_zoom_big = LongPressButton(self.parent.frame_right, parent=self, text="大")
        btn_zoom_big.grid(row=5, column=2)

        self.label_zoom = tk.Label(self.parent.frame_right, textvariable=self.label_zoom_var, width=16)
        self.label_zoom.grid(row=6, column=0, columnspan=3)

        btn = tk.Button(self.parent.frame_right, text="提交配置", command=self.submit_configure)
        btn.grid(row=7, column=1, pady=25)


class ManualConfigure(tk.Frame):
    def __init__(self, parent, player_obj, config_data):
        tk.Frame.__init__(self)
        self.parent = parent            # 父窗口
        self.player_obj = player_obj    # PLAYER 实例对象 或 None
        self.config_data = config_data  # 当前 running_config 内容

        self.listbox = None
        self.cur_selected_name = ""
        self.canvas_width, self.canvas_height = PREVIEW_IMAGE_INFO
        self.scale = None
        self.frame_left = None     # 左侧列表栏
        self.frame_right = None    # 右侧调整区
        self.frame_preview = None  # 预览区

        # 配置将对哪些 Drawer 进行手工配置（前提是已完成应的实现）, 新增中文展示
        self.can_config_drawer_dict = {
            'DrawerDialogVideo': '评论位置', 'DrawerHuman': '人物位置', 'DrawerVideo': '置顶栏位置',
        }
        self.can_config_drawer_dict_reversal = {
            '评论位置': 'DrawerDialogVideo', '人物位置': 'DrawerHuman', '置顶栏位置': 'DrawerVideo',
        }
        # self.create_window()
        self.create_widgets()

    def create_window(self):
        x, y = self.parent.winfo_x(), self.parent.winfo_y()
        w, h = self.parent.winfo_width(), self.parent.winfo_height()
        self.geometry(f"+{x}+{y + h * 4 // 5}")
        self.attributes("-topmost", 0)

    def create_widgets(self):
        self.frame_left = tk.Frame(self.parent, width=130, height=self.canvas_height)
        self.frame_left.grid(row=0, column=0, columnspan=2, pady=2)
        self.frame_left.pack_propagate(False)
        # scrollbar = tk.Scrollbar(self.frame_left)  # 获取和比较大小，是否显示滑动条
        # scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # self.listbox = tk.Listbox(self.frame_left, yscrollcommand=scrollbar.set, height=12)
        self.listbox = tk.Listbox(self.frame_left, height=12)
        # scrollbar.config(command=self.listbox.yview)

        drawer_names = [item["type"] for item in self.config_data["drawers"]
                        if "drawers" in self.config_data and item["type"] in self.can_config_drawer_dict.keys()]
        for name in drawer_names:
            display_name = self.can_config_drawer_dict[name]
            self.listbox.insert(tk.END, display_name)
        # self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH)

        # scrollbar.config(width=20)
        self.listbox.bind('<<ListboxSelect>>', self.listbox_changed)

        self.frame_right = tk.Frame(self.parent, width=200, height=self.canvas_height)
        self.frame_right.grid(row=0, column=2, columnspan=2, pady=2)
        self.frame_right.pack_propagate(False)

        self.frame_preview = tk.Frame(self.parent, width=162, height=self.canvas_height, relief="solid", bd=1)
        self.frame_preview.grid(row=0, column=4, columnspan=2, padx=15, pady=2)
        self.frame_preview.pack_propagate(False)

        if drawer_names:
            self.do_listbox_changed(self.listbox.get(0))
            self.listbox.select_set(0)

    def clear_frame_widget(self):
        if self.frame_right:
            for widget in self.frame_right.winfo_children():
                widget.destroy()
        if self.frame_left:
            for widget in self.frame_preview.winfo_children():
                widget.destroy()

    def listbox_changed(self, event):
        cur_index = event.widget.curselection()
        cur_name = self.listbox.get(cur_index)
        if self.cur_selected_name == cur_name:
            return
        self.cur_selected_name = cur_name
        self.do_listbox_changed(cur_name)

    def do_listbox_changed(self, cur_name):
        name_reversale = self.can_config_drawer_dict_reversal.get(cur_name) or ""
        if name_reversale in self.can_config_drawer_dict.keys():
            class_name = f'{name_reversale}Configure'
            if class_name in globals():  # dir():  # globals()  locals()
                cls_obj = eval(class_name)
                if cls_obj:
                    self.clear_frame_widget()
                    cls_obj(self)

    def do_config_update(self, dst_config, dst_xywh, zoom_factor, short_name, config_time, first_time, time_limit):
        if str(dst_config["xywh"]) == str(dst_xywh):
            glog.info(f"{short_name} 配置信息 xywh 未改变，不做处理")
            return False

        time_interval = int(time.time() - config_time)
        if not first_time and time_interval < time_limit:
            msg_str = f"手工更新需间隔{time_limit}秒，更改太频繁，请{int(time_limit - time_interval)}秒后重试"
            glog.info(msg_str)
            messagebox.showinfo(message=msg_str)
            return False

        flag = False
        new_config = deepcopy(self.config_data)
        for item in new_config["drawers"]:
            if item["type"] == "DrawerDialogVideo" and short_name == "DrawerDialogVideo":
                x, y, w, h = dst_xywh
                xx = int(x / zoom_factor)
                yy = int(y / zoom_factor)
                ww = int(item["xywh"][2])
                hh = int(item["xywh"][3])
                item["xywh"] = [xx, yy, ww, hh]
                flag = True
                break
            elif item["type"] == "DrawerHuman" and short_name == "DrawerHuman":
                item["xywh"] = [int(val / zoom_factor) for val in dst_xywh]
                flag = True
                break
            elif item["type"] == "DrawerVideo" and short_name == "DrawerVideo":
                item["xywh"] = [int(val / zoom_factor) for val in dst_xywh]
                flag = True
                break
        if not flag:
            return False

        glog.info(f"手工更新 {short_name} 配置信息，更新后的内容: {dst_xywh}")

        if self.upload_to_cos(new_config):
            self.config_data = new_config
            if self.player_obj is None:
                messagebox.showinfo(message='更新完成，开始播放器即生效！')
                return True
            else:
                if hasattr(self.player_obj, "_update_config_drawer"):
                    self.player_obj._update_config_drawer()
                    messagebox.showinfo(message='更新完成，请在播放器查看效果！')
                    return True
        else:
            messagebox.showinfo(message='更新失败，请检查网络！')
        return False

    def upload_to_cos(self, new_config):
        uid = self.config_data["uid"]  # uid
        env = os.environ.get('RUNNING_ENV', 'stable')
        net = os.environ.get('USE_INTRANET', 'intranet')
        customer_id = os.environ.get('CUSTOMER_ID')
        customer_name = os.environ.get('CUSTOMER_NAME')
        cur_version = os.environ.get("CUR_VERSION")
        platform = os.environ.get("PLATFORM", "")
        event = "手动更新配置"
        client_log_url = gateway_url[env][net] + clientLog_api

        prefix_path = f"tb_live/{env}/live_data/customer/" if os.environ.get(
            'IS_PBS') == "True" else f'cs/{env}/customer/'
        file_key = f'{uid}/online_config.json'
        manual_config_path = os.path.join(self.config_data["jumpy_sdk_path"], 'assets/manual_drawer_config.json')
        auth_url = gateway_url[env][net] + public_api + '/api/v1/cos/sts'
        try:
            res = request_get_with_auth(auth_url)
            content = json.loads(res.content)
            temp_secret_id = content['data']['credentials']['tmpSecretId']
            temp_secret_key = content['data']['credentials']['tmpSecretKey']
            session_token = content['data']['credentials']['sessionToken']
        except Exception as e:
            if os.environ.get('IS_PBS') != "True":
                async_client_log(customer_id=customer_id,
                                 customer_name=customer_name,
                                 cur_version=cur_version,
                                 event=event,
                                 content="fail",
                                 platform=platform,
                                 client_log_url=client_log_url)
                glog.info(f"event:{event}")
            glog.error(traceback.format_exc())
            return False
        with open(manual_config_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(new_config, ensure_ascii=False, indent=4,
                               separators=(',', ':')))
        TCOSHelper(temp_secret_id, temp_secret_key, token=session_token).upload(
            manual_config_path, file_key, prefix=prefix_path)
        os.remove(manual_config_path)
        return True


if __name__ == "__main__":
    root = tk.Tk()
    root.title("手动更改配置文件")
    data_d = {'width': 500, 'height': 200}
    root.geometry("{}x{}".format(data_d['width'], data_d['height']))
    ManualConfigure(root, data_d)
    root.mainloop()
