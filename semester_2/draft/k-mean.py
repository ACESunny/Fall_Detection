import zmq
import json
import numpy as np
from datetime import datetime
import time
import csv
import os
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import StandardScaler

class MovementClassifier:
    def __init__(self):
        self.kmeans = KMeans(n_clusters=7, random_state=42)  # 7 clusters for all movement types
        self.scaler = StandardScaler()
        self.is_trained = False
        self.cluster_labels = {}  # Will be assigned based on conditions
        
    def train_from_csv(self, filename):
        """ฝึกโมเดลจากไฟล์ CSV"""
        try:
            df = pd.read_csv(filename)
            features = df[['CoG_Angle', 'Movement_Rate']].values  # Fixed typo in column name
            
            # ปรับขนาดข้อมูล
            scaled_features = self.scaler.fit_transform(features)
            
            # ฝึกโมเดล K-Means
            self.kmeans.fit(scaled_features)
            self.is_trained = True
            
            # กำหนด label ให้กับแต่ละ cluster ตามเงื่อนไขใหม่
            self.assign_cluster_labels()
            
            print("Model training completed with 7 movement categories!")
            self.plot_clusters(features, "Movement Classification Clusters")
            
        except Exception as e:
            print(f"Error during model training: {e}")
    
    def assign_cluster_labels(self):
        """กำหนด label ให้กับ cluster ตามเงื่อนไขที่ระบุ"""
        centers = self.scaler.inverse_transform(self.kmeans.cluster_centers_)
        
        for i, (angle, rate) in enumerate(centers):
            if rate < 5 and angle < 10:
                self.cluster_labels[i] = "Fallen"
            elif 5 <= rate < 20 and angle < 10:
                self.cluster_labels[i] = "Lying still"
            elif 5 <= rate < 20 and 10 <= angle < 70:
                self.cluster_labels[i] = "About to fall"
            elif 20 <= rate < 50 and angle >= 70:
                self.cluster_labels[i] = "Walking"
            elif rate >= 50 and angle >= 70:
                self.cluster_labels[i] = "Running"
            elif 20 <= rate < 50 and angle < 10:
                self.cluster_labels[i] = "Crawling"
            elif 5 <= rate < 20 and angle < 10:
                self.cluster_labels[i] = "Restless lying"
            else:
                self.cluster_labels[i] = f"Unclassified {i}"

    def predict_movement(self, cog_angle, movement_rate):
        """ทำนายการเคลื่อนไหวตามเงื่อนไขที่กำหนด"""
        if not self.is_trained:
            return "Untrained model"
        
        # ใช้กฎที่กำหนดแทนการทำนายด้วย K-Means โดยตรง
        if movement_rate < 5 and cog_angle < 10:
            return "Fallen"
        elif 5 <= movement_rate < 20:
            if cog_angle < 10:
                return "Lying still"
            elif 10 <= cog_angle < 70:
                return "About to fall"
        elif 20 <= movement_rate < 50:
            if cog_angle >= 70:
                return "Walking"
            elif cog_angle < 10:
                return "Crawling"
        elif movement_rate >= 50 and cog_angle >= 70:
            return "Running"
        elif 5 <= movement_rate < 20 and cog_angle < 10:
            return "Restless lying"
        return "Unclassified"

    def plot_clusters(self, features, title):
        """แสดงผลกราฟการจัดกลุ่ม"""
        if not self.is_trained:
            return
            
        plt.figure(figsize=(12, 8))
        
        # แสดงข้อมูลและกลุ่ม
        scatter = plt.scatter(features[:, 0], features[:, 1], c=self.kmeans.labels_, cmap='tab20', alpha=0.6)
        
        # แสดงจุดศูนย์กลางกลุ่ม
        centers = self.scaler.inverse_transform(self.kmeans.cluster_centers_)
        plt.scatter(centers[:, 0], centers[:, 1], c='red', s=200, alpha=0.8, marker='X')
        
        # เส้นแบ่งเงื่อนไข
        plt.axvline(x=10, color='gray', linestyle='--', alpha=0.5)
        plt.axvline(x=70, color='gray', linestyle='--', alpha=0.5)
        plt.axhline(y=5, color='gray', linestyle='--', alpha=0.5)
        plt.axhline(y=20, color='gray', linestyle='--', alpha=0.5)
        plt.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        
        # ตั้งชื่อกราฟและแกน
        plt.title(title)
        plt.xlabel('CoG Angle (degrees)')
        plt.ylabel('Movement Rate')
        plt.colorbar(scatter, label='Cluster')
        
        # เพิ่มคำอธิบาย
        for i, (angle, rate) in enumerate(centers):
            status = self.cluster_labels.get(i, "Unknown")
            plt.annotate(f'{status}\n(A:{angle:.1f}°, R:{rate:.1f})', 
                        (angle, rate),
                        textcoords="offset points", 
                        xytext=(0,10), 
                        ha='center')
        
        plt.grid(True)
        plt.show()

class RealTimeProcessor:
    def __init__(self):
        self.context = zmq.Context()
        self.feature_socket = self.context.socket(zmq.SUB)
        self.feature_socket.connect("tcp://localhost:5559")
        self.feature_socket.setsockopt_string(zmq.SUBSCRIBE, "FeatureData")
        
        self.prediction_socket = self.context.socket(zmq.PUB)
        self.prediction_socket.bind("tcp://*:5560")
        
        self.classifier = MovementClassifier()
    
    def process_realtime(self):
        print("Waiting for movement data...")
        try:
            while True:
                try:
                    topic = self.feature_socket.recv_string()
                    data_json = self.feature_socket.recv_string()
                    feature_data = json.loads(data_json)
                    
                    # ทำนายสถานะ
                    movement = self.classifier.predict_movement(
                        feature_data['CoG_Angle'], 
                        feature_data['Movement_Rate']
                    )
                    
                    # สร้างข้อมูลผลลัพธ์
                    result = {
                        'timestamp': feature_data['Feature_Timestamp'],
                        'cog_angle': feature_data['CoG_Angle'],
                        'movement_rate': feature_data['Movement_Rate'],
                        'movement_status': movement
                    }
                    
                    # ส่งผลการทำนาย
                    self.prediction_socket.send_string("MovementStatus", zmq.SNDMORE)
                    self.prediction_socket.send_string(json.dumps(result))
                    
                    # แสดงผลลัพธ์
                    self.display_movement_result(result)
                    
                except zmq.Again:
                    time.sleep(0.01)
                except Exception as e:
                    print(f"Processing error: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("Stopping movement analysis...")

    def display_movement_result(self, result):
        """แสดงผลลัพธ์การวิเคราะห์การเคลื่อนไหว"""
        print(f"\nTimestamp: {result['timestamp']}")
        print(f"CoG Angle: {result['cog_angle']:.1f}°")
        print(f"Movement Rate: {result['movement_rate']:.2f}")
        print(f"Status: {result['movement_status'].upper()}")
        
        # แสดงคำแนะนำตามสถานะ
        if result['movement_status'] == "Fallen":
            print("🚨 EMERGENCY: Person has fallen!")
            print("Action: Immediate assistance required")
        elif result['movement_status'] == "About to fall":
            print("⚠️ WARNING: High fall risk detected")
            print("Action: Provide support immediately")
        elif result['movement_status'] == "Walking":
            print("🚶 Normal walking pattern")
            print("Action: Monitoring only")
        elif result['movement_status'] == "Running":
            print("🏃 High activity detected")
            print("Action: Ensure safe environment")
        elif result['movement_status'] == "Lying still":
            print("🛌 Person is lying down")
            print("Action: Check comfort level")
        elif result['movement_status'] == "Crawling":
            print("🐢 Person is crawling")
            print("Action: Assess need for assistance")
        elif result['movement_status'] == "Restless lying":
            print("🛏️ Person is restless while lying")
            print("Action: Check for discomfort")
        else:
            print("❓ Unclassified movement")
            print("Action: Further observation needed")

def main_menu():
    print("\nMovement Classification System")
    print("1. Train model from CSV")
    print("2. Start real-time analysis")
    print("3. Test with manual input")
    print("4. Exit")
    
    classifier = MovementClassifier()
    
    while True:
        choice = input("Select option (1-4): ")
        
        if choice == '1':
            filename = input("CSV filename [default: movement_data.csv]: ") or "movement_data.csv"
            if os.path.exists(filename):
                classifier.train_from_csv(filename)
            else:
                print(f"File not found: {filename}")
        
        elif choice == '2':
            if not classifier.is_trained:
                print("Please train model first")
                continue
            processor = RealTimeProcessor()
            processor.classifier = classifier
            processor.process_realtime()
        
        elif choice == '3':
            try:
                angle = float(input("Enter CoG Angle (0-90°): "))
                rate = float(input("Enter Movement Rate: "))
                status = classifier.predict_movement(angle, rate)
                print(f"\nMovement status: {status.upper()}")
            except ValueError:
                print("Invalid input values")
        
        elif choice == '4':
            print("Exiting system...")
            break
        
        else:
            print("Invalid option selected")

if __name__ == "__main__":
    main_menu()