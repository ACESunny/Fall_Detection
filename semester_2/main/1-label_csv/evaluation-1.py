import pandas as pd
import numpy as np
from sklearn.semi_supervised import LabelPropagation
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import (confusion_matrix, accuracy_score, 
                           precision_score, recall_score, f1_score)
from sklearn.model_selection import train_test_split

# 1. Load data
labeled_data = pd.read_csv('combined_filtered_data_with_new_labels.csv')
unlabeled_data = pd.read_csv('fall.csv')

# 2. Prepare features and labels
X_labeled = labeled_data[['Frame_Rate', 'CoG_Angle', 'Movement_Rate']].values
y_labeled = labeled_data['Label'].values
X_unlabeled = unlabeled_data[['Frame_Rate', 'CoG_Angle', 'Movement_Rate']].values

# 3. Split labeled data into train/test sets (80/20)
X_train, X_test, y_train, y_test = train_test_split(
    X_labeled, y_labeled, test_size=0.4, random_state=42
)

# 4. Label Propagation (using training data + unlabeled data)
X_for_propagation = np.vstack([X_train, X_unlabeled])
y_for_propagation = np.concatenate([y_train, np.full(X_unlabeled.shape[0], -1)])

label_prop = LabelPropagation(kernel='knn', n_neighbors=9, max_iter=1000)
label_prop.fit(X_for_propagation, y_for_propagation)
pseudo_labels = label_prop.transduction_[len(X_train):]

# 5. Create enhanced training set (original labeled + pseudo-labeled)
X_enhanced = np.vstack([X_train, X_unlabeled])
y_enhanced = np.concatenate([y_train, pseudo_labels])

# 6. Train and evaluate models
results = []

def evaluate(model, model_name, X_test, y_test):
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    
    # Calculate metrics for each class
    metrics = []
    for i in range(len(np.unique(y_test))):
        tp = cm[i,i]
        fp = cm[:,i].sum() - tp
        fn = cm[i,:].sum() - tp
        tn = cm.sum() - (tp + fp + fn)
        
        metrics.append({
            'Model': model_name,
            'Class': i,
            'TP': tp,
            'FP': fp,
            'FN': fn,
            'TN': tn,
            'Accuracy': (tp + tn) / (tp + tn + fp + fn),
            'Precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
            'Recall': tp / (tp + fn) if (tp + fn) > 0 else 0,
            'F1': 2*tp / (2*tp + fp + fn) if (2*tp + fp + fn) > 0 else 0
        })
    
    # Calculate overall metrics
    overall = {
        'Model': model_name,
        'Class': 'Overall',
        'Accuracy': accuracy_score(y_test, y_pred),
        'Precision': precision_score(y_test, y_pred, average='weighted'),
        'Recall': recall_score(y_test, y_pred, average='weighted'),
        'F1': f1_score(y_test, y_pred, average='weighted')
    }
    
    return metrics + [overall]

# Train KNN
knn = KNeighborsClassifier(n_neighbors=9)
knn.fit(X_enhanced, y_enhanced)
results.extend(evaluate(knn, "KNN", X_test, y_test))

# Train SVM
svm = SVC(kernel='rbf', gamma='scale', C=1.0)
svm.fit(X_enhanced, y_enhanced)
results.extend(evaluate(svm, "SVM", X_test, y_test))

# 7. Save results
results_df = pd.DataFrame(results)
results_df.to_csv('model_evaluation_results.csv', index=False)

# 8. Save predictions
unlabeled_data['KNN_Prediction'] = knn.predict(X_unlabeled)
unlabeled_data['SVM_Prediction'] = svm.predict(X_unlabeled)
unlabeled_data.to_csv('all_predictions.csv', index=False)

print("Evaluation results saved to 'model_evaluation_results.csv'")
print("All predictions saved to 'all_predictions.csv'")