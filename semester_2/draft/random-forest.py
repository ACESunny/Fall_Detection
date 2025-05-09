import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler
import joblib
import os

class EnhancedMovementClassifier:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.movement_types = {
            0: 'Fallen',
            1: 'About to fall',
            2: 'Walking',
            3: 'Running',
            4: 'Lying still',
            5: 'Crawling',
            6: 'Restless lying'
        }
        
    def load_and_preprocess_data(self, filename):
        """โหลดและเตรียมข้อมูลจากไฟล์ CSV"""
        try:
            df = pd.read_csv(filename)
            
            # ตรวจสอบคอลัมน์ที่จำเป็น
            required_cols = ['CoG_Angle', 'Movement_Rate']
            if not all(col in df.columns for col in required_cols):
                raise ValueError("Missing required columns in CSV file")
            
            # สร้าง label ตามเงื่อนไขที่กำหนด
            df['Movement_Type'] = df.apply(self._label_movement, axis=1)
            
            # แยก features และ labels
            X = df[['CoG_Angle', 'Movement_Rate']].values
            y = df['Movement_Type'].values
            
            return X, y
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return None, None
    
    def _label_movement(self, row):
        """กำหนด label ให้กับแต่ละแถวข้อมูลตามเงื่อนไข"""
        angle = row['CoG_Angle']
        rate = row['Movement_Rate']
        
        if rate < 5 and angle < 10:
            return 0  # Fallen
        elif 5 <= rate < 20:
            if angle < 10:
                return 4  # Lying still
            elif 10 <= angle < 70:
                return 1  # About to fall
        elif 20 <= rate < 50:
            if angle >= 70:
                return 2  # Walking
            elif angle < 10:
                return 5  # Crawling
        elif rate >= 50 and angle >= 70:
            return 3  # Running
        elif 5 <= rate < 20 and angle < 10:
            return 6  # Restless lying
        
        # หากไม่ตรงเงื่อนไขใดๆ ให้ใช้กฎเสริม
        return self._fallback_classification(angle, rate)
    
    def _fallback_classification(self, angle, rate):
        """กฎสำรองสำหรับข้อมูลที่ไม่ตรงเงื่อนไขหลัก"""
        if angle < 15:
            return 4 if rate < 15 else 5  # Lying still or Crawling
        elif angle < 45:
            return 1  # About to fall
        else:
            return 2 if rate < 60 else 3  # Walking or Running
    
    def train_model(self, X, y, test_size=0.2):
        """ฝึกโมเดลด้วย Random Forest"""
        try:
            # แบ่งข้อมูลสำหรับ training และ testing
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # ปรับขนาดข้อมูล
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # ฝึกโมเดล
            self.model.fit(X_train_scaled, y_train)
            
            # ประเมินโมเดล
            y_pred = self.model.predict(X_test_scaled)
            print("\nModel Evaluation:")
            print(classification_report(y_test, y_pred, target_names=self.movement_types.values()))
            
            self.is_trained = True
            return True
            
        except Exception as e:
            print(f"Error training model: {e}")
            return False
    
    def predict_movement(self, cog_angle, movement_rate):
        """ทำนายประเภทการเคลื่อนไหว"""
        if not self.is_trained:
            return "Model not trained"
        
        try:
            # ปรับขนาดข้อมูล
            scaled_data = self.scaler.transform([[cog_angle, movement_rate]])
            
            # ทำนาย
            prediction = self.model.predict(scaled_data)[0]
            
            return self.movement_types.get(prediction, "Unknown")
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return "Error"
    
    def save_model(self, filename):
        """บันทึกโมเดลที่ฝึกไว้"""
        try:
            joblib.dump({
                'model': self.model,
                'scaler': self.scaler,
                'movement_types': self.movement_types
            }, filename)
            print(f"Model saved to {filename}")
        except Exception as e:
            print(f"Error saving model: {e}")
    
    def load_model(self, filename):
        """โหลดโมเดลที่บันทึกไว้"""
        try:
            if os.path.exists(filename):
                data = joblib.load(filename)
                self.model = data['model']
                self.scaler = data['scaler']
                self.movement_types = data['movement_types']
                self.is_trained = True
                print(f"Model loaded from {filename}")
                return True
            else:
                print(f"File not found: {filename}")
                return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False


def main():
    print("Enhanced Movement Classification System")
    classifier = EnhancedMovementClassifier()
    
    while True:
        print("\nMenu:")
        print("1. Train new model")
        print("2. Load existing model")
        print("3. Test with manual input")
        print("4. Exit")
        
        choice = input("Select option (1-4): ")
        
        if choice == '1':
            filename = input("Enter CSV filename (default: feature_data.csv): ") or "feature_data.csv"
            X, y = classifier.load_and_preprocess_data(filename)
            
            if X is not None and y is not None:
                if classifier.train_model(X, y):
                    save = input("Save trained model? (y/n): ").lower()
                    if save == 'y':
                        model_file = input("Enter model filename (default: movement_model.pkl): ") or "movement_model.pkl"
                        classifier.save_model(model_file)
        
        elif choice == '2':
            model_file = input("Enter model filename (default: movement_model.pkl): ") or "movement_model.pkl"
            classifier.load_model(model_file)
        
        elif choice == '3':
            if not classifier.is_trained:
                print("Please train or load a model first")
                continue
                
            try:
                angle = float(input("Enter CoG Angle (0-90°): "))
                rate = float(input("Enter Movement Rate: "))
                movement = classifier.predict_movement(angle, rate)
                print(f"\nPredicted Movement: {movement}")
            except ValueError:
                print("Invalid input values")
        
        elif choice == '4':
            print("Exiting system...")
            break
        
        else:
            print("Invalid option selected")

if __name__ == "__main__":
    main()