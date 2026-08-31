# main.py - نسخة محسنة مع تصميم متطور وتوصيات ديناميكية

import streamlit as st
import pandas as pd
from plotly import express as px
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import io
import base64
from typing import Optional, Tuple, Dict, Any
import warnings
warnings.filterwarnings('ignore')

# ========== إعداد الصفحة ==========
st.set_page_config(
    page_title="🏠 Real Estate Egypt - Smart Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== PostgreSQL Connection ==========
@st.cache_resource
def get_db_engine() -> Optional[Engine]:
    """إنشاء اتصال بقاعدة البيانات"""
    try:
        DATABASE_URL = "postgresql://postgres:200471@localhost:5432/sify"
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ فشل الاتصال بقاعدة البيانات: {str(e)}")
        return None

# ========== Custom CSS ==========
st.markdown("""
<style>
    /* ===== التنسيقات العامة ===== */
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 30px;
        font-size: 3.5rem;
        font-weight: 800;
        letter-spacing: 2px;
        animation: fadeInDown 0.8s ease-out;
    }
    
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    .custom-divider {
        height: 3px;
        background: linear-gradient(90deg, transparent, #667eea, #764ba2, #f093fb, transparent);
        margin: 30px 0;
        border-radius: 3px;
        animation: shimmer 2s infinite;
        background-size: 200% 100%;
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    /* ===== بطاقات المقاييس ===== */
    .metric-card {
        padding: 20px 25px;
        border-radius: 20px;
        color: white;
        margin: 10px 0;
        box-shadow: 0 10px 40px rgba(102,126,234,0.3);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
        cursor: pointer;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .metric-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 20px 60px rgba(102,126,234,0.4);
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        border-radius: 50%;
        transition: all 0.6s;
    }
    
    .metric-card:hover::before {
        transform: scale(1.5);
    }
    
    .metric-card .icon {
        font-size: 2rem;
        margin-bottom: 5px;
    }
    
    .metric-card h3 {
        font-size: 0.85rem;
        opacity: 0.9;
        margin-bottom: 5px;
        font-weight: 500;
        letter-spacing: 0.5px;
        position: relative;
        z-index: 1;
    }
    
    .metric-card h2 {
        font-size: 2rem;
        font-weight: 800;
        position: relative;
        z-index: 1;
    }
    
    .metric-card .trend {
        font-size: 0.8rem;
        opacity: 0.8;
        margin-top: 5px;
        position: relative;
        z-index: 1;
    }
    
    .metric-card.blue { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .metric-card.green { background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%); }
    .metric-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .metric-card.purple { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .metric-card.gold { background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%); color: #333; }
    .metric-card.pink { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }
    
    /* ===== بطاقات التوصيات ===== */
    .insight-card {
        background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%);
        border: 1px solid rgba(102,126,234,0.2);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        transition: all 0.3s;
    }
    
    .insight-card:hover {
        border-color: #667eea;
        box-shadow: 0 5px 20px rgba(102,126,234,0.15);
        transform: translateX(5px);
    }
    
    .insight-card .emoji { font-size: 1.5rem; margin-right: 10px; }
    .insight-card .title { font-weight: 700; color: #667eea; font-size: 1.1rem; }
    .insight-card .description { color: #666; margin-top: 5px; }
    
    /* ===== تبويبات ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.05);
        border-radius: 15px;
        padding: 6px;
        flex-wrap: wrap;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 12px;
        padding: 10px 22px;
        color: rgba(255,255,255,0.7);
        font-weight: 600;
        transition: all 0.3s ease;
        font-size: 0.9rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 20px rgba(102,126,234,0.3);
    }
    
    /* ===== أزرار ===== */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(102,126,234,0.4);
    }
    
    /* ===== حاوية الرؤى ===== */
    .insights-container {
        background: linear-gradient(135deg, rgba(102,126,234,0.03) 0%, rgba(118,75,162,0.03) 100%);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(102,126,234,0.1);
    }
    
    /* ===== مؤشر الأداء ===== */
    .performance-indicator {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 15px;
        border-radius: 30px;
        background: rgba(102,126,234,0.1);
        margin: 5px 0;
    }
    
    .performance-indicator .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
    }
    
    .dot.green { background: #43cea2; }
    .dot.yellow { background: #ffd93d; }
    .dot.red { background: #ff6b6b; }
    
    /* ===== متجاوب ===== */
    @media (max-width: 768px) {
        .main-title { font-size: 2rem; }
        .metric-card h2 { font-size: 1.5rem; }
        .metric-card { min-height: 90px; padding: 15px; }
    }
</style>
""", unsafe_allow_html=True)

# ========== Data Loading Functions ==========
@st.cache_data(ttl=300, show_spinner=False)
def load_stg_data():
    """تحميل البيانات من stg_scraped_data"""
    engine = get_db_engine()
    if not engine:
        return pd.DataFrame()
    
    try:
        query = """
        SELECT 
            link,
            title,
            property_type,
            location,
            state,
            source,
            price_egp as price,
            area_m2 as area,
            bedrooms,
            bathrooms,
            down_payment_egp,
            scraped_at
        FROM sify.sify_sc.stg_scraped_data
        ORDER BY scraped_at DESC
        """
        df = pd.read_sql(query, engine)
        
        if not df.empty and 'price' in df.columns and 'area' in df.columns:
            df['price_per_m'] = df.apply(
                lambda row: row['price'] / row['area'] if row['area'] and row['area'] > 0 else 0,
                axis=1
            )
        
        return df
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def get_stats():
    """الحصول على إحصائيات من قاعدة البيانات"""
    engine = get_db_engine()
    if not engine:
        return {}
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COALESCE(AVG(price_egp), 0) as avg_price,
                    COALESCE(AVG(area_m2), 0) as avg_area,
                    MAX(scraped_at) as last_update
                FROM sify.sify_sc.stg_scraped_data
            """))
            row = result.fetchone()
            
            last_update = row[3] if row and row[3] else None
            if last_update:
                if hasattr(last_update, 'strftime'):
                    last_update = last_update.strftime('%Y-%m-%d %H:%M')
                else:
                    last_update = str(last_update)
            
            return {
                'total_properties': row[0] if row else 0,
                'average_price': row[1] if row else 0,
                'average_area': row[2] if row else 0,
                'last_update': last_update
            }
    except Exception as e:
        st.error(f"❌ خطأ في جلب الإحصائيات: {str(e)}")
        return {}

# ========== ML Functions ==========
@st.cache_data(ttl=3600, show_spinner=False)
def train_price_model(df: pd.DataFrame) -> Tuple[Optional[Any], Optional[pd.DataFrame], Optional[float], Optional[float], Optional[list]]:
    """تدريب نموذج للتنبؤ بأسعار العقارات"""
    if df.empty or len(df) < 10:
        return None, None, None, None, None, None
    
    df_encoded = df.copy()
    base_features = ['area', 'bedrooms', 'bathrooms']
    
    if 'property_type' in df_encoded.columns:
        dummies = pd.get_dummies(df_encoded['property_type'], prefix='type')
        df_encoded = pd.concat([df_encoded, dummies], axis=1)
    
    if 'location' in df_encoded.columns:
        top_locations = df_encoded['location'].value_counts().head(20).index
        df_encoded['location_encoded'] = df_encoded['location'].apply(
            lambda x: x if x in top_locations else 'Other'
        )
        dummies = pd.get_dummies(df_encoded['location_encoded'], prefix='loc')
        df_encoded = pd.concat([df_encoded, dummies], axis=1)
    
    feature_cols = base_features.copy()
    type_cols = [col for col in df_encoded.columns if col.startswith('type_')]
    loc_cols = [col for col in df_encoded.columns if col.startswith('loc_')]
    feature_cols.extend(type_cols)
    feature_cols.extend(loc_cols)
    
    available_features = [f for f in feature_cols if f in df_encoded.columns and not df_encoded[f].isna().all()]
    
    if len(available_features) < 3:
        return None, None, None, None, None, None
    
    X = df_encoded[available_features].fillna(0)
    y = df_encoded['price']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    importance = pd.DataFrame({
        'feature': available_features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return model, importance, mae, r2, available_features, df_encoded

# ========== Helper Functions ==========
def export_to_csv(df):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_str = csv_buffer.getvalue()
    b64 = base64.b64encode(csv_str.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="real_estate_data.csv">📥 Download CSV</a>'
    return href

def export_to_excel(df):
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Real Estate')
    excel_buffer.seek(0)
    b64 = base64.b64encode(excel_buffer.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="real_estate_data.xlsx">📥 Download Excel</a>'
    return href

# ========== Advanced Analytics Functions ==========
def generate_dynamic_insights(df: pd.DataFrame) -> Dict:
    """توليد رؤى ديناميكية بناءً على البيانات"""
    insights = {
        'market_status': {},
        'opportunities': [],
        'risks': [],
        'recommendations': []
    }
    
    if df.empty:
        return insights
    
    # تحليل السوق
    avg_price = df['price'].mean()
    median_price = df['price'].median()
    price_std = df['price'].std()
    avg_ppm = df['price_per_m'].mean()
    
    # تحديد حالة السوق
    if price_std / avg_price < 0.3:
        market_stability = "مستقر"
        stability_emoji = "✅"
    elif price_std / avg_price < 0.5:
        market_stability = "متقلب"
        stability_emoji = "⚠️"
    else:
        market_stability = "غير مستقر"
        stability_emoji = "🔴"
    
    insights['market_status'] = {
        'stability': market_stability,
        'stability_emoji': stability_emoji,
        'avg_price': avg_price,
        'median_price': median_price,
        'avg_ppm': avg_ppm
    }
    
    # تحديد الفرص
    # 1. أفضل المناطق قيمة
    location_value = df.groupby('location').agg({
        'price_per_m': 'mean',
        'price': 'count'
    }).sort_values('price_per_m')
    
    if not location_value.empty:
        best_value_locations = location_value.head(3)
        for loc, row in best_value_locations.iterrows():
            insights['opportunities'].append({
                'type': 'best_value',
                'location': loc,
                'price_per_m': row['price_per_m'],
                'count': row['price'],
                'message': f"📍 {loc}: سعر المتر {row['price_per_m']:,.0f} EGP - قيمة ممتازة"
            })
    
    # 2. العقارات الأقل من متوسط السعر
    good_deals = df[df['price_per_m'] < avg_ppm * 0.8].head(5)
    for _, row in good_deals.iterrows():
        insights['opportunities'].append({
            'type': 'good_deal',
            'title': row.get('title', 'عقار'),
            'location': row.get('location', 'N/A'),
            'price': row['price'],
            'price_per_m': row['price_per_m'],
            'message': f"🏠 صفقة مميزة: {row.get('title', 'عقار')} - سعر المتر {row['price_per_m']:,.0f} EGP (أقل من المتوسط)"
        })
    
    # تحديد المخاطر
    # 1. المناطق ذات الأسعار المرتفعة
    high_price_locations = df.groupby('location')['price_per_m'].mean().sort_values(ascending=False).head(3)
    for loc, price in high_price_locations.items():
        insights['risks'].append({
            'type': 'high_price',
            'location': loc,
            'price_per_m': price,
            'message': f"⚠️ {loc}: سعر المتر {price:,.0f} EGP - أعلى من المتوسط بكثير"
        })
    
    # 2. العقارات المبالغ في أسعارها
    overpriced = df[df['price_per_m'] > avg_ppm * 1.5].head(5)
    for _, row in overpriced.iterrows():
        insights['risks'].append({
            'type': 'overpriced',
            'title': row.get('title', 'عقار'),
            'price_per_m': row['price_per_m'],
            'message': f"⚠️ {row.get('title', 'عقار')} - سعر المتر {row['price_per_m']:,.0f} EGP (مبالغ فيه)"
        })
    
    # توصيات عامة
    # 1. بناءً على استقرار السوق
    if market_stability == "مستقر":
        insights['recommendations'].append({
            'priority': 'high',
            'emoji': '✅',
            'title': 'سوق مستقر - وقت مناسب للشراء',
            'description': 'الأسعار مستقرة، فرصة جيدة للاستثمار طويل المدى'
        })
    elif market_stability == "متقلب":
        insights['recommendations'].append({
            'priority': 'medium',
            'emoji': '⚠️',
            'title': 'سوق متقلب - كن حذراً',
            'description': 'الأسعار غير مستقرة، انتظر فرصة أفضل أو تفاوض بقوة'
        })
    else:
        insights['recommendations'].append({
            'priority': 'high',
            'emoji': '🔴',
            'title': 'سوق غير مستقر - انتظر',
            'description': 'السوق غير مستقر حالياً، انتظر حتى تستقر الأسعار'
        })
    
    # 2. بناءً على أفضل الفرص
    if best_value_locations is not None and not best_value_locations.empty:
        best_loc = best_value_locations.index[0]
        insights['recommendations'].append({
            'priority': 'high',
            'emoji': '💎',
            'title': f'أفضل منطقة للاستثمار: {best_loc}',
            'description': f'سعر المتر {best_value_locations.iloc[0]["price_per_m"]:,.0f} EGP - عائد استثماري مرتفع'
        })
    
    return insights

def create_advanced_charts(df: pd.DataFrame) -> Dict:
    """إنشاء رسوم بيانية متقدمة"""
    charts = {}
    
    if df.empty:
        return charts
    
    # 1. Heatmap للمناطق والأسعار
    if 'location' in df.columns and 'property_type' in df.columns:
        # اختيار أفضل 10 مناطق وأكثر 5 أنواع
        top_locations = df['location'].value_counts().head(10).index
        top_types = df['property_type'].value_counts().head(5).index
        
        heatmap_data = df[df['location'].isin(top_locations) & df['property_type'].isin(top_types)]
        if not heatmap_data.empty:
            pivot_data = heatmap_data.pivot_table(
                values='price_per_m',
                index='location',
                columns='property_type',
                aggfunc='mean'
            )
            
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='Viridis',
                text=pivot_data.values.round(0),
                texttemplate='%{text:,.0f}',
                textfont={"size": 10},
                hoverongaps=False,
                colorbar_title="EGP/m²"
            ))
            fig.update_layout(
                title='🔥 توزيع الأسعار حسب الموقع والنوع',
                height=500,
                xaxis_title='نوع العقار',
                yaxis_title='الموقع'
            )
            charts['heatmap'] = fig
    
    # 2. Radar Chart للمقارنة بين المناطق
    if 'location' in df.columns:
        top_locations = df['location'].value_counts().head(5).index
        radar_data = df[df['location'].isin(top_locations)]
        
        metrics = ['price_per_m', 'area', 'bedrooms']
        available_metrics = [m for m in metrics if m in radar_data.columns]
        
        if available_metrics:
            radar_avg = radar_data.groupby('location')[available_metrics].mean()
            
            # تطبيع البيانات
            for col in available_metrics:
                if radar_avg[col].std() > 0:
                    radar_avg[col] = (radar_avg[col] - radar_avg[col].min()) / (radar_avg[col].max() - radar_avg[col].min())
            
            fig = go.Figure()
            
            colors = ['#667eea', '#f093fb', '#43cea2', '#ffd93d', '#ff6b6b']
            for i, loc in enumerate(radar_avg.index):
                fig.add_trace(go.Scatterpolar(
                    r=radar_avg.loc[loc].values,
                    theta=available_metrics,
                    fill='toself',
                    name=loc,
                    line_color=colors[i % len(colors)],
                    fillcolor=colors[i % len(colors)] + '40'
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 1.2]
                    )
                ),
                title='📊 مقارنة المناطق (مؤشرات مطبعة)',
                height=500,
                showlegend=True
            )
            charts['radar'] = fig
    
    # 3. توزيع الأسعار مع منحنيات
    if 'price' in df.columns:
        # إنشاء رسم بياني مع منحنى التوزيع
        hist_data = df['price'].dropna()
        
        fig = go.Figure()
        
        # الهيستوغرام
        fig.add_trace(go.Histogram(
            x=hist_data,
            nbinsx=30,
            name='توزيع الأسعار',
            marker_color='#667eea',
            opacity=0.7,
            hovertemplate='السعر: %{x:,.0f} EGP<br>العدد: %{y}<extra></extra>'
        ))
        
        # منحنى الكثافة (KDE)
        from scipy import stats
        kde = stats.gaussian_kde(hist_data)
        x_range = np.linspace(hist_data.min(), hist_data.max(), 100)
        density = kde(x_range) * len(hist_data) * (hist_data.max() - hist_data.min()) / 30
        
        fig.add_trace(go.Scatter(
            x=x_range,
            y=density,
            mode='lines',
            name='منحنى التوزيع',
            line=dict(color='#764ba2', width=3),
            hovertemplate='السعر: %{x:,.0f} EGP<br>الكثافة: %{y:.2f}<extra></extra>'
        ))
        
        # خطوط المتوسط والوسيط
        mean_price = hist_data.mean()
        median_price = hist_data.median()
        
        fig.add_vline(x=mean_price, line_dash="dash", line_color="#43cea2", 
                      annotation_text=f"المتوسط: {mean_price:,.0f}", annotation_position="top")
        fig.add_vline(x=median_price, line_dash="dash", line_color="#ffd93d", 
                      annotation_text=f"الوسيط: {median_price:,.0f}", annotation_position="bottom")
        
        fig.update_layout(
            title='💰 توزيع الأسعار مع منحنى الكثافة',
            height=450,
            xaxis_title='السعر (EGP)',
            yaxis_title='العدد',
            bargap=0.05,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        charts['price_distribution'] = fig
    
    # 4. مخطط فقاعي 3D (Scatter 3D)
    if all(col in df.columns for col in ['price', 'area', 'bedrooms']):
        fig = go.Figure(data=go.Scatter3d(
            x=df['area'],
            y=df['bedrooms'],
            z=df['price'],
            mode='markers',
            marker=dict(
                size=8,
                color=df['price_per_m'] if 'price_per_m' in df.columns else df['price'],
                colorscale='Viridis',
                showscale=True,
                colorbar_title="السعر/m²",
                opacity=0.8
            ),
            text=df['location'] if 'location' in df.columns else None,
            hovertemplate='<b>المساحة:</b> %{x:.0f} m²<br><b>الغرف:</b> %{y}<br><b>السعر:</b> %{z:,.0f} EGP<br>%{text}<extra></extra>'
        ))
        
        fig.update_layout(
            title='🏠 العلاقة بين المساحة والغرف والسعر',
            height=550,
            scene=dict(
                xaxis_title='المساحة (m²)',
                yaxis_title='عدد الغرف',
                zaxis_title='السعر (EGP)',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            )
        )
        charts['scatter_3d'] = fig
    
    return charts

# ========== Sidebar ==========
with st.sidebar:
    st.image("https://img.icons8.com/color/96/real-estate.png", width=80)
    st.markdown("## 🔍 Filters")
    
    with st.spinner("جاري تحميل البيانات..."):
        df_full = load_stg_data()
    
    selected_type = "All"
    selected_location = "All"
    selected_bedrooms = "All"
    price_range = (0, 1000000)
    area_range = (0, 1000)
    
    if df_full.empty:
        st.warning("⚠️ لا توجد بيانات في قاعدة البيانات")
    else:
        property_types = ["All"] + sorted(df_full['property_type'].dropna().unique().tolist())
        selected_type = st.selectbox("🏘️ Property Type", property_types)
        
        locations = ["All"] + sorted(df_full['location'].dropna().unique().tolist())
        selected_location = st.selectbox("📍 Location", locations)
        
        if 'bedrooms' in df_full.columns:
            bed_options = ["All"] + sorted(df_full['bedrooms'].dropna().unique().tolist())
            selected_bedrooms = st.selectbox("🛏️ Bedrooms", bed_options)
        
        if 'price' in df_full.columns and not df_full['price'].dropna().empty:
            price_min = int(df_full['price'].min())
            price_max = int(df_full['price'].max())
            price_range = st.slider(
                "💰 Price Range (EGP)",
                price_min, price_max,
                (price_min, price_max),
                format="%d"
            )
        
        if 'area' in df_full.columns and not df_full['area'].dropna().empty:
            area_min = int(df_full['area'].min())
            area_max = int(df_full['area'].max())
            area_range = st.slider(
                "📐 Area Range (m²)",
                area_min, area_max,
                (area_min, area_max)
            )
    
    st.markdown("---")
    st.markdown("## 📊 Quick Stats")
    stats = get_stats()
    if stats:
        st.metric("🏠 Total Properties", f"{stats.get('total_properties', 0):,}")
        st.metric("💰 Avg Price", f"{stats.get('average_price', 0):,.0f} EGP")
        st.metric("📐 Avg Area", f"{stats.get('average_area', 0):.0f} m²")
        if stats.get('last_update'):
            st.caption(f"🔄 Last Update: {stats['last_update']}")
    
    st.markdown("---")
    st.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ========== Apply Filters ==========
def apply_filters(df):
    if df.empty:
        return df
    
    filtered = df.copy()
    
    if selected_type != "All" and 'property_type' in filtered.columns:
        filtered = filtered[filtered['property_type'] == selected_type]
    
    if selected_location != "All" and 'location' in filtered.columns:
        filtered = filtered[filtered['location'] == selected_location]
    
    if selected_bedrooms != "All" and 'bedrooms' in filtered.columns:
        filtered = filtered[filtered['bedrooms'] == selected_bedrooms]
    
    if 'price' in filtered.columns:
        filtered = filtered[(filtered['price'] >= price_range[0]) & (filtered['price'] <= price_range[1])]
    
    if 'area' in filtered.columns:
        filtered = filtered[(filtered['area'] >= area_range[0]) & (filtered['area'] <= area_range[1])]
    
    return filtered

# ========== Main Tabs ==========
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Market Insights", "🤖 ML Predictions", "💰 Finance Calculator"])

# ============================================================
# ========== TAB 1: DASHBOARD ==========
# ============================================================
with tab1:
    if df_full.empty:
        st.info("📭 لا توجد بيانات في قاعدة البيانات")
    else:
        df = apply_filters(df_full)
        
        if df.empty:
            st.info("لا توجد عقارات تطابق الفلاتر المختارة")
        else:
            # ===== العنوان الديناميكي =====
            col_title, col_date = st.columns([3, 1])
            with col_title:
                total_props = len(df)
                if total_props > 1000:
                    title_emoji = "🏙️"
                elif total_props > 100:
                    title_emoji = "🏘️"
                else:
                    title_emoji = "🏠"
                
                st.markdown(f"""
                <h2 style="margin-bottom: 0; color: #667eea;">
                    {title_emoji} نظرة عامة على السوق
                    <span style="font-size: 1rem; color: #666; font-weight: 400;">
                        - {total_props:,} عقار
                    </span>
                </h2>
                """, unsafe_allow_html=True)
            
            with col_date:
                st.caption(f"🔄 آخر تحديث: {datetime.now().strftime('%I:%M %p')}")
            
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            
            # ===== بطاقات المقاييس المحسنة =====
            st.markdown("### 📊 المقاييس الرئيسية")
            
            # حساب الاتجاهات (مقارنة بالمتوسط)
            avg_price = df['price'].mean()
            avg_area = df['area'].mean()
            avg_ppm = df['price_per_m'].mean()
            total_value = df['price'].sum()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card blue">
                    <div class="icon">🏠</div>
                    <h3>إجمالي العقارات</h3>
                    <h2>{len(df):,}</h2>
                    <div class="trend">📊 {len(df[df['price'] > avg_price])} عقار فوق المتوسط</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card green">
                    <div class="icon">💰</div>
                    <h3>متوسط السعر</h3>
                    <h2>{avg_price:,.0f} EGP</h2>
                    <div class="trend">📈 السعر الأعلى: {df['price'].max():,.0f} EGP</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card orange">
                    <div class="icon">📐</div>
                    <h3>متوسط المساحة</h3>
                    <h2>{avg_area:.0f} m²</h2>
                    <div class="trend">📏 الأكبر: {df['area'].max():.0f} m²</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card purple">
                    <div class="icon">📏</div>
                    <h3>متوسط سعر المتر</h3>
                    <h2>{avg_ppm:,.0f} EGP</h2>
                    <div class="trend">💎 الأقل: {df['price_per_m'].min():,.0f} EGP</div>
                </div>
                """, unsafe_allow_html=True)
            
            # ===== قسم الرؤى والتوصيات الديناميكية =====
            st.markdown("### 💡 رؤى السوق وتوصيات ذكية")
            
            insights = generate_dynamic_insights(df)
            
            # حالة السوق
            if insights['market_status']:
                status = insights['market_status']
                col_status, col_avg = st.columns(2)
                
                with col_status:
                    st.markdown(f"""
                    <div class="insight-card" style="border-left: 4px solid #43cea2;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 2rem;">{status['stability_emoji']}</span>
                            <div>
                                <div class="title">حالة السوق: {status['stability']}</div>
                                <div class="description">
                                    متوسط السعر: {status['avg_price']:,.0f} EGP | 
                                    الوسيط: {status['median_price']:,.0f} EGP
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_avg:
                    st.markdown(f"""
                    <div class="insight-card" style="border-left: 4px solid #667eea;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 2rem;">📊</span>
                            <div>
                                <div class="title">متوسط سعر المتر</div>
                                <div class="description">
                                    {status['avg_ppm']:,.0f} EGP/m²
                                    <br>
                                    <span style="color: #43cea2;">
                                        {int((status['avg_ppm'] / df['price_per_m'].min()) * 100)}% أعلى من أقل سعر
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # الفرص والمخاطر
            col_opp, col_risk = st.columns(2)
            
            with col_opp:
                st.markdown("#### ✅ فرص استثمارية")
                if insights['opportunities']:
                    for opp in insights['opportunities'][:3]:
                        st.markdown(f"""
                        <div class="insight-card" style="border-left: 4px solid #43cea2;">
                            <div style="display: flex; align-items: flex-start; gap: 10px;">
                                <span style="font-size: 1.5rem;">💎</span>
                                <div>
                                    <div class="description">{opp['message']}</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("لا توجد فرص مميزة حالياً")
            
            with col_risk:
                st.markdown("#### ⚠️ مخاطر محتملة")
                if insights['risks']:
                    for risk in insights['risks'][:3]:
                        st.markdown(f"""
                        <div class="insight-card" style="border-left: 4px solid #ff6b6b;">
                            <div style="display: flex; align-items: flex-start; gap: 10px;">
                                <span style="font-size: 1.5rem;">⚠️</span>
                                <div>
                                    <div class="description">{risk['message']}</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("✅ لا توجد مخاطر واضحة حالياً")
            
            # ===== التوصيات =====
            st.markdown("#### 🎯 توصيات ذكية")
            if insights['recommendations']:
                cols = st.columns(min(len(insights['recommendations']), 3))
                for i, rec in enumerate(insights['recommendations'][:3]):
                    with cols[i]:
                        st.markdown(f"""
                        <div class="insight-card" style="border-left: 4px solid #667eea; text-align: center;">
                            <div style="font-size: 2.5rem;">{rec['emoji']}</div>
                            <div class="title" style="font-size: 0.95rem;">{rec['title']}</div>
                            <div class="description" style="font-size: 0.85rem;">{rec['description']}</div>
                            <div style="margin-top: 8px;">
                                <span style="background: #667eea20; padding: 3px 12px; border-radius: 20px; font-size: 0.75rem; color: #667eea;">
                                    أولوية {rec['priority']}
                                </span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            
            # ===== الرسوم البيانية المتقدمة =====
            st.markdown("### 📈 تحليلات متقدمة")
            
            advanced_charts = create_advanced_charts(df)
            
            # توزيع الأسعار مع منحنى الكثافة
            if 'price_distribution' in advanced_charts:
                st.plotly_chart(advanced_charts['price_distribution'], width='stretch', key="price_dist")
            
            # Heatmap
            col1, col2 = st.columns(2)
            if 'heatmap' in advanced_charts:
                with col1:
                    st.plotly_chart(advanced_charts['heatmap'], width='stretch', key="heatmap")
            
            # Radar
            if 'radar' in advanced_charts:
                with col2:
                    st.plotly_chart(advanced_charts['radar'], width='stretch', key="radar")
            
            # 3D Scatter
            if 'scatter_3d' in advanced_charts:
                st.plotly_chart(advanced_charts['scatter_3d'], width='stretch', key="scatter_3d")
            
            # ===== جدول البيانات =====
            st.markdown("### 📋 قائمة العقارات")
            
            display_cols = ['title', 'property_type', 'price', 'location', 'bedrooms', 'area', 'price_per_m']
            available_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(
                df[available_cols],
                width='stretch',
                hide_index=True,
                column_config={
                    'price': st.column_config.NumberColumn('السعر', format='%d EGP'),
                    'area': st.column_config.NumberColumn('المساحة', format='%.0f m²'),
                    'price_per_m': st.column_config.NumberColumn('سعر المتر', format='%d EGP'),
                }
            )
            
            # ===== تصدير =====
            st.markdown("### 📥 تصدير")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(export_to_csv(df), unsafe_allow_html=True)
            with col2:
                st.markdown(export_to_excel(df), unsafe_allow_html=True)

# ============================================================
# ========== TAB 2: MARKET INSIGHTS ==========
# ============================================================
with tab2:
    st.markdown("## 📈 تحليل السوق المتقدم")
    
    if not df_full.empty:
        df = apply_filters(df_full)
        
        if not df.empty:
            # ===== إحصائيات متقدمة =====
            st.markdown("### 📊 الإحصائيات المتقدمة")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "📊 الانحراف المعياري",
                    f"{df['price'].std():,.0f}" if 'price' in df.columns else "N/A",
                    help="مدى تشتت الأسعار"
                )
            
            with col2:
                st.metric(
                    "📈 نطاق الأسعار",
                    f"{df['price'].max() - df['price'].min():,.0f}" if 'price' in df.columns else "N/A",
                    help="الفرق بين أعلى وأقل سعر"
                )
            
            with col3:
                st.metric(
                    "🎯 السعر الوسيط",
                    f"{df['price'].median():,.0f}" if 'price' in df.columns else "N/A",
                    help="القيمة الوسطى للأسعار"
                )
            
            with col4:
                st.metric(
                    "📐 المساحة الوسيطة",
                    f"{df['area'].median():.0f} m²" if 'area' in df.columns else "N/A",
                    help="القيمة الوسطى للمساحات"
                )
            
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            
            # ===== تحليل المناطق =====
            st.markdown("### 🗺️ تحليل المناطق")
            
            if 'location' in df.columns and 'price_per_m' in df.columns:
                # أفضل 10 مناطق من حيث السعر
                loc_stats = df.groupby('location').agg({
                    'price': ['mean', 'median', 'count', 'std'],
                    'price_per_m': 'mean'
                }).round(0)
                
                loc_stats.columns = ['متوسط السعر', 'الوسيط', 'العدد', 'الانحراف', 'سعر المتر']
                loc_stats = loc_stats.sort_values('سعر المتر', ascending=False)
                
                st.dataframe(
                    loc_stats.head(15),
                    width='stretch',
                    column_config={
                        'متوسط السعر': st.column_config.NumberColumn('متوسط السعر', format='%d EGP'),
                        'الوسيط': st.column_config.NumberColumn('الوسيط', format='%d EGP'),
                        'العدد': 'العدد',
                        'الانحراف': st.column_config.NumberColumn('الانحراف', format='%d'),
                        'سعر المتر': st.column_config.NumberColumn('سعر المتر', format='%d EGP')
                    }
                )
            
            # ===== تحليل الارتباط =====
            st.markdown("### 🔗 مصفوفة الارتباط")
            
            numeric_cols = ['price', 'area', 'bedrooms', 'bathrooms', 'price_per_m']
            numeric_cols = [c for c in numeric_cols if c in df.columns]
            
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu_r',
                    text=corr_matrix.values.round(2),
                    texttemplate='%{text}',
                    textfont={"size": 12, "color": "white"},
                    hoverongaps=False,
                    zmin=-1,
                    zmax=1
                ))
                fig.update_layout(
                    title='📊 العلاقة بين المتغيرات',
                    height=500,
                    xaxis_title='المتغيرات',
                    yaxis_title='المتغيرات'
                )
                st.plotly_chart(fig, width='stretch', key="correlation")
            
            # ===== تحليل القيم الشاذة =====
            st.markdown("### 🔍 القيم الشاذة")
            
            if 'price' in df.columns and 'area' in df.columns:
                # حساب Z-score
                from scipy import stats
                df['z_score'] = stats.zscore(df['price'])
                outliers = df[abs(df['z_score']) > 2]
                
                st.metric(
                    "عدد القيم الشاذة",
                    f"{len(outliers)} من {len(df)} عقار",
                    help="العقارات ذات الأسعار غير النمطية"
                )
                
                if not outliers.empty:
                    with st.expander("📋 عرض العقارات الشاذة"):
                        st.dataframe(
                            outliers[['title', 'location', 'price', 'area', 'price_per_m']],
                            width='stretch',
                            column_config={
                                'price': st.column_config.NumberColumn('السعر', format='%d EGP'),
                                'area': st.column_config.NumberColumn('المساحة', format='%.0f m²'),
                                'price_per_m': st.column_config.NumberColumn('سعر المتر', format='%d EGP')
                            }
                        )
            
            # ===== تحليل العائد الاستثماري =====
            st.markdown("### 📈 تحليل العائد الاستثماري")
            
            if 'price' in df.columns:
                avg_price = df['price'].mean()
                avg_ppm = df['price_per_m'].mean()
                
                # حساب العائد المتوقع
                expected_rent = avg_price * 0.006  # 0.6% من السعر شهرياً
                annual_return = expected_rent * 12
                roi = (annual_return / avg_price) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "💰 الإيجار المتوقع شهرياً",
                        f"{expected_rent:,.0f} EGP",
                        help="متوسط الإيجار المتوقع (0.6% من قيمة العقار)"
                    )
                with col2:
                    st.metric(
                        "📈 العائد السنوي المتوقع",
                        f"{annual_return:,.0f} EGP",
                        help="العائد السنوي من الإيجار"
                    )
                with col3:
                    st.metric(
                        "📊 نسبة العائد الاستثماري (ROI)",
                        f"{roi:.2f}%",
                        help="نسبة العائد على الاستثمار"
                    )
                
                # أفضل المناطق للاستثمار
                if 'location' in df.columns:
                    roi_by_location = df.groupby('location').apply(
                        lambda x: ((x['price'].mean() * 0.006 * 12) / x['price'].mean()) * 100
                    ).sort_values(ascending=False)
                    
                    st.markdown("#### 🏆 أفضل 5 مناطق للاستثمار")
                    for loc, roi_val in roi_by_location.head(5).items():
                        st.markdown(f"""
                        <div class="performance-indicator">
                            <span class="dot green"></span>
                            <span style="font-weight: 600;">{loc}</span>
                            <span style="margin-left: auto; color: #43cea2; font-weight: 700;">ROI: {roi_val:.2f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
        
        else:
            st.info("لا توجد بيانات لعرضها")
    else:
        st.info("📭 لا توجد بيانات في قاعدة البيانات")

# ============================================================
# ========== TAB 3: ML PREDICTIONS ==========
# ============================================================
with tab3:
    st.markdown("## 🤖 التنبؤ الذكي بالأسعار")
    
    if not df_full.empty:
        df = apply_filters(df_full)
        
        if not df.empty and len(df) >= 10:
            with st.spinner("🧠 جاري تدريب نموذج الذكاء الاصطناعي..."):
                model, importance, mae, r2, feature_cols, df_encoded = train_price_model(df)
            
            if model is not None and importance is not None:
                # ===== أداء النموذج =====
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card blue" style="min-height: 80px;">
                        <h3 style="font-size: 0.8rem;">🎯 دقة النموذج (R²)</h3>
                        <h2 style="font-size: 1.8rem;">{r2:.2%}</h2>
                        <div class="trend">{'ممتاز' if r2 > 0.8 else 'جيد' if r2 > 0.6 else 'مقبول'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card green" style="min-height: 80px;">
                        <h3 style="font-size: 0.8rem;">📊 متوسط الخطأ المطلق</h3>
                        <h2 style="font-size: 1.8rem;">{mae:,.0f} EGP</h2>
                        <div class="trend">نسبة الخطأ: {(mae/df['price'].mean()*100):.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                
                # ===== أهمية المتغيرات =====
                st.markdown("### 📊 أهمية المتغيرات")
                
                fig = px.bar(
                    importance.head(10),
                    x='importance',
                    y='feature',
                    orientation='h',
                    title='🏆 أهم العوامل المؤثرة على السعر',
                    color='importance',
                    color_continuous_scale='Viridis',
                    labels={'importance': 'الأهمية', 'feature': 'المتغير'}
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, width='stretch', key="feature_importance")
                
                # ===== أداة التنبؤ =====
                st.markdown("### 🔮 تنبؤ بسعر العقار")
                st.markdown("أدخل مواصفات العقار للحصول على سعر متوقع")
                
                property_types = df['property_type'].dropna().unique().tolist() if 'property_type' in df.columns else ['Apartment', 'Villa']
                locations = df['location'].dropna().unique().tolist() if 'location' in df.columns else ['Cairo', 'Alexandria']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    pred_area = st.number_input("📐 المساحة (m²)", min_value=10, max_value=1000, value=120)
                with col2:
                    pred_bedrooms = st.selectbox("🛏️ عدد الغرف", [1, 2, 3, 4, 5, 6], index=2)
                with col3:
                    pred_bathrooms = st.selectbox("🛁 عدد الحمامات", [1, 2, 3, 4, 5], index=1)
                
                col4, col5 = st.columns(2)
                with col4:
                    pred_property_type = st.selectbox("🏘️ نوع العقار", property_types, index=0)
                with col5:
                    pred_location = st.selectbox("📍 الموقع", locations, index=0)
                
                if st.button("💰 تنبؤ بالسعر", type="primary"):
                    try:
                        # بناء بيانات التنبؤ
                        pred_data = {
                            'area': pred_area,
                            'bedrooms': pred_bedrooms,
                            'bathrooms': pred_bathrooms,
                            'property_type': pred_property_type,
                            'location': pred_location
                        }
                        pred_df = pd.DataFrame([pred_data])
                        
                        # ترميز البيانات
                        pred_encoded = pred_df.copy()
                        
                        for col in feature_cols:
                            if col.startswith('type_'):
                                type_val = col.replace('type_', '')
                                pred_encoded[col] = 1 if pred_property_type == type_val else 0
                            elif col.startswith('loc_'):
                                loc_val = col.replace('loc_', '')
                                if pred_location == loc_val or (loc_val == 'Other' and pred_location not in locations):
                                    pred_encoded[col] = 1
                                else:
                                    pred_encoded[col] = 0
                            elif col not in pred_encoded.columns:
                                pred_encoded[col] = 0
                        
                        pred_encoded = pred_encoded[feature_cols].fillna(0)
                        
                        # التنبؤ
                        prediction = model.predict(pred_encoded)[0]
                        
                        # عرض النتيجة
                        st.markdown(f"""
                        <div class="insight-card" style="border-left: 4px solid #43cea2; text-align: center; padding: 30px;">
                            <div style="font-size: 1rem; color: #666;">السعر المتوقع</div>
                            <div style="font-size: 3rem; font-weight: 800; color: #667eea; margin: 10px 0;">
                                {prediction:,.0f} EGP
                            </div>
                            <div style="display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; margin-top: 15px;">
                                <span>📐 {pred_area} m²</span>
                                <span>🛏️ {pred_bedrooms} غرف</span>
                                <span>🛁 {pred_bathrooms} حمامات</span>
                                <span>🏘️ {pred_property_type}</span>
                                <span>📍 {pred_location}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # مقارنة مع متوسط السوق
                        avg_price = df['price'].mean()
                        diff_percent = ((prediction - avg_price) / avg_price) * 100
                        
                        if diff_percent > 20:
                            st.info(f"⚠️ السعر المتوقع أعلى من متوسط السوق بنسبة {diff_percent:.1f}%")
                        elif diff_percent < -20:
                            st.success(f"✅ السعر المتوقع أقل من متوسط السوق بنسبة {abs(diff_percent):.1f}% - فرصة استثمارية!")
                        else:
                            st.info(f"ℹ️ السعر المتوقع قريب من متوسط السوق (فرق {abs(diff_percent):.1f}%)")
                    
                    except Exception as e:
                        st.error(f"❌ خطأ في التنبؤ: {str(e)}")
                
                # ===== مقارنة الأسعار الفعلية والمتوقعة =====
                st.markdown("### 📈 مقارنة الأسعار الفعلية والمتوقعة")
                
                # استخدام العينة للعرض
                sample_size = min(100, len(df))
                sample_df = df.sample(sample_size).copy()
                sample_encoded = df_encoded.loc[sample_df.index, feature_cols].fillna(0)
                sample_pred = model.predict(sample_encoded)
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=sample_df['price'],
                    y=sample_pred,
                    mode='markers',
                    marker=dict(
                        color='#667eea',
                        size=10,
                        opacity=0.7,
                        line=dict(color='#764ba2', width=1)
                    ),
                    name='التنبؤات',
                    hovertemplate='فعلي: %{x:,.0f} EGP<br>متوقع: %{y:,.0f} EGP<br><extra></extra>'
                ))
                
                # خط الكمال
                max_val = max(sample_df['price'].max(), sample_pred.max())
                min_val = min(sample_df['price'].min(), sample_pred.min())
                fig.add_trace(go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    line=dict(color='#43cea2', dash='dash', width=2),
                    name='تنبؤ مثالي'
                ))
                
                fig.update_layout(
                    title='🎯 أداء النموذج: الفعلي مقابل المتوقع',
                    xaxis_title='السعر الفعلي (EGP)',
                    yaxis_title='السعر المتوقع (EGP)',
                    height=500,
                    showlegend=True,
                    hovermode='closest'
                )
                st.plotly_chart(fig, width='stretch', key="actual_vs_pred")
                
                # ===== توصيات ذكية =====
                st.markdown("### 💡 توصيات ذكية بناءً على التحليل")
                
                # أفضل العقارات قيمة
                if 'price_per_m' in df.columns:
                    avg_ppm = df['price_per_m'].mean()
                    good_deals = df[df['price_per_m'] < avg_ppm * 0.8].head(5)
                    
                    if not good_deals.empty:
                        st.markdown("#### 🏆 أفضل الصفقات (أقل من متوسط السوق)")
                        for _, row in good_deals.iterrows():
                            st.markdown(f"""
                            <div class="insight-card" style="border-left: 4px solid #43cea2;">
                                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                                    <span><b>{row.get('title', 'عقار')}</b> | 📍 {row.get('location', 'N/A')}</span>
                                    <span style="color: #43cea2; font-weight: 700;">
                                        {row['price_per_m']:,.0f} EGP/m²
                                    </span>
                                    <span style="background: #43cea220; padding: 2px 12px; border-radius: 20px; font-size: 0.8rem; color: #43cea2;">
                                        {((avg_ppm - row['price_per_m']) / avg_ppm * 100):.0f}% أقل من المتوسط
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("لا توجد صفقات مميزة حالياً")
                
                # نصائح للمستثمرين
                st.markdown("#### 📌 نصائح للمستثمرين")
                tips = [
                    "💎 استثمر في المناطق ذات النمو السكاني المرتفع",
                    "📈 تابع اتجاهات السوق بشكل دوري",
                    "🤝 تفاوض على السعر خاصة في السوق المتقلب",
                    "📋 تأكد من صحة الأوراق القانونية قبل الشراء",
                    "📍 اختر مواقع قريبة من الخدمات الأساسية"
                ]
                
                for tip in tips:
                    st.markdown(f"""
                    <div class="performance-indicator">
                        <span class="dot green"></span>
                        <span>{tip}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ البيانات غير كافية لتدريب النموذج. يحتاج على الأقل 10 عقارات.")
        else:
            st.info("لا توجد بيانات كافية للتحليل الذكي (تحتاج على الأقل 10 عقارات)")
    else:
        st.info("📭 لا توجد بيانات في قاعدة البيانات")


# ============================================================
# ========== TAB 4: FINANCE CALCULATOR ==========
# ============================================================

# ===== دوال مساعدة للحاسبة =====
def calculate_monthly_payment(loan_amount: float, annual_rate: float, years: int) -> float:
    """حساب القسط الشهري للقرض"""
    if loan_amount <= 0:
        return 0
    monthly_rate = annual_rate / 12
    n_months = years * 12
    if monthly_rate == 0:
        return loan_amount / n_months
    return loan_amount * monthly_rate * (1 + monthly_rate)**n_months / ((1 + monthly_rate)**n_months - 1)

def generate_savings_plan(monthly_savings: float, target_amount: float, max_months: int = 120) -> pd.DataFrame:
    """إنشاء خطة ادخار مفصلة"""
    if monthly_savings <= 0 or target_amount <= 0:
        return pd.DataFrame()
    
    months_to_target = min(int(np.ceil(target_amount / monthly_savings)), max_months)
    plan_data = []
    
    for month in range(1, months_to_target + 1):
        saved = monthly_savings * month
        progress = min((saved / target_amount) * 100, 100)
        
        plan_data.append({
            'الشهر': month,
            'المدخرات المتراكمة': saved,
            'نسبة الإنجاز': progress,
            'المتبقي': max(target_amount - saved, 0)
        })
    
    return pd.DataFrame(plan_data)


# ===== محتوى التبويب الرابع =====
with tab4:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea, #764ba2, #f093fb); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0;">
            💰 حاسبة التمويل العقاري الذكية
        </h1>
        <p style="color: #888; font-size: 1.1rem;">خطط لشراء منزل أحلامك أو استثمارك العقاري بذكاء واحترافية</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    if df_full.empty:
        st.info("📭 لا توجد بيانات في قاعدة البيانات لعرض التوصيات")
    else:
        df = apply_filters(df_full)
        
        if df.empty:
            st.info("لا توجد عقارات تطابق الفلاتر المختارة")
        else:
            # ============================================================
            # ========== قسم إدخال البيانات المالية ==========
            # ============================================================
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea08, #764ba208); 
                        border-radius: 20px; padding: 25px; border: 1px solid #667eea20;">
                <h3 style="color: #667eea;">📝 أدخل بياناتك المالية</h3>
                <p style="color: #888; font-size: 0.9rem;">املأ البيانات التالية للحصول على تحليل مالي شامل وتوصيات ذكية</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ===== المدخلات المالية =====
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div style="background: #667eea10; border-radius: 15px; padding: 20px;">
                    <h4 style="color: #667eea; margin-top: 0;">💰 الدخل والمصروفات</h4>
                """, unsafe_allow_html=True)
                
                monthly_income = st.number_input(
                    "💼 الدخل الشهري (EGP)",
                    min_value=1000,
                    max_value=1000000,
                    value=15000,
                    step=1000,
                    help="أدخل صافي دخلك الشهري بعد الخصومات"
                )
                
                monthly_expenses = st.number_input(
                    "💸 المصاريف الشهرية (EGP)",
                    min_value=0,
                    max_value=1000000,
                    value=8000,
                    step=500,
                    help="أدخل مجموع مصاريفك الشهرية (إيجار، مواصلات، طعام، فواتير، إلخ)"
                )
                
                # حساب نسبة الادخار تلقائياً
                savings_ratio = ((monthly_income - monthly_expenses) / monthly_income * 100) if monthly_income > 0 else 0
                
                st.markdown(f"""
                <div style="background: {'#43cea220' if savings_ratio > 30 else '#ffd93d20' if savings_ratio > 20 else '#ff6b6b20'}; 
                            padding: 10px 15px; border-radius: 10px; margin-top: 5px;">
                    <span style="font-weight: 600;">نسبة الادخار:</span>
                    <span style="color: {'#43cea2' if savings_ratio > 30 else '#ffd93d' if savings_ratio > 20 else '#ff6b6b'};
                                font-weight: 700; font-size: 1.1rem;">
                        {savings_ratio:.1f}%
                    </span>
                    <span style="font-size: 0.8rem; color: #888;">
                        ({'ممتاز' if savings_ratio > 30 else 'جيد' if savings_ratio > 20 else 'بحاجة للتحسين'})
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div style="background: #764ba210; border-radius: 15px; padding: 20px;">
                    <h4 style="color: #764ba2; margin-top: 0;">🎯 الهدف والتمويل</h4>
                """, unsafe_allow_html=True)
                
                goal_type = st.selectbox(
                    "🎯 نوع الهدف",
                    ["شراء (سكن)", "استثمار", "شراء وإيجار"],
                    help="اختر هدفك الأساسي من الشراء"
                )
                
                target_price = st.number_input(
                    "🏠 السعر المستهدف (اختياري)",
                    min_value=0,
                    max_value=100000000,
                    value=0,
                    step=50000,
                    help="أدخل سعر العقار الذي تفكر فيه (اترك 0 للحصول على توصيات تلقائية)"
                )
                
                # خيارات التمويل المتقدمة
                with st.expander("⚙️ خيارات التمويل المتقدمة"):
                    down_payment_percent = st.slider(
                        "نسبة الدفعة الأولى",
                        min_value=5,
                        max_value=50,
                        value=20,
                        step=5,
                        help="نسبة المبلغ الذي ستقدمه كدفعة أولى"
                    ) / 100
                    
                    interest_rate = st.slider(
                        "نسبة الفائدة السنوية",
                        min_value=5.0,
                        max_value=25.0,
                        value=12.0,
                        step=0.5,
                        help="نسبة الفائدة المتوقعة من البنك"
                    ) / 100
                    
                    loan_term = st.slider(
                        "مدة القرض (بالسنوات)",
                        min_value=5,
                        max_value=30,
                        value=20,
                        step=5,
                        help="مدة سداد القرض"
                    )
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # ===== زر الحساب =====
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                calculate_btn = st.button(
                    "🚀 احسب قدرتي المالية واحصل على توصيات",
                    type="primary",
                    use_container_width=True
                )
            
            # ============================================================
            # ========== حساب وتحليل البيانات ==========
            # ============================================================
            
            if calculate_btn:
                with st.spinner("🧮 جاري تحليل البيانات المالية وتوليد التوصيات..."):
                    
                    # ===== حساب المتغيرات المالية =====
                    monthly_savings = monthly_income - monthly_expenses
                    annual_savings = monthly_savings * 12
                    
                    # حساب القدرة الشرائية
                    max_monthly_payment = monthly_income * 0.40  # 40% كحد أقصى للقسط
                    
                    # حساب القرض الأقصى
                    monthly_rate = interest_rate / 12
                    n_months = loan_term * 12
                    
                    if monthly_rate > 0:
                        max_loan = max_monthly_payment * ((1 + monthly_rate)**n_months - 1) / (monthly_rate * (1 + monthly_rate)**n_months)
                    else:
                        max_loan = max_monthly_payment * n_months
                    
                    # حساب الحد الأقصى لسعر العقار
                    max_property_price = max_loan / (1 - down_payment_percent)
                    required_down_payment = max_property_price * down_payment_percent
                    
                    # حساب الوقت اللازم للادخار
                    if monthly_savings > 0:
                        months_to_save = required_down_payment / monthly_savings
                        years_to_save = months_to_save / 12
                    else:
                        months_to_save = float('inf')
                        years_to_save = float('inf')
                    
                    # ===== تحليل الهدف المحدد =====
                    if target_price > 0:
                        target_down_payment = target_price * down_payment_percent
                        target_loan = target_price * (1 - down_payment_percent)
                        target_monthly_payment = calculate_monthly_payment(target_loan, interest_rate, loan_term)
                        
                        is_affordable = target_monthly_payment <= max_monthly_payment
                        
                        if monthly_savings > 0:
                            months_to_target = target_down_payment / monthly_savings
                            years_to_target = months_to_target / 12
                        else:
                            months_to_target = float('inf')
                            years_to_target = float('inf')
                    else:
                        target_down_payment = None
                        target_loan = None
                        target_monthly_payment = None
                        is_affordable = None
                        months_to_target = None
                        years_to_target = None
                    
                    # ===== عرض النتائج =====
                    
                    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                    
                    # ====== عنوان النتائج ======
                    st.markdown("""
                    <div style="text-align: center; padding: 10px 0;">
                        <h2 style="color: #667eea;">📊 نتائج التحليل المالي</h2>
                        <p style="color: #888;">بناءً على بياناتك المالية، إليك تحليل شامل لقدرتك الشرائية</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ====== البطاقات الرئيسية ======
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.markdown(f"""
                        <div class="metric-card gold" style="min-height: 110px;">
                            <div class="icon">💰</div>
                            <h3 style="font-size: 0.75rem;">المدخرات الشهرية</h3>
                            <h2 style="font-size: 1.8rem;">{monthly_savings:,.0f} EGP</h2>
                            <div class="trend" style="font-size: 0.7rem;">
                                {annual_savings:,.0f} EGP سنوياً
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div class="metric-card blue" style="min-height: 110px;">
                            <div class="icon">🏠</div>
                            <h3 style="font-size: 0.75rem;">الحد الأقصى للسعر</h3>
                            <h2 style="font-size: 1.8rem;">{max_property_price:,.0f} EGP</h2>
                            <div class="trend" style="font-size: 0.7rem;">
                                يمكنك شراء عقار حتى هذا المبلغ
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown(f"""
                        <div class="metric-card green" style="min-height: 110px;">
                            <div class="icon">💳</div>
                            <h3 style="font-size: 0.75rem;">القسط الشهري الأقصى</h3>
                            <h2 style="font-size: 1.8rem;">{max_monthly_payment:,.0f} EGP</h2>
                            <div class="trend" style="font-size: 0.7rem;">
                                40% من الدخل
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col4:
                        st.markdown(f"""
                        <div class="metric-card purple" style="min-height: 110px;">
                            <div class="icon">🏦</div>
                            <h3 style="font-size: 0.75rem;">الدفعة الأولى المطلوبة</h3>
                            <h2 style="font-size: 1.8rem;">{required_down_payment:,.0f} EGP</h2>
                            <div class="trend" style="font-size: 0.7rem;">
                                {down_payment_percent*100:.0f}% من قيمة العقار
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                    
                    # ====== تفاصيل التمويل ======
                    st.markdown("### 📋 تفاصيل التمويل")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "🏦 نسبة الدفعة الأولى",
                            f"{down_payment_percent*100:.0f}%",
                            help="النسبة المطلوبة كدفعة أولى"
                        )
                        
                        st.metric(
                            "📈 نسبة الفائدة",
                            f"{interest_rate*100:.1f}%",
                            help="نسبة الفائدة السنوية"
                        )
                    
                    with col2:
                        st.metric(
                            "📅 مدة القرض",
                            f"{loan_term} سنة",
                            help="مدة سداد القرض"
                        )
                        
                        st.metric(
                            "💳 الحد الأقصى للقرض",
                            f"{max_loan:,.0f} EGP",
                            help="أقصى مبلغ يمكنك اقتراضه"
                        )
                    
                    with col3:
                        if np.isfinite(years_to_save):
                            st.metric(
                                "⏰ وقت الادخار للدفعة الأولى",
                                f"{years_to_save:.1f} سنة",
                                help=f"أي {months_to_save:.0f} شهر"
                            )
                        else:
                            st.metric(
                                "⏰ وقت الادخار للدفعة الأولى",
                                "غير ممكن",
                                help="المدخرات غير كافية"
                            )
                        
                        st.metric(
                            "📊 نسبة التمويل",
                            f"{(1 - down_payment_percent)*100:.0f}%",
                            help="نسبة المبلغ الذي سيموله البنك"
                        )
                    
                    # ====== تحليل الهدف المحدد ======
                    if target_price > 0 and target_down_payment:
                        st.markdown("### 🎯 تحليل الهدف المحدد")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "🏠 السعر المستهدف",
                                f"{target_price:,.0f} EGP"
                            )
                            
                            st.metric(
                                "💳 الدفعة الأولى المطلوبة",
                                f"{target_down_payment:,.0f} EGP"
                            )
                        
                        with col2:
                            st.metric(
                                "📆 القسط الشهري المتوقع",
                                f"{target_monthly_payment:,.0f} EGP"
                            )
                            
                            if is_affordable:
                                st.success("✅ هذا العقار في متناول يدك!")
                            else:
                                st.error("❌ هذا العقار غير متاح حالياً")
                                needed_increase = target_monthly_payment - max_monthly_payment
                                st.info(f"💡 تحتاج إلى زيادة الدخل بـ {needed_increase:,.0f} EGP شهرياً")
                        
                        with col3:
                            if np.isfinite(years_to_target):
                                st.metric(
                                    "⏰ وقت الادخار للهدف",
                                    f"{years_to_target:.1f} سنة",
                                    help=f"أي {months_to_target:.0f} شهر"
                                )
                            else:
                                st.metric(
                                    "⏰ وقت الادخار للهدف",
                                    "غير ممكن",
                                    help="المدخرات غير كافية"
                                )
                            
                            # نسبة تحقيق الهدف
                            if years_to_save > 0:
                                achievement_ratio = min((monthly_savings * 12) / (target_down_payment / years_to_save), 100)
                            else:
                                achievement_ratio = 0
                            st.metric(
                                "📊 نسبة تحقيق الهدف",
                                f"{achievement_ratio:.0f}%",
                                help="نسبة ما تم تحقيقه من الهدف"
                            )
                        
                        # ====== خطة الادخار ======
                        st.markdown("### 📈 خطة الادخار")
                        
                        if monthly_savings > 0 and target_down_payment:
                            # إنشاء خطة ادخار مفصلة
                            plan_df = generate_savings_plan(monthly_savings, target_down_payment)
                            
                            if not plan_df.empty:
                                # رسم بياني لخطة الادخار
                                fig = go.Figure()
                                
                                # خط المدخرات
                                fig.add_trace(go.Scatter(
                                    x=plan_df['الشهر'],
                                    y=plan_df['المدخرات المتراكمة'],
                                    mode='lines+markers',
                                    name='المدخرات المتراكمة',
                                    line=dict(color='#667eea', width=3),
                                    marker=dict(size=6),
                                    fill='tozeroy',
                                    fillcolor='#667eea30'
                                ))
                                
                                # خط الهدف
                                fig.add_hline(
                                    y=target_down_payment,
                                    line_dash="dash",
                                    line_color="#f5576c",
                                    annotation_text="🎯 الهدف",
                                    annotation_position="top right"
                                )
                                
                                fig.update_layout(
                                    title='📈 تقدم المدخرات نحو الهدف',
                                    xaxis_title='عدد الأشهر',
                                    yaxis_title='المدخرات (EGP)',
                                    height=400,
                                    hovermode='x unified',
                                    showlegend=True,
                                    template='plotly_white'
                                )
                                
                                st.plotly_chart(fig, width='stretch', key="savings_plan")
                                
                                # جدول الخطة
                                with st.expander("📋 تفاصيل خطة الادخار"):
                                    st.dataframe(
                                        plan_df,
                                        width='stretch',
                                        column_config={
                                            'الشهر': 'الشهر',
                                            'المدخرات المتراكمة': st.column_config.NumberColumn('المدخرات المتراكمة', format='%d EGP'),
                                            'نسبة الإنجاز': st.column_config.NumberColumn('نسبة الإنجاز', format='%.1f%%'),
                                            'المتبقي': st.column_config.NumberColumn('المتبقي', format='%d EGP')
                                        },
                                        hide_index=True
                                    )
                    
                    # ============================================================
                    # ========== التوصيات الذكية ==========
                    # ============================================================
                    
                    st.markdown("### 🏆 توصيات ذكية للعقارات")
                    
                    # الحصول على العقارات المناسبة
                    suitable_properties = df[
                        (df['price'] <= max_property_price * 1.2) &
                        (df['price'] >= max_property_price * 0.4)
                    ].copy()
                    
                    if not suitable_properties.empty:
                        # حساب العائد الاستثماري
                        if goal_type in ["استثمار", "شراء وإيجار"]:
                            suitable_properties['estimated_rent'] = suitable_properties['price'] * 0.006
                            suitable_properties['annual_return'] = suitable_properties['estimated_rent'] * 12
                            suitable_properties['roi'] = (suitable_properties['annual_return'] / suitable_properties['price']) * 100
                            suitable_properties['payback_years'] = suitable_properties['price'] / suitable_properties['annual_return']
                        
                        # حساب قيمة الصفقة
                        avg_ppm = df['price_per_m'].mean()
                        suitable_properties['value_score'] = (avg_ppm / suitable_properties['price_per_m']).clip(0, 2)
                        
                        # ترتيب حسب الأفضلية
                        if goal_type == "استثمار":
                            suitable_properties = suitable_properties.sort_values(
                                ['roi', 'value_score'], 
                                ascending=[False, False]
                            )
                        else:
                            suitable_properties = suitable_properties.sort_values(
                                ['value_score', 'price_per_m'], 
                                ascending=[False, True]
                            )
                        
                        # عرض التوصيات
                        st.markdown("#### ✅ العقارات المناسبة لك")
                        
                        # عرض أفضل 3 توصيات بشكل مميز
                        top_3 = suitable_properties.head(3)
                        
                        for idx, (_, row) in enumerate(top_3.iterrows()):
                            # حساب العائد المتوقع
                            roi_text = ""
                            if goal_type in ["استثمار", "شراء وإيجار"]:
                                roi = row.get('roi', 0)
                                roi_text = f"📈 العائد المتوقع: {roi:.1f}%"
                            
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #667eea08, #764ba208); 
                                        border: 2px solid #667eea40; border-radius: 15px; padding: 20px; 
                                        margin: 10px 0; transition: all 0.3s;">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                                    <div>
                                        <h4 style="color: #667eea; margin: 0;">🏠 {row.get('title', 'عقار')}</h4>
                                        <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 8px;">
                                            <span>📍 {row.get('location', 'N/A')}</span>
                                            <span>🏘️ {row.get('property_type', 'N/A')}</span>
                                            <span>💰 {row['price']:,.0f} EGP</span>
                                            <span>📐 {row.get('area', 0):.0f} m²</span>
                                            <span>📏 {row['price_per_m']:,.0f} EGP/m²</span>
                                            {f'<span>{roi_text}</span>' if roi_text else ''}
                                        </div>
                                    </div>
                                    <div style="display: flex; gap: 10px; align-items: center;">
                                        <span style="background: #43cea220; padding: 4px 15px; border-radius: 20px; color: #43cea2; font-weight: 600; font-size: 0.85rem;">
                                            {((avg_ppm - row['price_per_m']) / avg_ppm * 100 if row['price_per_m'] < avg_ppm else 0):.0f}% أفضل من المتوسط
                                        </span>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # عرض باقي التوصيات في جدول
                        with st.expander(f"📋 عرض جميع التوصيات ({len(suitable_properties)} عقار)"):
                            display_cols = ['title', 'property_type', 'price', 'location', 'area', 'price_per_m']
                            if goal_type in ["استثمار", "شراء وإيجار"]:
                                display_cols.extend(['roi', 'payback_years'])
                            
                            available_cols = [c for c in display_cols if c in suitable_properties.columns]
                            
                            column_config = {
                                'title': 'العنوان',
                                'property_type': 'النوع',
                                'price': st.column_config.NumberColumn('السعر', format='%d EGP'),
                                'location': 'الموقع',
                                'area': st.column_config.NumberColumn('المساحة', format='%.0f m²'),
                                'price_per_m': st.column_config.NumberColumn('سعر المتر', format='%d EGP'),
                                'roi': st.column_config.NumberColumn('العائد المتوقع', format='%.1f%%'),
                                'payback_years': st.column_config.NumberColumn('فترة الاسترداد', format='%.1f سنة')
                            }
                            
                            st.dataframe(
                                suitable_properties[available_cols].head(20),
                                width='stretch',
                                column_config=column_config,
                                hide_index=True
                            )
                    
                    else:
                        st.info("🔍 لا توجد عقارات مناسبة حالياً. جرب تعديل الفلاتر أو زيادة الدخل")
                    
                    # ============================================================
                    # ========== نصائح وتحليلات إضافية ==========
                    # ============================================================
                    
                    st.markdown("### 💡 نصائح وتحليلات")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 📊 تحليل الوضع المالي")
                        
                        # تقييم الوضع المالي
                        if savings_ratio > 30:
                            status = "🟢 ممتاز"
                            status_color = "#43cea2"
                            advice = "استمر في هذا المستوى من الادخار لتحقيق أهدافك بسرعة"
                        elif savings_ratio > 20:
                            status = "🟡 جيد"
                            status_color = "#ffd93d"
                            advice = "حاول زيادة نسبة الادخار إلى 30% لتسريع تحقيق الهدف"
                        else:
                            status = "🔴 يحتاج للتحسين"
                            status_color = "#ff6b6b"
                            advice = "راجع مصاريفك وحاول تقليل النفقات غير الضرورية"
                        
                        st.markdown(f"""
                        <div style="background: #667eea10; border-radius: 15px; padding: 15px; margin: 5px 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600;">حالة الادخار:</span>
                                <span style="color: {status_color}; font-weight: 700;">{status}</span>
                            </div>
                            <div style="margin-top: 8px; color: #888; font-size: 0.9rem;">
                                💡 {advice}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # نسبة القسط للدخل
                        if target_price > 0 and target_monthly_payment:
                            payment_to_income = (target_monthly_payment / monthly_income) * 100 if monthly_income > 0 else 0
                            st.markdown(f"""
                            <div style="background: #764ba210; border-radius: 15px; padding: 15px; margin: 5px 0;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: 600;">نسبة القسط للدخل:</span>
                                    <span style="color: {'#43cea2' if payment_to_income < 30 else '#ffd93d' if payment_to_income < 40 else '#ff6b6b'}; 
                                        font-weight: 700;">
                                        {payment_to_income:.1f}%
                                    </span>
                                </div>
                                <div style="margin-top: 8px; color: #888; font-size: 0.9rem;">
                                    { '✅ نسبة آمنة (أقل من 30%)' if payment_to_income < 30 else 
                                      '⚠️ نسبة مقبولة (30-40%)' if payment_to_income < 40 else 
                                      '❌ نسبة مرتفعة (أكثر من 40%) - يفضل تقليل القسط' }
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("#### 📈 توصيات حسب الهدف")
                        
                        if goal_type == "شراء (سكن)":
                            recommendations = [
                                "🔹 اختر موقعاً قريباً من الخدمات الأساسية (مدارس، مستشفيات، مواصلات)",
                                "🔹 تأكد من صحة الأوراق القانونية للعقار",
                                "🔹 ابحث عن عقارات في مناطق ذات نمو سكاني",
                                "🔹 استشر خبيراً قبل اتخاذ القرار النهائي",
                                "🔹 احسب التكاليف الإضافية (صيانة، ضرائب، تأمين)"
                            ]
                        elif goal_type == "استثمار":
                            recommendations = [
                                "🔹 استثمر في المناطق ذات الطلب المرتفع على الإيجار",
                                "🔹 اختر عقارات قريبة من الجامعات والشركات",
                                "🔹 احسب العائد الاستثماري بدقة قبل الشراء",
                                "🔹 تنويع الاستثمار في أكثر من منطقة",
                                "🔹 تابع اتجاهات السوق بشكل دوري"
                            ]
                        else:  # شراء وإيجار
                            recommendations = [
                                "🔹 اختر عقاراً يجمع بين السكن المريح والعائد الاستثماري",
                                "🔹 تأكد من وجود طلب على الإيجار في المنطقة",
                                "🔹 احسب العائد الإيجاري المتوقع",
                                "🔹 ضع خطة لإدارة العقار بشكل احترافي",
                                "🔹 احسب التكاليف التشغيلية والصيانة"
                            ]
                        
                        for rec in recommendations:
                            st.markdown(f"""
                            <div class="performance-indicator">
                                <span class="dot green"></span>
                                <span style="font-size: 0.9rem;">{rec}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # ============================================================
                    # ========== تصدير النتائج ==========
                    # ============================================================
                    
                    st.markdown("### 📥 تصدير النتائج")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # تصدير التوصيات
                        if not suitable_properties.empty:
                            st.markdown(export_to_csv(suitable_properties), unsafe_allow_html=True)
                    
                    with col2:
                        if not suitable_properties.empty:
                            st.markdown(export_to_excel(suitable_properties), unsafe_allow_html=True)
                    
                    with col3:
                        # تصدير خطة الادخار
                        if target_price > 0 and monthly_savings > 0:
                            if 'plan_df' in locals() and not plan_df.empty:
                                st.markdown(export_to_csv(plan_df), unsafe_allow_html=True)
                    
                    # ============================================================
                    # ========== تقرير كامل ==========
                    # ============================================================
                    
                    with st.expander("📊 عرض التقرير المالي الكامل"):
                        report_data = {
                            '📊 الملخص المالي': {
                                'الدخل الشهري': f"{monthly_income:,.0f} EGP",
                                'المصاريف الشهرية': f"{monthly_expenses:,.0f} EGP",
                                'المدخرات الشهرية': f"{monthly_savings:,.0f} EGP",
                                'المدخرات السنوية': f"{annual_savings:,.0f} EGP",
                                'نسبة الادخار': f"{savings_ratio:.1f}%"
                            },
                            '🏠 القدرة الشرائية': {
                                'الحد الأقصى للسعر': f"{max_property_price:,.0f} EGP",
                                'الحد الأقصى للقرض': f"{max_loan:,.0f} EGP",
                                'الدفعة الأولى المطلوبة': f"{required_down_payment:,.0f} EGP",
                                'القسط الشهري الأقصى': f"{max_monthly_payment:,.0f} EGP",
                                'وقت الادخار للدفعة الأولى': f"{years_to_save:.1f} سنة" if np.isfinite(years_to_save) else "غير ممكن"
                            },
                            '🎯 تفاصيل الهدف': {
                                'السعر المستهدف': f"{target_price:,.0f} EGP" if target_price > 0 else "غير محدد",
                                'الدفعة الأولى للهدف': f"{target_down_payment:,.0f} EGP" if target_down_payment else "غير محدد",
                                'القسط الشهري للهدف': f"{target_monthly_payment:,.0f} EGP" if target_monthly_payment else "غير محدد",
                                'في المتناول': "نعم" if is_affordable else "لا" if is_affordable is not None else "غير محدد",
                                'وقت الادخار للهدف': f"{years_to_target:.1f} سنة" if years_to_target and np.isfinite(years_to_target) else "غير محدد"
                            },
                            '🏦 شروط التمويل': {
                                'نسبة الدفعة الأولى': f"{down_payment_percent*100:.0f}%",
                                'نسبة الفائدة': f"{interest_rate*100:.1f}%",
                                'مدة القرض': f"{loan_term} سنة",
                                'نسبة التمويل': f"{(1 - down_payment_percent)*100:.0f}%"
                            },
                            '🎯 الهدف': {
                                'نوع الهدف': goal_type
                            }
                        }
                        
                        st.json(report_data)
                    
                    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                    
                    # ====== خاتمة ======
                    st.markdown("""
                    <div style="text-align: center; padding: 20px; color: #888;">
                        <p style="font-size: 1.1rem;">💡 تذكر أن هذه الحاسبة توفر تقديرات تقريبية</p>
                        <p style="font-size: 0.9rem;">يُنصح بالاستعانة بخبير مالي أو عقاري قبل اتخاذ القرار النهائي</p>
                    </div>
                    """, unsafe_allow_html=True)

# ========== Footer ==========
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; padding: 20px; color: #666;">
    <p>🏠 Real Estate Egypt Dashboard | AI-Powered Smart Analytics</p>
    <p style="font-size: 0.8em;">Version 7.0 - Enhanced Design & Dynamic Insights</p>
</div>
""", unsafe_allow_html=True)