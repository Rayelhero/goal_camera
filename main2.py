import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import time
from cv2_enumerate_cameras import enumerate_cameras

class SlitScanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Race Finish Line Capture")
        
        # Camera initialization
        self.cameras = enumerate_cameras()
        if not self.cameras:
            messagebox.showerror("Error", "No cameras detected!")
            root.destroy()
            return
            
        self.selected_cam_index = self.select_camera()
        if self.selected_cam_index is None:
            root.destroy()
            return
            
        # Video capture setup
        self.cap = cv2.VideoCapture(self.cameras[self.selected_cam_index].index)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open selected camera!")
            root.destroy()
            return
        
        # Set the resolution to 1080p
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
        self.slit_x = 960
        self.composite = None
        self.is_recording = False
        self.last_preview_update = 0
        
        # GUI setup
        self.setup_ui()
        self.update_frame()

    def select_camera(self):
        if len(self.cameras) == 1:
            return 0
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Camera")
        dialog.transient(self.root)
        dialog.grab_set()
        
        selected = tk.IntVar(value=0)
        
        ttk.Label(dialog, text="Available Cameras:").pack(padx=10, pady=5)
        for idx, cam in enumerate(self.cameras):
            rb = ttk.Radiobutton(
                dialog, 
                text=f"{cam.name} (Index {cam.index})",
                variable=selected,
                value=idx
            )
            rb.pack(anchor=tk.W, padx=10)
            
        ttk.Button(dialog, text="Confirm", 
                 command=lambda: dialog.destroy()).pack(pady=10)
        
        self.root.wait_window(dialog)
        return selected.get()

    def setup_ui(self):
        # Control buttons
        self.controls = ttk.Frame(self.root)
        self.controls.pack(padx=10, pady=10)
        
        self.start_btn = ttk.Button(
            self.controls, 
            text="Start New Capture", 
            command=self.start_capture
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            self.controls,
            text="Save Capture",
            command=self.stop_capture,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Video display panels
        self.display_frame = ttk.Frame(self.root)
        self.display_frame.pack(padx=10, pady=10)
        
        # Live camera feed (left)
        self.live_panel = tk.Label(self.display_frame)
        self.live_panel.pack(side=tk.LEFT, padx=5)
        
        # Composite preview (right)
        self.composite_panel = tk.Label(self.display_frame)
        self.composite_panel.pack(side=tk.LEFT, padx=5)

        # Slit position controls
        self.slit_controls = ttk.Frame(self.root)
        self.slit_controls.pack(padx=10, pady=10)

        self.left_btn = ttk.Button(
            self.slit_controls,
            text="Left",
            command=self.move_slit_left
        )
        self.left_btn.pack(side=tk.LEFT, padx=5)

        self.right_btn = ttk.Button(
            self.slit_controls,
            text="Right",
            command=self.move_slit_right
        )
        self.right_btn.pack(side=tk.LEFT, padx=5)

        width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"Camera resolution: {int(width)}x{int(height)}")

    def move_slit_left(self):
        self.slit_x = max(0, self.slit_x - 10)  # Ensure slit_x doesn't go below 0

    def move_slit_right(self):
        self.slit_x = min(int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) - 1, self.slit_x + 10)  # Ensure slit_x doesn't exceed frame width

    def start_capture(self):
        self.composite = None
        self.is_recording = True
        self.start_time = time.time()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def stop_capture(self):
        self.is_recording = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if self.composite is not None:
            cv2.imwrite("finish_line_capture.png", self.composite)
            messagebox.showinfo("Saved", "Composite image saved successfully!")

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            current_time = time.time()
            
            # Draw a red border around the slit_x coordinate
            height, width, _ = frame.shape
            cv2.rectangle(frame, (self.slit_x - 5, 0), (self.slit_x + 5, height), (0, 0, 255), 2)
            
            # Update live preview (left panel)
            live_preview = cv2.resize(frame, (320, 240))
            live_preview = cv2.cvtColor(live_preview, cv2.COLOR_BGR2RGB)
            live_img = Image.fromarray(live_preview)
            live_tkimg = ImageTk.PhotoImage(image=live_img)
            self.live_panel.imgtk = live_tkimg
            self.live_panel.config(image=live_tkimg)
            
            # Process frame if recording
            if self.is_recording:
                vertical_slice = frame[:, self.slit_x:self.slit_x+1]
                self.composite = vertical_slice if self.composite is None \
                    else np.hstack((self.composite, vertical_slice))
                
                # Update composite preview every 0.5 seconds (right panel)
                if current_time - self.last_preview_update >= 0.5:
                    comp_preview = cv2.resize(self.composite, (640, 480))
                    comp_preview = cv2.cvtColor(comp_preview, cv2.COLOR_BGR2RGB)
                    comp_img = Image.fromarray(comp_preview)
                    comp_tkimg = ImageTk.PhotoImage(image=comp_img)
                    self.composite_panel.imgtk = comp_tkimg
                    self.composite_panel.config(image=comp_tkimg)
                    self.last_preview_update = current_time

        self.root.after(10, self.update_frame)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = SlitScanApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", str(e))
