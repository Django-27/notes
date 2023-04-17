import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from tkinter import font
from tkinter.ttk import Notebook

root = tk.Tk()
root.geometry("900x540")
width = 900
height = 540
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = int(screen_width / 2 - width / 2)
y = int(screen_height / 2 - height / 2)
size = '{}x{}+{}+{}'.format(width, height, x, y)

root.geometry(size)
root.resizable(False, False)
root.title("自定义Notebook")

frame_grey = tk.Frame(root, bg="#F5F5F5")
frame_grey.pack(fill=tk.BOTH, expand=True)

frame_left = tk.Frame(frame_grey, bg="#FFFFFF")
frame_left.pack(fill=tk.Y, pady=(3, 0), padx=(0, 1), side=tk.LEFT)

bt1 = tk.Button(frame_left, bg="#2ECF7D", text="直播配置", border=0, command=lambda: call_func(value="直播配置"),
                width=15, height=2, font=font.Font(size=12), fg="white", pady=5)
bt1.pack(side=tk.TOP)

bt2 = tk.Button(frame_left, bg="#FFFFFF", text="问答控制", border=0, command=lambda: call_func(value="问答控制"),
                width=15, height=2, font=font.Font(size=12))
bt2.pack(side=tk.TOP)

bt3 = tk.Button(frame_left, bg="#FFFFFF", text="画面配置", border=0, command=lambda: call_func(value="画面配置"),
                width=15, height=2, font=font.Font(size=12))
bt3.pack(side=tk.TOP)

frame_right = tk.Frame(frame_grey, bg="#FFFFFF")
frame_right.pack(fill=tk.BOTH, expand=True, pady=(3, 0), padx=(0, 0), side=tk.LEFT)

style = ttk.Style()
style.layout('TNotebook.Tab', [])
style.configure({"status": "disable"})
note = ttk.Notebook(frame_right)
note.pack(expand=1, fill='both')

# ----------------------- fr1 ----------------------------------------
fr1 = tk.Frame(note, bg="white", width=200, height=200)
lab1 = tk.Label(fr1, text="直播配置")
lab1.pack()
note.add(fr1)

# ----------------------- fr2 ----------------------------------------
fr2 = tk.Frame(note, bg="white")
lab2 = tk.Label(fr2, text="问答控制")
lab2.pack()
note.add(fr2)

# ----------------------- fr3 ----------------------------------------
fr3 = tk.Frame(note, bg="white")
lab3 = tk.Label(fr3, text="画面配置")
lab3.pack()
note.add(fr3)


def call_func(value):
    if value == "直播配置":
        bt1.configure({"bg": "#2ECF7D", "fg": "white"})
        bt2.configure({"bg": "#FFFFFF", "fg": "black"})
        bt3.configure({"bg": "#FFFFFF", "fg": "black"})
        note.select(0)
    elif value == "问答控制":
        bt1.configure({"bg": "#FFFFFF", "fg": "black"})
        bt2.configure({"bg": "#2ECF7D", "fg": "white"})
        bt3.configure({"bg": "#FFFFFF", "fg": "black"})
        note.select(1)
    elif value == "画面配置":
        bt1.configure({"bg": "#FFFFFF", "fg": "black"})
        bt2.configure({"bg": "#FFFFFF", "fg": "black"})
        bt3.configure({"bg": "#2ECF7D", "fg": "white"})
        note.select(2)


# call_func("直播配置")
root.mainloop()
