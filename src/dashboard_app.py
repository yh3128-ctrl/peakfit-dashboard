import streamlit as st
import pandas as pd
import numpy as np
import os

# --- Page Config ---
st.set_page_config(page_title="PeakFit 큐레이션 대시보드", page_icon="⛰️", layout="wide")

# --- Custom CSS (Premium UI) ---
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #3B82F6;
    }
    .tag-bubble {
        display: inline-block;
        background: linear-gradient(135deg, #3B82F6, #2563EB);
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 5px;
        margin-bottom: 5px;
    }
    .foodie-tag {
        background: linear-gradient(135deg, #F59E0B, #EA580C);
    }
    </style>
""", unsafe_allow_html=True)

# --- Load Data ---
@st.cache_data
def load_data():
    base_dir = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt"
    data_path = os.path.join(base_dir, "data", "processed", "PeakFit_Final_Curation_DB.csv")
    places_path = os.path.join(base_dir, "data", "raw", "team-share", "mountain_places_v3.csv")
    
    if not os.path.exists(data_path):
        return pd.DataFrame(), pd.DataFrame()
        
    df = pd.read_csv(data_path)
    df_places = pd.read_csv(places_path) if os.path.exists(places_path) else pd.DataFrame()
    return df, df_places

df, df_places = load_data()

if df.empty:
    st.error("데이터 파일을 찾을 수 없습니다. PeakFit_Final_Curation_DB.csv 파일이 존재하는지 확인해주세요.")
    st.stop()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2) * np.sin(dlambda/2)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1-a)))

# --- Sidebar Filters ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2836/2836544.png", width=60)
st.sidebar.title("🏔️ PeakFit 조건 설정")
st.sidebar.markdown("나에게 딱 맞는 등산 코스를 찾아보세요!")

# 1. 페르소나 선택
persona_options = ["상관없음"] + sorted(df['Persona_Type'].dropna().unique().tolist())
selected_persona = st.sidebar.selectbox("💡 어떤 분위기의 등산을 원하시나요?", persona_options)

# 2. 체력 수준 조절
st.sidebar.markdown("---")
st.sidebar.subheader("💪 체력 및 난이도")
max_endurance = st.sidebar.slider("최대 체력 소모량 한계 (100점 만점)", min_value=10, max_value=100, value=50, step=5)
max_joint = st.sidebar.slider("관절/무릎 부담 한계 (100점 만점)", min_value=10, max_value=100, value=60, step=5)

# 3. 하산 후 맛집
st.sidebar.markdown("---")
st.sidebar.subheader("🍲 하산 후 경험")
need_foodie = st.sidebar.checkbox("도보 20분 내 찐맛집 필수 (미식 코스만 보기)")

# --- Filter Logic ---
filtered_df = df.copy()

if selected_persona != "상관없음":
    filtered_df = filtered_df[filtered_df['Persona_Type'] == selected_persona]

filtered_df = filtered_df[
    (filtered_df['Score_Endurance'] <= max_endurance) & 
    (filtered_df['Score_Joint_Strain'] <= max_joint)
]

if need_foodie:
    filtered_df = filtered_df[filtered_df['Foodie_Index_100'] > 0]
    filtered_df = filtered_df.sort_values(by=['Foodie_Index_100', 'Score_Endurance'], ascending=[False, True])
else:
    filtered_df = filtered_df.sort_values(by=['Score_Endurance'])

# --- Main Layout ---
st.markdown('<div class="main-header">PeakFit 2030 맞춤형 큐레이션</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">선택하신 조건에 맞는 최적의 코스 리스트입니다. (총 {}개 코스 발견)</div>'.format(len(filtered_df)), unsafe_allow_html=True)

if len(filtered_df) == 0:
    st.warning("조건에 맞는 코스가 없습니다. 필터 조건을 조금 완화해 보세요!")
else:
    top_courses = filtered_df.head(5)
    
    for idx, row in top_courses.iterrows():
        mountain = row.get('Mountain', row.get('join_key', 'Unknown'))
        
        with st.container():
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader(f"🚩 {mountain} ({row['Filename'].replace('.gpx','')})")
                
                tags = str(row['Final_Curation_Tags']).split()
                tag_html = ""
                for t in tags:
                    if '맛집' in t or '미식' in t:
                        tag_html += f'<span class="tag-bubble foodie-tag">{t}</span>'
                    else:
                        tag_html += f'<span class="tag-bubble">{t}</span>'
                st.markdown(tag_html, unsafe_allow_html=True)
                st.write("")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("총 거리", f"{row['Total_Distance_km']} km")
                m2.metric("예상 소요 시간", f"{row['Estimated_Time_hrs']} 시간")
                m3.metric("누적 획득 고도", f"{row['Elevation_Gain_m']} m")
                
                st.markdown(f"**💡 산행 요약:** {row.get('산_개요', '설명 없음')}")
            
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown("#### 📊 PeakFit 지표")
                st.progress(row['Score_Endurance'] / 100, text=f"체력 소모도 ({row['Score_Endurance']}점)")
                st.progress(row['Score_Joint_Strain'] / 100, text=f"관절 무리도 ({row['Score_Joint_Strain']}점)")
                
                foodie_score = row.get('Foodie_Index_100', 0)
                st.progress(foodie_score / 100, text=f"뚜벅이 미식 지수 ({foodie_score}점)")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # 맛집 추천 리스트 표시 (Expander)
        if foodie_score > 0 and not df_places.empty:
            with st.expander("🍲 이 코스의 하산 지점 도보 20분 거리 맛집 보기"):
                end_lat = row['End_Lat']
                end_lon = row['End_Lon']
                
                # 벡터 연산으로 거리 계산
                places_filtered = df_places.copy()
                places_filtered['거리(m)'] = haversine(
                    end_lat, end_lon, 
                    places_filtered['장소위도'].values, 
                    places_filtered['장소경도'].values
                )
                
                # 1.5km 이내 & 맛집 점수 60점 이상 필터링 후 점수순 정렬
                good_places = places_filtered[
                    (places_filtered['거리(m)'] <= 1500) & 
                    (places_filtered['맛집점수'] >= 60)
                ].sort_values('맛집점수', ascending=False).head(3)
                
                if len(good_places) > 0:
                    for _, place in good_places.iterrows():
                        st.markdown(f"**[{place['장소명']}]({place['카카오지도URL']})** - {place['카테고리']} (★{place['맛집점수']}점 / 하산지점으로부터 {int(place['거리(m)'])}m)")
                else:
                    st.write("강력 추천할 만한 찐맛집이 주변에 부족합니다.")
        
        st.markdown("---")

    # --- 하단 지도 시각화 ---
    st.markdown("### 🗺️ 추천 코스 하산 지점 (맛집 탐방 시작점)")
    map_df = top_courses[['End_Lat', 'End_Lon', 'Mountain']].dropna()
    if not map_df.empty:
        map_df = map_df.rename(columns={'End_Lat': 'lat', 'End_Lon': 'lon'})
        st.map(map_df, zoom=6, use_container_width=True)
    else:
        st.info("지도에 표시할 좌표가 없습니다.")
