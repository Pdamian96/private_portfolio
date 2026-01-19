import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
import math
# Imports needed if you implement the Save Image feature later:
# from PIL import ImageDraw, ImageFont 

class ImageMeasureTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Measurement Tool Pro")
        
        # State Variables
        self.measure_id = 0
        self.pixel_to_meter = 1.0 
        self.points = []
        self.is_calibrating = False
        self.measurements = [] 
        self.hovered_tag = None
        self.scale = 1.0
        self.min_scale = 0.1
        self.max_scale = 10.0
        self.original_image = None
        self.image_id = None
        self.measurements_visible = True
        
        # UI Colors
        self.normal_color = "#FF3333"
        self.line_hover_color = "orange"
        # Changing hover color to a bright yellow/gold for better contrast against black bg
        self.text_hover_color = "#FFFF00" 
        self.preview_color = "#AAAAAA"

        # UI Layout
        self.canvas = tk.Canvas(root, cursor="cross", bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Status Bar
        self.status_frame = tk.Frame(root, bd=1, relief=tk.SUNKEN, bg="#2e2e2e")
        self.status_frame.pack(fill=tk.X)
        self.coords_label = tk.Label(self.status_frame, text="X: 0, Y: 0", width=20, anchor="w", bg="#2e2e2e", fg="#aaaaaa")
        self.coords_label.pack(side=tk.LEFT, padx=5)
        self.info_label = tk.Label(self.status_frame, text="Ready", anchor="w", bg="#2e2e2e", fg="#aaaaaa")
        self.info_label.pack(side=tk.LEFT, fill=tk.X)

        self.preview_line = None
        self.preview_text = None

        self.setup_menu()

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Escape>", lambda e: self.cancel_action())
        self.root.bind("h", lambda e: self.toggle_visibility())
        self.root.bind("H", lambda e: self.toggle_visibility())

    def setup_menu(self):
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Open Image", command=self.open_image)
        file_menu.add_command(label="Calibrate Scale", command=self.start_calibration)
        file_menu.add_separator()
        file_menu.add_command(label="Toggle Measurements (H)", command=self.toggle_visibility)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu.add_cascade(label="File", menu=file_menu)

    def toggle_visibility(self):
        self.measurements_visible = not self.measurements_visible
        state = tk.NORMAL if self.measurements_visible else tk.HIDDEN
        self.canvas.itemconfigure("measurement", state=state)
        status = "Visible" if self.measurements_visible else "Hidden"
        self.info_label.config(text=f"Measurements {status}")

    def get_snapped_point(self, start_x, start_y, current_x, current_y):
        dx, dy = current_x - start_x, current_y - start_y
        dist = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        snap_angle = round(angle / (math.pi / 4)) * (math.pi / 4)
        return start_x + dist * math.cos(snap_angle), start_y + dist * math.sin(snap_angle)

    def on_click(self, event):
        if not self.original_image: return
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        if len(self.points) == 1 and (event.state & 0x0001):
            cx, cy = self.get_snapped_point(self.points[0][0], self.points[0][1], cx, cy)

        self.points.append((cx, cy))

        if len(self.points) == 2:
            if self.is_calibrating:
                self.finish_calibration()
            else:
                self.measure()
            self.points.clear()
            self.clear_preview()

    def measure(self):
        (x1, y1), (x2, y2) = self.points
        pixel_dist = math.hypot(x2 - x1, y2 - y1) / self.scale
        meter_dist = pixel_dist / self.pixel_to_meter

        tag = f"measure_{self.measure_id}"
        self.measure_id += 1
        self.measurements.append(tag)

        shared_tags = (tag, "measurement")
        self.canvas.create_oval(x1-3, y1-3, x1+3, y1+3, fill=self.normal_color, outline="", tags=shared_tags + ("point",))
        self.canvas.create_oval(x2-3, y2-3, x2+3, y2+3, fill=self.normal_color, outline="", tags=shared_tags + ("point",))
        self.canvas.create_line(x1, y1, x2, y2, fill=self.normal_color, width=2, tags=shared_tags + ("line",))
        
        label = f"{meter_dist:.3f}m"
        # Added a slight offset to y position so it doesn't sit exactly on the line
        self.canvas.create_text((x1+x2)/2, (y1+y2)/2 - 15, text=label, fill=self.normal_color, 
                                font=("Arial", int(10*self.scale), "bold"), tags=shared_tags + ("text",))
        
        if not self.measurements_visible:
            self.canvas.itemconfigure(tag, state=tk.HIDDEN)

    def on_mouse_move(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        if self.original_image:
            img_x = int(cx / self.scale)
            img_y = int(cy / self.scale)
            self.coords_label.config(text=f"X: {img_x}, Y: {img_y}")

        if len(self.points) == 1:
            curr_x, curr_y = cx, cy
            if event.state & 0x0001: 
                curr_x, curr_y = self.get_snapped_point(self.points[0][0], self.points[0][1], cx, cy)
            self.update_preview(self.points[0][0], self.points[0][1], curr_x, curr_y)
        else:
            items = self.canvas.find_overlapping(cx-2, cy-2, cx+2, cy+2)
            measure_tag = next((t for item in items for t in self.canvas.gettags(item) if t.startswith("measure_")), None)
            if measure_tag != self.hovered_tag:
                self.clear_hover()
                if measure_tag and self.measurements_visible: self.apply_hover(measure_tag)

    def update_preview(self, x1, y1, x2, y2):
        self.clear_preview()
        self.preview_line = self.canvas.create_line(x1, y1, x2, y2, fill=self.preview_color, dash=(4, 4))
        dist = (math.hypot(x2 - x1, y2 - y1) / self.scale) / self.pixel_to_meter
        self.preview_text = self.canvas.create_text((x1+x2)/2, (y1+y2)/2 - 15, 
                                                   text=f"{dist:.3f}m", fill=self.preview_color, font=("Arial", int(10*self.scale)))

    def clear_preview(self):
        if self.preview_line: self.canvas.delete(self.preview_line)
        if self.preview_text: self.canvas.delete(self.preview_text)

    # --- UPDATED HOVER LOGIC ---
    def apply_hover(self, tag):
        self.hovered_tag = tag
        self.canvas.tag_raise(tag)

        # 1. Find the text item associated with this tag
        text_item = self.canvas.find_withtag(f"{tag}&&text")
        if text_item:
            # 2. Get the bounding box coords of the text
            x1, y1, x2, y2 = self.canvas.bbox(text_item)
            padding = 4
            # 3. Create a black rectangle behind it.
            # stipple="gray50" creates a semi-transparent effect in Tkinter.
            bg_rect = self.canvas.create_rectangle(x1-padding, y1-padding, x2+padding, y2+padding,
                                                    fill="black", outline="black", stipple="gray50", 
                                                    tags=("hover_bg",))
            # 4. Ensure the text is drawn ON TOP of the new background rectangle
            self.canvas.tag_raise(f"{tag}&&text", bg_rect)

        self.canvas.itemconfig(f"{tag}&&line", fill=self.line_hover_color, width=3)
        self.canvas.itemconfig(f"{tag}&&text", fill=self.text_hover_color)

    def clear_hover(self):
        if self.hovered_tag:
            # 1. Delete the temporary background rectangle
            self.canvas.delete("hover_bg")

            tag = self.hovered_tag
            self.canvas.itemconfig(f"{tag}&&line", fill=self.normal_color, width=2)
            self.canvas.itemconfig(f"{tag}&&text", fill=self.normal_color)
            self.hovered_tag = None
    # ---------------------------

    def start_calibration(self):
        self.is_calibrating = True
        self.info_label.config(text="Mode: CALIBRATION (Draw known distance)", fg=self.text_hover_color)
        self.points.clear()

    def finish_calibration(self):
        (x1, y1), (x2, y2) = self.points
        pixel_dist = math.hypot(x2 - x1, y2 - y1) / self.scale
        real_dist = simpledialog.askfloat("Calibration", "Real distance (meters):", minvalue=0.0001)
        if real_dist:
            self.pixel_to_meter = pixel_dist / real_dist
            self.info_label.config(text=f"Scale: {self.pixel_to_meter:.2f} px/m", fg="#aaaaaa")
        self.is_calibrating = False

    def open_image(self):
        path = filedialog.askopenfilename()
        if not path: return
        self.original_image = Image.open(path)
        self.scale = 1.0
        self.canvas.delete("all")
        self.tk_image = ImageTk.PhotoImage(self.original_image)
        self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image, tags=("image",))
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.info_label.config(text=f"Opened: {path.split('/')[-1]}")

    def on_zoom(self, event):
        if not self.original_image: return
        factor = 1.1 if (event.delta > 0 or event.num == 4) else 0.9
        if not (self.min_scale <= self.scale * factor <= self.max_scale): return
        self.scale *= factor
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.scale("all", cx, cy, factor, factor)
        resized = self.original_image.resize((int(self.original_image.width * self.scale), 
                                              int(self.original_image.height * self.scale)), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.image_id, image=self.tk_image)
        
        # Update font sizes for existing text
        new_font_size = max(8, int(10 * self.scale))
        for item in self.canvas.find_withtag("text"):
             self.canvas.itemconfig(item, font=("Arial", new_font_size, "bold"))
             
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        # If we are hovering while zooming, we need to redraw the bg rect for new size
        if self.hovered_tag:
             self.clear_hover()
             self.apply_hover(self.hovered_tag)

    def start_pan(self, event): self.canvas.scan_mark(event.x, event.y)
    def do_pan(self, event): self.canvas.scan_dragto(event.x, event.y, gain=1)
    def cancel_action(self): 
        self.points.clear(); self.clear_preview(); self.is_calibrating = False
        self.info_label.config(text="Ready", fg="#aaaaaa")
    def on_right_click(self, event):
        item = self.canvas.find_closest(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        for tag in self.canvas.gettags(item):
            if tag.startswith("measure_"):
                self.canvas.delete(tag)
                if tag in self.measurements: self.measurements.remove(tag)
                self.clear_hover()
    def undo(self, event=None):
        if self.measurements: 
            self.canvas.delete(self.measurements.pop())
            self.clear_hover()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageMeasureTool(root)
    root.mainloop()