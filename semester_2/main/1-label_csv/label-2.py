import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.semi_supervised import LabelPropagation
from mpl_toolkits.mplot3d import Axes3D

# 1. อ่านข้อมูลจากไฟล์ที่ถูก Label แล้ว
labeled_data = pd.read_csv('combined_filtered_data_with_new_labels.csv')
# Remove outliers where Movement_Rate > 1000
labeled_data = labeled_data[labeled_data['Movement_Rate'] <= 1000]
X_labeled = labeled_data[['Frame_Rate', 'CoG_Angle', 'Movement_Rate']].values
y_labeled = labeled_data['Label'].values

# 2. อ่านข้อมูลจากไฟล์ที่ยังไม่มี Label
unlabeled_data = pd.read_csv('fall.csv')
# Remove outliers where Movement_Rate > 1000
unlabeled_data = unlabeled_data[unlabeled_data['Movement_Rate'] <= 1000]
X_unlabeled = unlabeled_data[['Frame_Rate', 'CoG_Angle', 'Movement_Rate']].values

# 3. รวมข้อมูลและสร้าง array labels
X = np.vstack([X_labeled, X_unlabeled])
y = np.concatenate([y_labeled, np.full(X_unlabeled.shape[0], -1)])

# 4. สร้างและฝึกโมเดล Label Propagation
label_prop_model = LabelPropagation(
    kernel='knn',        # 'rbf' (default) or 'knn'
    gamma=100,            # only for 'rbf' kernel: higher = tighter similarity
    n_neighbors=9,       # only for 'knn' kernel: number of neighbors
    max_iter=100,       # max iterations to converge
    tol=1e-3             # tolerance for stopping criterion
)
label_prop_model.fit(X, y)

# 5. ทำนาย label สำหรับข้อมูลที่ยังไม่มี label
predicted_labels = label_prop_model.transduction_[len(X_labeled):]

# 6. เพิ่ม label ลงในข้อมูลเดิม
unlabeled_data['Label'] = predicted_labels

# แสดงผลกราฟ
plt.figure(figsize=(15, 10))

# กราฟ 1: ข้อมูลก่อนทำ Label Propagation
plt.subplot(2, 2, 1)
sns.scatterplot(x='CoG_Angle', y='Movement_Rate', hue='Label', 
                data=labeled_data, palette='viridis', s=100)
plt.title('Labeled Data Before Propagation (Outliers Removed)')
plt.xlabel('CoG Angle')
plt.ylabel('Movement Rate')

# กราฟ 2: ข้อมูลที่ยังไม่มี Label ก่อนทำนาย
plt.subplot(2, 2, 2)
sns.scatterplot(x='CoG_Angle', y='Movement_Rate', 
                data=unlabeled_data, color='gray', s=100, alpha=0.5)
plt.title('Unlabeled Data Before Propagation (Outliers Removed)')
plt.xlabel('CoG Angle')
plt.ylabel('Movement Rate')

# กราฟ 3: ผลลัพธ์หลังทำ Label Propagation
plt.subplot(2, 2, 3)
combined_data = pd.concat([labeled_data, unlabeled_data])
sns.scatterplot(x='CoG_Angle', y='Movement_Rate', hue='Label', 
                data=combined_data, palette='viridis', s=100)
plt.title('All Data After Label Propagation (Outliers Removed)')
plt.xlabel('CoG Angle')
plt.ylabel('Movement Rate')

# กราฟ 4: 3D Plot แสดงความสัมพันธ์ของ Features ทั้ง 3
plt.subplot(2, 2, 4, projection='3d')
scatter = plt.gca().scatter(
    combined_data['Frame_Rate'], 
    combined_data['CoG_Angle'], 
    combined_data['Movement_Rate'], 
    c=combined_data['Label'], cmap='viridis')
plt.title('3D View: Frame Rate vs CoG Angle vs Movement Rate (Outliers Removed)')
plt.xlabel('Frame Rate')
plt.ylabel('CoG Angle')
plt.gca().set_zlabel('Movement Rate')
plt.colorbar(scatter, label='Label')

plt.tight_layout()
plt.show()

# บันทึกไฟล์ผลลัพธ์
unlabeled_data.to_csv('new_labeled_data.csv', index=False)
print("การทำ Label Propagation เสร็จสิ้น ผลลัพธ์ถูกบันทึกใน new_labeled_data.csv")