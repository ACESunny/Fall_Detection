import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import os
from sklearn.metrics import silhouette_score

class PureKMeansClassifier:
    def __init__(self):
        self.kmeans = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.optimal_clusters = 0

    def load_data(self, filename):
        """โหลดข้อมูลจากไฟล์ CSV"""
        try:
            df = pd.read_csv(filename)
            if not all(col in df.columns for col in ['CoG_Angle', 'Movement_Rate']):
                raise ValueError("Required columns not found")
            return df[['CoG_Angle', 'Movement_Rate']].values
        except Exception as e:
            print(f"Error loading data: {e}")
            return None

    def find_optimal_clusters(self, data, max_k=10):
        """หาจำนวนกลุ่มที่เหมาะสมโดยใช้ silhouette score"""
        scaled_data = self.scaler.fit_transform(data)
        best_score = -1
        best_k = 2
        
        for k in range(2, max_k+1):
            kmeans = KMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(scaled_data)
            score = silhouette_score(scaled_data, labels)
            
            if score > best_score:
                best_score = score
                best_k = k
                
        self.optimal_clusters = best_k
        print(f"Optimal number of clusters found: {best_k}")
        return best_k

    def train(self, data):
        """ฝึกโมเดล K-Means"""
        try:
            # หาจำนวนกลุ่มที่เหมาะสม
            k = self.find_optimal_clusters(data)
            
            # ปรับขนาดข้อมูล
            scaled_data = self.scaler.fit_transform(data)
            
            # ฝึกโมเดล
            self.kmeans = KMeans(n_clusters=k, random_state=42)
            self.kmeans.fit(scaled_data)
            self.is_trained = True
            
            print("K-Means training completed!")
            self.plot_clusters(data)
            return True
            
        except Exception as e:
            print(f"Training error: {e}")
            return False

    def predict(self, cog_angle, movement_rate):
        """ทำนายกลุ่ม"""
        if not self.is_trained:
            return "Model not trained"
        
        try:
            scaled_data = self.scaler.transform([[cog_angle, movement_rate]])
            cluster = self.kmeans.predict(scaled_data)[0]
            return f"Cluster {cluster}"
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return "Error"

    def plot_clusters(self, data):
        """แสดงผลกราฟการจัดกลุ่ม"""
        if not self.is_trained:
            return
            
        plt.figure(figsize=(12, 8))
        scaled_data = self.scaler.transform(data)
        labels = self.kmeans.labels_
        centroids = self.scaler.inverse_transform(self.kmeans.cluster_centers_)
        
        plt.scatter(data[:, 0], data[:, 1], c=labels, cmap='viridis', alpha=0.6)
        plt.scatter(centroids[:, 0], centroids[:, 1], c='red', marker='X', s=200, alpha=0.8)
        
        plt.title(f'K-Means Clustering ({self.optimal_clusters} clusters)')
        plt.xlabel('CoG Angle (degrees)')
        plt.ylabel('Movement Rate')
        plt.grid(True)
        plt.show()

def main():
    print("Pure K-Means Classification System")
    classifier = PureKMeansClassifier()
    
    while True:
        print("\nMenu:")
        print("1. Train model from CSV")
        print("2. Test with manual input")
        print("3. Exit")
        
        choice = input("Select option (1-3): ")
        
        if choice == '1':
            filename = input("Enter CSV filename (default: feature_data.csv): ") or "feature_data.csv"
            if os.path.exists(filename):
                data = classifier.load_data(filename)
                if data is not None:
                    classifier.train(data)
            else:
                print(f"File not found: {filename}")
        
        elif choice == '2':
            if not classifier.is_trained:
                print("Please train the model first")
                continue
                
            try:
                angle = float(input("Enter CoG Angle: "))
                rate = float(input("Enter Movement Rate: "))
                cluster = classifier.predict(angle, rate)
                print(f"\nPredicted: {cluster}")
            except ValueError:
                print("Invalid input values")
        
        elif choice == '3':
            print("Exiting program...")
            break
        
        else:
            print("Invalid option selected")

if __name__ == "__main__":
    main()