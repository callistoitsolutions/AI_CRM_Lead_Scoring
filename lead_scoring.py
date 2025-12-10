"""
Lead Scoring Model for Rental CRM Leads - Streamlit App
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
from xgboost import XGBClassifier
import warnings
warnings.filterwarnings('ignore')


def create_features(df):
    """Create meaningful features from the existing dataset columns"""
    df = df.copy()
    
    # 1. Budget Features
    df['budget_range'] = df['budget_max'] - df['budget_min']
    df['budget_mid'] = (df['budget_min'] + df['budget_max']) / 2
    df['budget_flexibility'] = df['budget_range'] / (df['budget_mid'] + 1)
    df['budget_mid_norm'] = (df['budget_mid'] - df['budget_mid'].min()) / (df['budget_mid'].max() - df['budget_mid'].min())
    df['budget_range_norm'] = (df['budget_range'] - df['budget_range'].min()) / (df['budget_range'].max() - df['budget_range'].min())
    
    # 2. Area Features
    area_freq = df['preferred_area'].value_counts(normalize=True)
    df['area_popularity'] = df['preferred_area'].map(area_freq)
    df['area_tier'] = pd.cut(df['area_popularity'], 
                            bins=[0, 0.02, 0.04, 1.0], 
                            labels=['Low', 'Medium', 'High'])
    
    # 3. User Type Features
    user_type_mapping = {
        'Family': 3,
        'Working Professionals': 2,
        'Bachelor': 1,
        'Company Guest': 2
    }
    df['user_type_score'] = df['user_type'].map(user_type_mapping).fillna(1)
    
    # 4. BHK Features
    df['bhk_score'] = df['bhk'] / 3.0
    
    # 5. Move-in Time Features
    move_in_mapping = {
        'Immediate': 4,
        'Within 15 Days': 3,
        '1 Month': 2,
        '2 Months': 1
    }
    df['move_in_urgency'] = df['move_in_time'].map(move_in_mapping).fillna(1)
    
    # 6. Source Features
    source_mapping = {
        'Referral': 4,
        'Website': 3,
        'WhatsApp': 3,
        'Facebook': 2,
        'Instagram': 2,
        'Google Ads': 1
    }
    df['source_quality'] = df['source'].map(source_mapping).fillna(1)
    
    # 7. Composite Features
    df['lead_quality_score'] = (
        0.3 * df['budget_mid_norm'] +
        0.2 * df['area_popularity'] +
        0.2 * df['user_type_score'] / 3.0 +
        0.1 * df['bhk_score'] +
        0.1 * df['move_in_urgency'] / 4.0 +
        0.1 * df['source_quality'] / 4.0
    )
    
    return df


def create_target_variable(df):
    """Create a target variable based on lead quality indicators"""
    df = df.copy()
    
    high_budget = df['budget_mid'] > df['budget_mid'].quantile(0.6)
    popular_area = df['area_popularity'] > df['area_popularity'].quantile(0.6)
    urgent_move = df['move_in_urgency'] >= 3
    good_source = df['source_quality'] >= 3
    family_or_working = df['user_type'].isin(['Family', 'Working Professionals'])
    
    df['is_high_quality'] = (
        (high_budget.astype(int) + 
         popular_area.astype(int) + 
         urgent_move.astype(int) + 
         good_source.astype(int) + 
         family_or_working.astype(int)) >= 3
    ).astype(int)
    
    return df


def get_feature_importance(model, feature_names, categorical_cols):
    """Get feature importance from the model"""
    if hasattr(model.named_steps['classifier'], 'feature_importances_'):
        importances = model.named_steps['classifier'].feature_importances_
    else:
        return None
    
    preprocessor = model.named_steps['preprocessor']
    num_features = preprocessor.named_transformers_['num'].named_steps['scaler'].get_feature_names_out()
    cat_features = preprocessor.named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(categorical_cols)
    all_features = np.concatenate([num_features, cat_features])
    
    importance_df = pd.DataFrame({
        'feature': all_features,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    return importance_df


def main():
    st.set_page_config(page_title="Lead Scoring System", layout="wide")
    st.title("🎯 Rental CRM Lead Scoring System")
    st.markdown("---")
    
    # File Upload
    uploaded_file = st.file_uploader("Upload your Excel file with leads", type=['xlsx', 'xls'])
    
    if uploaded_file is not None:
        try:
            # Load data
            with st.spinner("Loading data..."):
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Loaded {len(df)} leads successfully!")
            
            # Display basic info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Leads", len(df))
            with col2:
                st.metric("Total Columns", len(df.columns))
            with col3:
                st.metric("Missing Values", df.isnull().sum().sum())
            
            # Show data preview
            with st.expander("📊 View Data Preview"):
                st.dataframe(df.head(10))
            
            # Run Analysis Button
            if st.button("🚀 Run Lead Scoring Analysis", type="primary"):
                with st.spinner("Processing leads and training models..."):
                    
                    # Feature Engineering
                    df_featured = create_features(df)
                    df_featured = create_target_variable(df_featured)
                    
                    # Prepare features
                    feature_cols = [
                        'budget_mid_norm', 'budget_range_norm', 'budget_flexibility',
                        'area_popularity', 'user_type_score', 'bhk_score',
                        'move_in_urgency', 'source_quality', 'lead_quality_score'
                    ]
                    categorical_features = ['source', 'preferred_area', 'user_type', 'area_tier']
                    feature_cols.extend(categorical_features)
                    
                    X = df_featured[feature_cols].copy()
                    y = df_featured['is_high_quality'].copy()
                    
                    # Show target distribution
                    st.subheader("📈 Target Distribution")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("High Quality Leads", f"{y.sum()} ({y.mean():.1%})")
                    with col2:
                        st.metric("Regular Leads", f"{(~y).sum()} ({(~y).mean():.1%})")
                    
                    # Preprocessing
                    numerical_cols = X.select_dtypes(include=[np.number]).columns.tolist()
                    categorical_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
                    
                    numerical_transformer = Pipeline([
                        ('imputer', SimpleImputer(strategy='median')),
                        ('scaler', StandardScaler())
                    ])
                    
                    categorical_transformer = Pipeline([
                        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
                        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
                    ])
                    
                    preprocessor = ColumnTransformer(
                        transformers=[
                            ('num', numerical_transformer, numerical_cols),
                            ('cat', categorical_transformer, categorical_cols)
                        ]
                    )
                    
                    # Split data
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.25, random_state=42, stratify=y
                    )
                    
                    # Train Models
                    st.subheader("🤖 Training Models")
                    progress_bar = st.progress(0)
                    
                    # RandomForest
                    rf_model = Pipeline([
                        ('preprocessor', preprocessor),
                        ('classifier', RandomForestClassifier(
                            n_estimators=200, max_depth=10, random_state=42, class_weight='balanced'
                        ))
                    ])
                    rf_model.fit(X_train, y_train)
                    progress_bar.progress(50)
                    
                    # XGBoost
                    xgb_model = Pipeline([
                        ('preprocessor', preprocessor),
                        ('classifier', XGBClassifier(
                            n_estimators=200, max_depth=6, learning_rate=0.1, 
                            random_state=42, eval_metric='logloss'
                        ))
                    ])
                    xgb_model.fit(X_train, y_train)
                    progress_bar.progress(100)
                    
                    # Evaluate Models
                    st.subheader("📊 Model Performance")
                    
                    rf_proba = rf_model.predict_proba(X_test)[:, 1]
                    xgb_proba = xgb_model.predict_proba(X_test)[:, 1]
                    
                    rf_auc = roc_auc_score(y_test, rf_proba)
                    xgb_auc = roc_auc_score(y_test, xgb_proba)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("RandomForest AUC", f"{rf_auc:.4f}")
                    with col2:
                        st.metric("XGBoost AUC", f"{xgb_auc:.4f}")
                    
                    # Select best model
                    best_model = xgb_model if xgb_auc > rf_auc else rf_model
                    best_model_name = "XGBoost" if xgb_auc > rf_auc else "RandomForest"
                    
                    st.success(f"🏆 Best Model: {best_model_name}")
                    
                    # Generate Lead Scores
                    all_scores = best_model.predict_proba(X)[:, 1]
                    df_featured['lead_score'] = (all_scores * 100).round(1)
                    df_featured['lead_category'] = pd.cut(
                        df_featured['lead_score'],
                        bins=[0, 40, 70, 100],
                        labels=['Cold', 'Warm', 'Hot']
                    )
                    
                    # Display Results
                    st.subheader("🎯 Lead Score Distribution")
                    category_counts = df_featured['lead_category'].value_counts()
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🔥 Hot Leads", category_counts.get('Hot', 0))
                    with col2:
                        st.metric("🌤️ Warm Leads", category_counts.get('Warm', 0))
                    with col3:
                        st.metric("❄️ Cold Leads", category_counts.get('Cold', 0))
                    
                    # Top Leads
                    st.subheader("⭐ Top 20 Leads")
                    top_leads = df_featured.sort_values('lead_score', ascending=False).head(20)
                    display_cols = ['lead_id', 'name', 'preferred_area', 'budget_mid', 'lead_score', 'lead_category']
                    
                    # Check which columns exist
                    available_cols = [col for col in display_cols if col in top_leads.columns]
                    st.dataframe(top_leads[available_cols], use_container_width=True)
                    
                    # Feature Importance
                    st.subheader("🔍 Feature Importance")
                    importance_df = get_feature_importance(best_model, feature_cols, categorical_cols)
                    
                    fig, ax = plt.subplots(figsize=(10, 6))
                    top_10 = importance_df.head(10)
                    ax.barh(top_10['feature'], top_10['importance'])
                    ax.set_xlabel('Importance')
                    ax.set_title(f'Top 10 Important Features ({best_model_name})')
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Download Results
                    st.subheader("💾 Download Results")
                    
                    # Convert to Excel in memory
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_featured.to_excel(writer, sheet_name='All_Leads_Scored', index=False)
                        top_leads.to_excel(writer, sheet_name='Top_20_Leads', index=False)
                        importance_df.to_excel(writer, sheet_name='Feature_Importance', index=False)
                    
                    st.download_button(
                        label="📥 Download Complete Results",
                        data=output.getvalue(),
                        file_name="lead_scoring_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("✅ Analysis Complete!")
                    
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)
    else:
        st.info("👆 Please upload an Excel file to begin the analysis")


if __name__ == "__main__":
    main()