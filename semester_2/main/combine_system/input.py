import cv2
import zmq
import base64
import json
from datetime import datetime
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread, Event
from PIL import Image, ImageTk

class VideoSenderApp:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.show_video = True
        self.show_fps = True
        self.stop_event = Event()
        self.cap = None
        self.frame_delay = 1/30  # Default frame delay for 30 FPS
        
        self.setup_ui()
        self.setup_zmq()
        
    def setup_ui(self):
        self.root.title("Video Sender Controller")
        self.root.geometry("1000x800")
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Video frame
        video_frame = ttk.LabelFrame(main_frame, text="Video Feed", padding="10")
        video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Video label
        self.video_label = ttk.Label(video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.fps_var = tk.StringVar(value="FPS: 0.00")
        status_bar = ttk.Frame(main_frame)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(status_bar, textvariable=self.status_var, relief=tk.SUNKEN, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(status_bar, textvariable=self.fps_var, relief=tk.SUNKEN, width=15).pack(side=tk.RIGHT)
        
        # Source selection
        source_frame = ttk.Frame(control_frame)
        source_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(source_frame, text="Video Source:").pack(side=tk.LEFT, padx=5)
        
        self.source_var = tk.StringVar(value="webcam")
        ttk.Radiobutton(source_frame, text="Webcam", variable=self.source_var, value="webcam").pack(side=tk.LEFT)
        ttk.Radiobutton(source_frame, text="IP Camera", variable=self.source_var, value="ipcam").pack(side=tk.LEFT)
        ttk.Radiobutton(source_frame, text="Video File", variable=self.source_var, value="file").pack(side=tk.LEFT)
        
        self.source_entry = ttk.Entry(source_frame, width=40)
        self.source_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.source_entry.insert(0, "0")  # Default webcam index
        
        ttk.Button(source_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_sending)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_sending, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.video_toggle = ttk.Checkbutton(btn_frame, text="Show Video", command=self.toggle_video, variable=tk.BooleanVar(value=True))
        self.video_toggle.pack(side=tk.LEFT, padx=5)
        
        self.fps_toggle = ttk.Checkbutton(btn_frame, text="Show FPS", command=self.toggle_fps, variable=tk.BooleanVar(value=True))
        self.fps_toggle.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Exit", command=self.on_close).pack(side=tk.RIGHT, padx=5)
        
    def setup_zmq(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://*:5555")

        self.fps_socket = self.context.socket(zmq.PUB)
        self.fps_socket.bind("tcp://*:5551")
        
    def browse_file(self):
        if self.source_var.get() == "file":
            filename = filedialog.askopenfilename(
                title="Select Video File",
                filetypes=[("Video Files", "*.mp4;*.avi;*.mov"), ("All Files", "*.*")]
            )
            if filename:
                self.source_entry.delete(0, tk.END)
                self.source_entry.insert(0, filename)
        
    def open_video_source(self):
        source = self.source_entry.get()
        
        if self.source_var.get() == "webcam":
            try:
                source = int(source)
            except ValueError:
                messagebox.showerror("Error", "Webcam index must be a number")
                return None
        elif self.source_var.get() == "ipcam":
            if not source.startswith(("http://", "https://", "rtsp://")):
                messagebox.showerror("Error", "IP Camera must start with http://, https://, or rtsp://")
                return None
        
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            messagebox.showerror("Error", f"Cannot open video source: {source}")
            return None
            
        # Get original FPS
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        if original_fps <= 0:
            original_fps = 30  # Default FPS if cannot read
            
        self.frame_delay = 1 / original_fps
        return cap
        
    def start_sending(self):
        if not self.running:
            self.cap = self.open_video_source()
            if self.cap is None:
                return
                
            self.running = True
            self.stop_event.clear()
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("Running - Sending frames...")
            
            # Initialize FPS counter
            self.start_time = time.time()
            self.frame_count = 0
            
            Thread(target=self.send_frames, daemon=True).start()
            
    def stop_sending(self):
        if self.running:
            self.running = False
            self.stop_event.set()
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_var.set("Stopped")
            
            if self.cap:
                self.cap.release()
                self.cap = None
                
            # Clear video display
            self.video_label.config(image='')
            
    def toggle_video(self):
        self.show_video = not self.show_video
        if not self.show_video:
            self.video_label.config(image='')
            
    def toggle_fps(self):
        self.show_fps = not self.show_fps
        
    def send_frames(self):
        while not self.stop_event.is_set() and self.cap is not None:
            start_time = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                if self.source_var.get() == "file":
                    # For video files, loop when reaching the end
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break

            # Convert frame to base64 string
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            # Create data to send
            data = {
                "timestamp": timestamp,
                "frame": jpg_as_text
            }

            # Convert to JSON
            data_json = json.dumps(data)

            # Send through ZeroMQ
            self.socket.send_string("Sender_frame", zmq.SNDMORE)
            self.socket.send_string(data_json)

            # Calculate FPS
            self.frame_count += 1
            elapsed_time = time.time() - self.start_time

            if elapsed_time >= 1.0:  # Calculate FPS every second
                fps = self.frame_count / elapsed_time
                self.start_time = time.time()
                self.frame_count = 0

                # Send FPS data
                fps_data = {
                    "timestamp": timestamp,
                    "fps": fps
                }
                fps_json = json.dumps(fps_data)
                self.fps_socket.send_string("FPS", zmq.SNDMORE)
                self.fps_socket.send_string(fps_json)

                # Update FPS display
                self.fps_var.set(f"FPS: {fps:.2f}")

            # Display frame if enabled
            if self.show_video:
                self.display_frame(frame)

            # Delay to maintain frame rate
            elapsed_time = time.time() - start_time
            if elapsed_time < self.frame_delay:
                time.sleep(self.frame_delay - elapsed_time)
                
        if not self.stop_event.is_set():
            self.status_var.set("Error reading frames")
            self.stop_sending()
            
    def display_frame(self, frame):
        # Convert the image from BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        image = Image.fromarray(frame)
        
        # Resize image to fit the window
        width, height = self.video_label.winfo_width(), self.video_label.winfo_height()
        if width > 1 and height > 1:  # Ensure the label has been sized
            image = image.resize((width, height), Image.LANCZOS)
        
        # Convert to ImageTk format
        photo = ImageTk.PhotoImage(image=image)
        
        # Update the label
        self.video_label.config(image=photo)
        self.video_label.image = photo  # Keep a reference
        
    def on_close(self):
        self.stop_sending()
        self.root.after(100, self.cleanup)
        self.root.destroy()
        
    def cleanup(self):
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'fps_socket'):
            self.fps_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoSenderApp(root)
    
    # Handle window close event
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    root.mainloop()