import cv2
import json
import time
import os
import numpy as np
import tkinter as tk
from tkinter import ttk, simpledialog
from PIL import Image, ImageTk
import screenshot

TEMPLATES_DIR = "templates2"
os.makedirs(TEMPLATES_DIR, exist_ok=True)


class App:
    def __init__(self, root, image: np.ndarray, window_title):
        self.root = root
        self.root.title("Template Maker - One Window")

        self.orig = image
        self.h, self.w = image.shape[:2]

        # Convert OpenCV -> Tk
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(rgb))

        # ===== Canvas =====
        self.canvas = tk.Canvas(root, width=self.w, height=self.h, cursor="cross")
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        # ROI vars
        self.start = None
        self.rect = None
        self.roi = None

        # Mouse bind
        self.canvas.bind("<ButtonPress-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)

        # ===== Controls =====
        frame = ttk.LabelFrame(root, text="Controls")
        frame.pack(fill="x", padx=10, pady=5)

        tk.Button(frame, text="S - Save", bg="#6fa", width=12, command=self.save).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(frame, text="A - Auto", bg="#a6f", width=12, command=lambda: self.save(auto=True)).grid(row=0, column=1, padx=5)
        tk.Button(frame, text="R - Reset", bg="#fa6", width=12, command=self.reset).grid(row=0, column=2, padx=5)
        tk.Button(frame, text="Q - Quit", bg="#f66", width=12, command=root.quit).grid(row=0, column=3, padx=5)

        # ROI info (copy được)
        self.roi_var = tk.StringVar(value="None")
        ttk.Entry(root, textvariable=self.roi_var, font=("Consolas", 12)).pack(fill="x", padx=10, pady=5)

        # Log box
        self.log_box = tk.Text(root, height=8, font=("Consolas", 11))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=5)

    # ===== Utils =====
    def log(self, msg):
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)

    def clamp(self, x, y):
        x = max(0, min(self.w - 1, x))
        y = max(0, min(self.h - 1, y))
        return x, y

    # ===== Mouse events =====
    def on_down(self, event):
        x, y = self.clamp(event.x, event.y)
        self.start = (x, y)
        if self.rect:
            self.canvas.delete(self.rect)

    def on_drag(self, event):
        if not self.start:
            return

        x, y = self.clamp(event.x, event.y)

        if self.rect:
            self.canvas.delete(self.rect)

        self.rect = self.canvas.create_rectangle(
            self.start[0], self.start[1],
            x, y,
            outline="lime", width=2
        )

    def on_up(self, event):
        x2, y2 = self.clamp(event.x, event.y)
        x1, y1 = self.start

        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        if x2 - x1 < 3 or y2 - y1 < 3:
            return

        self.roi = (x1, y1, x2, y2)
        self.roi_var.set(f"{x1}, {y1}, {x2}, {y2}")
        self.log(f"ROI: {self.roi}")

    # ===== Save =====
    def save(self, auto=False):
        if not self.roi:
            self.log("No ROI.")
            return

        if auto:
            name = time.strftime("tpl_%Y%m%d_%H%M%S")
        else:
            name = simpledialog.askstring("Name", "Template name:")
            if not name:
                return

        x1, y1, x2, y2 = self.roi
        crop = self.orig[y1:y2, x1:x2]

        img_path = os.path.join(TEMPLATES_DIR, name + ".png")
        json_path = os.path.join(TEMPLATES_DIR, name + ".json")

        cv2.imwrite(img_path, crop)
        with open(json_path, "w") as f:
            json.dump({"x1": x1, "y1": y1, "x2": x2, "y2": y2}, f, indent=2)

        self.log(f"Saved {img_path}")
        self.log(f"Saved {json_path}")

    def reset(self):
        if self.rect:
            self.canvas.delete(self.rect)

        self.roi = None
        self.roi_var.set("None")

        self.refresh_image()  # <<< thêm dòng này

    def refresh_image(self):
        # chụp lại màn
        new_img = screenshot.screenshot(3)
        if new_img is None:
            self.log("Screenshot failed.")
            return

        self.orig = new_img
        self.h, self.w = new_img.shape[:2]

        rgb = cv2.cvtColor(new_img, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(rgb))

        # cập nhật canvas size và ảnh
        self.canvas.config(width=self.w, height=self.h)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.log("Image refreshed.")

# ===== MAIN =====
window_title = "LDPlayer-3"
img = screenshot.screenshot(3)

root = tk.Tk()
app = App(root, img, window_title)
root.mainloop()