import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.semi_supervised import LabelPropagation
from mpl_toolkits.mplot3d import Axes3D
from threading import Thread
import json
import zmq
from datetime import datetime
from config import PORTS

class FallDetector:
    def __init__(self):
        # ZeroMQ setup
        self.context = zmq.Context()
        self.socket.bind(f"tcp://*:{PORTS['feature_data']}")
        
        # Socket for receiving Feature data from feature.py
        self.feature_socket = self.context.socket(zmq.SUB)
        self.feature_socket.connect("tcp://localhost:5559")
        self.feature_socket.setsockopt_string(zmq.SUBSCRIBE, "FeatureData")
        self.feature_socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
        
        # Socket for sending alerts
        self.alert_socket = self.context.socket(zmq.PUB)
        self.alert_socket.bind("tcp://*:5558")  # For sending fall alerts
        
        # เพิ่ม socket สำหรับรับข้อมูลโซน
        self.zone_socket = self.context.socket(zmq.SUB)
        self.zone_socket.connect("tcp://localhost:5557")
        self.zone_socket.setsockopt_string(zmq.SUBSCRIBE, "ZoneDetector")
        
        # ใช้ Poller เพื่อจัดการหลาย socket
        self.poller = zmq.Poller()
        self.poller.register(self.feature_socket, zmq.POLLIN)
        self.poller.register(self.zone_socket, zmq.POLLIN)
        
        # Load models and data
        self.load_model()
        
        # Start processing thread
        self.running = True
        self.process_thread = Thread(target=self.process_features, daemon=True)
        self.process_thread.start()
    
    def load_model(self):
        """Load pre-trained label propagation model"""
        try:
            # Load your pre-trained model here
            self.label_prop_model = LabelPropagation(
                kernel='knn',
                n_neighbors=9,
                max_iter=100,
                tol=1e-3
            )
            # Load your pre-trained weights or data
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
    
    def process_features(self):
        """Continuously process incoming feature data"""
        while self.running:
            socks = dict(self.poller.poll(100))
            if self.feature_socket in socks:
                try:
                    # Receive feature data
                    topic = self.feature_socket.recv_string()
                    data_json = self.feature_socket.recv_string()
                    feature_data = json.loads(data_json)
                    
                    # Detect fall state
                    fall_state = self.detect_fall(feature_data)
                    
                    # Send alert
                    self.send_alert(fall_state)
                    
                except zmq.Again:
                    continue
                except Exception as e:
                    print(f"Error processing features: {e}")
                    continue
                
            if self.zone_socket in socks:
                topic = self.zone_socket.recv_string()
                zone_data = json.loads(self.zone_socket.recv_string())
                self.current_zones = zone_data  # บันทึกข้อมูลโซนล่าสุด
    
    def detect_fall(self, features):
        """
        Detect fall state from features
        Returns:
            0: ไม่ล้ม (No fall)
            1: กำลังจะล้ม (About to fall)
            2: ล้ม (Fallen)
        """
        try:
            # Prepare features (Frame_Rate, CoG_Angle, Movement_Rate)
            features_array = np.array([[features['Frame_Rate'], 
                                     features['CoG_Angle'], 
                                     features['Movement_Rate']]])
            
            # Predict using the model
            prediction = self.label_prop_model.predict(features_array)[0]
            
            return int(prediction)
        except Exception as e:
            print(f"Error in fall detection: {e}")
            return 0
    
    def send_alert(self, fall_state, zone=None):
        """Send alert through ZMQ"""
        alert_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            'state': fall_state,
            'zone': zone,
            'state_description': self.get_state_description(fall_state)
        }
        
        self.alert_socket.send_string("FallAlert", zmq.SNDMORE)
        self.alert_socket.send_string(json.dumps(alert_data))
        
        print(f"Alert sent: {alert_data}")
    
    def get_state_description(self, state):
        descriptions = {
            0: "ไม่ล้ม (No fall)",
            1: "กำลังจะล้ม (About to fall)",
            2: "ล้ม (Fallen)"
        }
        return descriptions.get(state, "Unknown state")
    
    def stop(self):
        """Clean up resources"""
        self.running = False
        if hasattr(self, 'feature_socket'):
            self.feature_socket.close()
        if hasattr(self, 'alert_socket'):
            self.alert_socket.close()
        if hasattr(self, 'context'):
            self.context.term()

if __name__ == "__main__":
    detector = FallDetector()
    
    try:
        while True:
            # Main thread can do other work here
            # Or just sleep to keep the program running
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        detector.stop()
        print("Program terminated by user")