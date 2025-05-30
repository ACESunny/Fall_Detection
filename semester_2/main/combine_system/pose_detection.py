import cv2
import zmq
import base64
import json
import numpy as np
import mediapipe as mp
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread, Event
from PIL import Image, ImageTk


class PoseDetectionApp:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.show_video = True
        self.stop_event = Event()

        
        self.setup_ui()
        self.setup_zmq()
        self.setup_mediapipe()
        
    def setup_ui(self):
        self.root.title("Pose Detection Controller")
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
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_detection)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_detection, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.video_toggle = ttk.Checkbutton(btn_frame, text="Show Video", command=self.toggle_video, variable=tk.BooleanVar(value=True))
        self.video_toggle.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Exit", command=self.on_close).pack(side=tk.RIGHT, padx=5)
        
    def setup_zmq(self):
        self.context = zmq.Context()
        self.receiver_socket = self.context.socket(zmq.SUB)
        self.receiver_socket.connect("tcp://localhost:5555")
        self.receiver_socket.setsockopt_string(zmq.SUBSCRIBE, 'Sender_frame')

        self.sender_socket = self.context.socket(zmq.PUB)
        self.sender_socket.bind("tcp://*:5556")
        
    def setup_mediapipe(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False, 
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
    def start_detection(self):
        if not self.running:
            self.running = True
            self.stop_event.clear()
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("Running - Processing frames...")
            
            Thread(target=self.process_frames, daemon=True).start()
            
    def stop_detection(self):
        if self.running:
            self.running = False
            self.stop_event.set()
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_var.set("Stopped")
            
    def toggle_video(self):
        self.show_video = not self.show_video
        if not self.show_video:
            self.video_label.config(image='')
            
    def process_frames(self):
        while not self.stop_event.is_set():
            try:
                # Receive frame from ZeroMQ
                topic = self.receiver_socket.recv_string()
                data_json = self.receiver_socket.recv_string()
                data = json.loads(data_json)

                # Extract timestamp and frame
                image_timestamp = data["timestamp"]
                jpg_as_text = data["frame"]
                
                # Convert frame from base64 back to image
                jpg_original = base64.b64decode(jpg_as_text)
                frame = cv2.imdecode(np.frombuffer(jpg_original, dtype=np.uint8), cv2.IMREAD_COLOR)

                # Convert frame to RGB (Mediapipe requires RGB format)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Process frame with Mediapipe Pose
                results = self.pose.process(rgb_frame)

                # Draw skeleton on frame (if landmarks exist)
                if results.pose_landmarks:
                    self.mp_drawing.draw_landmarks(
                        frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

                    # Get coordinates of all 33 landmarks
                    landmarks = results.pose_landmarks.landmark
                    height, width, _ = frame.shape

                    # Create list to store (x, y) coordinates
                    pose_data = []
                    for landmark in landmarks:
                        pose_data.extend([landmark.x, landmark.y])

                    # Calculate frame dimensions
                    max_width = width
                    max_height = height

                    # Add Pose_Timestamp
                    pose_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

                    # Create data to send
                    pose_info = {
                        "Image_Timestamp": image_timestamp,
                        "Pose_Timestamp": pose_timestamp,
                        "MAX_Height": max_height,
                        "MAX_Width": max_width,
                        "Landmarks": pose_data
                    }

                    # Convert data to JSON
                    pose_info_json = json.dumps(pose_info)

                    # Send data to PoseData topic
                    self.sender_socket.send_string("PoseData", zmq.SNDMORE)
                    self.sender_socket.send_string(pose_info_json)

                # Display frame if video is enabled
                if self.show_video:
                    self.display_frame(frame)
                    
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                self.stop_detection()
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                break
                
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
        self.stop_detection()
        self.root.after(100, self.cleanup)
        self.root.destroy()
        
    def cleanup(self):
        self.pose.close()
        self.receiver_socket.close()
        self.sender_socket.close()
        self.context.term()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    root = tk.Tk()
    app = PoseDetectionApp(root)
    
    # Handle window close event
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    root.mainloop()