import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

DATA_DIR = '.'
KEYWORDS_CSV = os.path.join(DATA_DIR, 'Voice_Clone_Detector_Keywords.csv')
PARAGRAPHS_CSV = os.path.join(DATA_DIR, 'Voice_Clone_Detector_Paragraphs.csv')
MODEL_FILE = 'hindi_scam_model.pkl'
VECTORIZER_FILE = 'tfidf_vectorizer.pkl'

def clean_text(text):

    import re
    return re.sub(r'\s+', ' ', text).strip()

def load_data():
    
    keywords_df = pd.read_csv(KEYWORDS_CSV)
    paragraphs_df = pd.read_csv(PARAGRAPHS_CSV)
    kw_data = keywords_df[['Text_Feature', 'Is_Scam_Label']].copy()
    kw_data.columns = ['text', 'label']
    kw_data['source'] = 'keywords'
    para_data = paragraphs_df[['Transcript_Text', 'Is_Scam_Label']].copy()
    para_data.columns = ['text', 'label']
    para_data['source'] = 'paragraphs'
    full_df = pd.concat([kw_data, para_data], ignore_index=True)
    full_df = full_df.dropna(subset=['text', 'label'])
    full_df['label'] = full_df['label'].astype(int)
    print(f'  Keywords CSV: {len(keywords_df)} rows')
    print(f'  Paragraphs CSV: {len(paragraphs_df)} rows')
    print(f'  Total combined rows: {len(full_df)}')
    print(f'  Scam messages: {(full_df['label'] == 1).sum()}')
    print(f'  Safe messages:  {(full_df['label'] == 0).sum()}')
    return full_df

def prepare_features(df, max_features=10000):
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        min_df=2, max_df=0.9, lowercase=False,
    )
    
    X = vectorizer.fit_transform(df['text'].apply(clean_text))
    y = df['label'].values
    print(f'  TF-IDF features shape: {X.shape}')
    print(f'  Number of unique words: {len(vectorizer.get_feature_names_out())}')
    return X, y, vectorizer

def train_and_evaluate(X, y, vectorizer):
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f'  Training set: {X_train.shape[0]} messages')
    print(f'  Test set:     {X_test.shape[0]} messages')
    print('Training model...')
    model = LogisticRegression(max_iter=1000, C=1.0, class_weight='balanced')
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f'  Test Accuracy: {accuracy:.2%}')
    print('  Classification Report:')
    print(classification_report(y_test, y_pred, target_names=['Safe', 'Scam']))
    feature_names = vectorizer.get_feature_names_out()
    coefs = model.coef_[0]
    top_positive = np.argsort(coefs)[-20:]
    top_negative = np.argsort(coefs)[:20]
    print('  Top 10 SCAM words:')
    
    for i in top_positive[-10:]:
    
        print(f'    +{coefs[i]:.3f}  {feature_names[i]}')
    
    print('  Top 10 SAFE words:')
    
    for i in top_negative[:10]:
    
        print(f'    {coefs[i]:+.3f}  {feature_names[i]}')
    
    return model, vectorizer

def save_model(model, vectorizer):
    
    joblib.dump(model, MODEL_FILE)
    joblib.dump(vectorizer, VECTORIZER_FILE)
    print(f'  Model saved to: {MODEL_FILE}')
    print(f'  Vectorizer saved to: {VECTORIZER_FILE}')

def main():
    
    print('=' * 60)
    print('  Training Hindi Scam Detection Model')
    print('=' * 60)
    
    if not os.path.exists(KEYWORDS_CSV):
    
        print(f'ERROR: Could not find {KEYWORDS_CSV}')
        exit(1)
    
    if not os.path.exists(PARAGRAPHS_CSV):
    
        print(f'ERROR: Could not find {PARAGRAPHS_CSV}')
        exit(1)
    
    df = load_data()
    X, y, vectorizer = prepare_features(df, max_features=15000)
    model, vectorizer = train_and_evaluate(X, y, vectorizer)
    save_model(model, vectorizer)
    print('=' * 60)
    print('  Training Complete!')
    print('=' * 60)
    print('  To use the model:')
    print('    import joblib')
    print('    model = joblib.load(\'hindi_scam_model.pkl\')')
    print('    vectorizer = joblib.load(\'tfidf_vectorizer.pkl\')')
    print('    X = vectorizer.transform([\'Hindi text here\'])')
    print('    prediction = model.predict(X)[0]  # 1=Scam, 0=Safe')

if __name__ == '__main__':

    main()
