import zmq
import json
import numpy as np
from datetime import datetime
import time
import csv
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread, Event
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

class FeatureCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.stop_event = Event()
        self.use_real_scale = False
        self.save_csv = False
        self.csv_writer = None
        self.calculator = None
        self.feature_history = []
        self.max_history = 100  # Max data points to keep for plotting
        
        self.setup_ui()
        self.setup_zmq()
        
    def setup_ui(self):
        self.root.title("Feature Calculator")
        self.root.geometry("1200x800")
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Data display frame
        data_frame = ttk.Frame(main_frame)
        data_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text display frame
        text_frame = ttk.LabelFrame(data_frame, text="Feature Data", padding="10")
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Graph frame
        graph_frame = ttk.LabelFrame(data_frame, text="Feature Trends", padding="10")
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Text display
        self.text_display = tk.Text(text_frame, wrap=tk.WORD, height=15)
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.text_display)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_display.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_display.yview)
        
        # Setup matplotlib figures
        self.setup_plots(graph_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Settings frame
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Real scale checkbox
        self.real_scale_var = tk.BooleanVar()
        ttk.Checkbutton(settings_frame, text="Use Real Scale", variable=self.real_scale_var).pack(side=tk.LEFT, padx=5)
        
        # CSV save checkbox
        self.csv_var = tk.BooleanVar()
        ttk.Checkbutton(settings_frame, text="Save to CSV", variable=self.csv_var, command=self.toggle_csv).pack(side=tk.LEFT, padx=5)
        
        self.csv_path_var = tk.StringVar()
        self.csv_entry = ttk.Entry(settings_frame, textvariable=self.csv_path_var, width=40)
        self.csv_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.csv_entry.insert(0, "feature_data.csv")
        
        ttk.Button(settings_frame, text="Browse", command=self.browse_csv).pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_calculation)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_calculation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Clear Data", command=self.clear_data).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Exit", command=self.on_close).pack(side=tk.RIGHT, padx=5)
        
    def setup_plots(self, parent_frame):
        # Create matplotlib figures
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Create subplots
        self.ax1 = self.figure.add_subplot(311)
        self.ax2 = self.figure.add_subplot(312)
        self.ax3 = self.figure.add_subplot(313)
        
        self.figure.tight_layout(pad=3.0)
        
        # Initialize empty plots
        self.line1, = self.ax1.plot([], [], 'b-')
        self.line2, = self.ax2.plot([], [], 'r-')
        self.line3, = self.ax3.plot([], [], 'g-')
        
        # Set titles and labels
        self.ax1.set_title('Frame Rate (fps)')
        self.ax2.set_title('Center of Gravity Angle (degrees)')
        self.ax3.set_title('Movement Rate')
        
        # Set common x-axis as time
        for ax in [self.ax1, self.ax2, self.ax3]:
            ax.set_xlabel('Time')
            ax.grid(True)
            ax.xaxis.set_major_locator(MaxNLocator(5))
        
    def setup_zmq(self):
        self.context = zmq.Context()
        
        # Socket for receiving Pose data
        self.pose_socket = self.context.socket(zmq.SUB)
        self.pose_socket.connect("tcp://localhost:5556")
        self.pose_socket.setsockopt_string(zmq.SUBSCRIBE, "PoseData")
        self.pose_socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
        
        # Socket for sending Feature data
        self.feature_socket = self.context.socket(zmq.PUB)
        self.feature_socket.bind("tcp://*:5559")
        
        # เพิ่ม socket สำหรับส่งกราฟ
        self.graph_socket = self.context.socket(zmq.PUB)
        self.graph_socket.bind("tcp://*:5560")
        
    def browse_csv(self):
        filename = filedialog.asksaveasfilename(
            title="Select CSV File",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            self.csv_path_var.set(filename)
            
    def toggle_csv(self):
        self.save_csv = self.csv_var.get()
        if not self.save_csv and self.csv_writer:
            self.csv_writer.close()
            self.csv_writer = None
            
    def start_calculation(self):
        if not self.running:
            self.use_real_scale = self.real_scale_var.get()
            self.save_csv = self.csv_var.get()
            
            if self.save_csv:
                csv_filename = self.csv_path_var.get()
                if not csv_filename:
                    messagebox.showerror("Error", "Please specify a CSV filename")
                    return
                self.csv_writer = CSVWriter(csv_filename)
            
            self.calculator = FeatureCalculator(use_real_scale=self.use_real_scale)
            self.running = True
            self.stop_event.clear()
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("Running - Calculating features...")
            
            Thread(target=self.process_data, daemon=True).start()
            
    def stop_calculation(self):
        if self.running:
            self.running = False
            self.stop_event.set()
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_var.set("Stopped")
            
            if self.csv_writer:
                self.csv_writer.close()
                self.csv_writer = None
                
    def clear_data(self):
        self.feature_history = []
        self.update_plots()
        self.text_display.delete(1.0, tk.END)
        self.status_var.set("Data cleared")
        
    def process_data(self):
        while not self.stop_event.is_set():
            try:
                topic = self.pose_socket.recv_string()
                data_json = self.pose_socket.recv_string()
                pose_data = json.loads(data_json)
                
                features = self.calculator.calculate_features(pose_data)
                
                if features:
                    # Send features via ZeroMQ
                    self.feature_socket.send_string("FeatureData", zmq.SNDMORE)
                    self.feature_socket.send_string(json.dumps(features))
                    
                    # Save to CSV if enabled
                    if self.save_csv and self.csv_writer:
                        self.csv_writer.write(features)
                    
                    # Update display
                    self.update_display(features)
                    
                    # Store for plotting
                    self.feature_history.append(features)
                    if len(self.feature_history) > self.max_history:
                        self.feature_history.pop(0)
                    
                    # Update plots
                    self.update_plots()
                    
            except zmq.Again:
                continue
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                time.sleep(1)
                
    def update_display(self, features):
        display_text = (
            f"⏱️ Timestamp: {features['Feature_Timestamp']}\n"
            f"📊 Frame Rate: {features['Frame_Rate']:.2f} fps\n"
            f"📐 CoG Angle: {features['CoG_Angle']:.2f} degrees\n"
            f"🏃 Movement Rate: {features['Movement_Rate']:.4f}\n"
            "----------------------------------------\n"
        )
        
        self.text_display.insert(tk.END, display_text)
        self.text_display.see(tk.END)  # Auto-scroll to bottom
        
    def update_plots(self):
        if not self.feature_history:
            return
            
        timestamps = [f['Feature_Timestamp'] for f in self.feature_history]
        frame_rates = [f['Frame_Rate'] for f in self.feature_history]
        cog_angles = [f['CoG_Angle'] for f in self.feature_history]
        movement_rates = [f['Movement_Rate'] for f in self.feature_history]
        
        # Convert timestamps to relative time for plotting
        try:
            first_time = datetime.strptime(timestamps[0], "%Y-%m-%d %H:%M:%S.%f")
            rel_times = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f") - 
                         first_time for ts in timestamps
                         ]
            x_values = [t.total_seconds() for t in rel_times]
        except:
            x_values = range(len(timestamps))
        
        # Update plot data
        self.line1.set_data(x_values, frame_rates)
        self.line2.set_data(x_values, cog_angles)
        self.line3.set_data(x_values, movement_rates)
        
        # Rescale and redraw
        for ax, data in zip([self.ax1, self.ax2, self.ax3], 
                            [frame_rates, cog_angles, movement_rates]):
            ax.relim()
            ax.autoscale_view()
        
        self.canvas.draw()
        
        # แปลงกราฟเป็นภาพและส่ง
        buf = io.BytesIO()
        self.figure.savefig(buf, format='jpg')
        buf.seek(0)
        img_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        self.graph_socket.send_string("GraphImage", zmq.SNDMORE)
        self.graph_socket.send_string(json.dumps({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "frame": img_data
        }))
        
    def on_close(self):
        self.stop_calculation()
        self.root.after(100, self.cleanup)
        self.root.destroy()
        
    def cleanup(self):
        if hasattr(self, 'pose_socket'):
            self.pose_socket.close()
        if hasattr(self, 'feature_socket'):
            self.feature_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        if self.csv_writer:
            self.csv_writer.close()

class FeatureCalculator:
    def __init__(self, use_real_scale=False):
        self.prev_frame = None
        self.prev_timestamp = None
        self.use_real_scale = use_real_scale
        self.connections = [
            (0, 11), (11, 12), (12, 24), (24, 23), (23, 11),
            (15, 13), (13, 11), (12, 14), (14, 16),
            (23, 25), (25, 27), (24, 26), (26, 28)
        ]

    def denormalize(self, x, y, max_width, max_height):
        """Convert from normalized to real scale"""
        real_x = x * max_width
        real_y = y * max_height
        return real_x, real_y

    def calculate_features(self, current_data):
        if self.prev_frame is None:
            self.prev_frame = current_data
            self.prev_timestamp = current_data["Image_Timestamp"]
            return None
        
        try:
            max_width = current_data["MAX_Width"]
            max_height = current_data["MAX_Height"]
            
            # Calculate Frame Rate
            current_time = datetime.strptime(current_data["Image_Timestamp"], "%Y-%m-%d %H:%M:%S.%f")
            prev_time = datetime.strptime(self.prev_timestamp, "%Y-%m-%d %H:%M:%S.%f")
            time_diff = (current_time - prev_time).total_seconds()
            frame_rate = 1 / time_diff if time_diff > 0 else 0
            
            # Get landmarks
            landmarks = current_data["Landmarks"]
            prev_landmarks = self.prev_frame["Landmarks"]
            
            # Center of Gravity Angle
            left_x, left_y = landmarks[23*2], landmarks[23*2+1]
            right_x, right_y = landmarks[24*2], landmarks[24*2+1]
            nose_x, nose_y = landmarks[0], landmarks[1]
            
            if self.use_real_scale:
                left_x, left_y = self.denormalize(left_x, left_y, max_width, max_height)
                right_x, right_y = self.denormalize(right_x, right_y, max_width, max_height)
                nose_x, nose_y = self.denormalize(nose_x, nose_y, max_width, max_height)
            
            cog_x = (right_x + left_x) / 2
            cog_y = (right_y + left_y) / 2
            dx = cog_x - nose_x
            dy = cog_y - nose_y
            cog_angle = np.arctan2(abs(dy), abs(dx)) * (180 / np.pi)
            
            # Calculate Movement Rate
            total_distance = 0.0
            num_connections = len(self.connections)
            
            for conn in self.connections:
                x1, y1 = landmarks[conn[0]*2], landmarks[conn[0]*2+1]
                x2, y2 = landmarks[conn[1]*2], landmarks[conn[1]*2+1]
                x1_prev, y1_prev = prev_landmarks[conn[0]*2], prev_landmarks[conn[0]*2+1]
                x2_prev, y2_prev = prev_landmarks[conn[1]*2], prev_landmarks[conn[1]*2+1]
                
                if self.use_real_scale:
                    x1, y1 = self.denormalize(x1, y1, max_width, max_height)
                    x2, y2 = self.denormalize(x2, y2, max_width, max_height)
                    x1_prev, y1_prev = self.denormalize(x1_prev, y1_prev, max_width, max_height)
                    x2_prev, y2_prev = self.denormalize(x2_prev, y2_prev, max_width, max_height)
                
                start_point_diff = np.sqrt((x1 - x1_prev)**2 + (y1 - y1_prev)**2)
                end_point_diff = np.sqrt((x2 - x2_prev)**2 + (y2 - y2_prev)**2)
                total_distance += (start_point_diff + end_point_diff) / 2
            
            avg_distance = total_distance / num_connections
            movement_rate = avg_distance / time_diff if time_diff > 0 else 0.0
            
            # Update previous frame
            self.prev_frame = current_data
            self.prev_timestamp = current_data["Image_Timestamp"]
            
            return {
                "Feature_Timestamp": current_data["Image_Timestamp"],
                "Frame_Rate": frame_rate,
                "CoG_Angle": cog_angle,
                "Movement_Rate": movement_rate
            }
            
        except Exception as e:
            print(f"Error calculating features: {e}")
            return None

class CSVWriter:
    def __init__(self, filename="feature_data.csv"):
        self.filename = filename
        self.file = None
        self.writer = None
        self.is_first_write = True
        
    def open(self):
        file_exists = os.path.isfile(self.filename)
        
        self.file = open(self.filename, mode='a', newline='')
        self.writer = csv.writer(self.file)
        
        if not file_exists or os.stat(self.filename).st_size == 0:
            self.writer.writerow(["Timestamp", "Frame_Rate", "CoG_Angle", "Movement_Rate"])
            self.is_first_write = False
    
    def write(self, feature_data):
        if self.writer is None:
            self.open()
        
        try:
            self.writer.writerow([
                feature_data["Feature_Timestamp"],
                feature_data["Frame_Rate"],
                feature_data["CoG_Angle"],
                feature_data["Movement_Rate"]
            ])
            self.file.flush()
        except Exception as e:
            print(f"Error writing to CSV: {e}")
    
    def close(self):
        if self.file is not None:
            self.file.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = FeatureCalculatorApp(root)
    
    # Handle window close event
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    root.mainloop()