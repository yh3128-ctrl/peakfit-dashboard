import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import streamlit as st
import pandas as pd
import numpy as np
import os
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import gpxpy

# --- Page Configuration ---
st.set_page_config(page_title="PeakFit Dashboard", page_icon="⛰️", layout="wide")

# --- Custom CSS (Minimalist White & Forest Green) ---
st.markdown("""
    <style>
    .main-header { font-size: 2.2rem; font-weight: 800; color: #1B5E20; margin-bottom: 0px; }
    .sub-header { font-size: 1.1rem; color: #4CAF50; margin-bottom: 2rem; font-weight: 600; }
    .summary-card { background-color: #FFFFFF; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-left: 6px solid #2E7D32; margin-bottom: 20px; }
    .tag-bubble { display: inline-block; background-color: #E8F5E9; color: #2E7D32; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; margin-right: 5px; margin-bottom: 5px; border: 1px solid #C8E6C9; }
    .poi-card { background-color: #FAFAFA; border: 1px solid #EEEEEE; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- Utility Functions ---
@st.cache_data
def load_data():
    # Streamlit Cloud 배포를 위해 동적(상대) 경로로 변경
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir) # tracking-pjt 폴더
    
    curation_path = os.path.join(base_dir, "data", "processed", "PeakFit_Final_Curation_DB.csv")
    places_path = os.path.join(base_dir, "data", "raw", "team-share", "mountain_places_v3.csv")
    
    df_curation = pd.read_csv(curation_path) if os.path.exists(curation_path) else pd.DataFrame()
    df_places = pd.read_csv(places_path) if os.path.exists(places_path) else pd.DataFrame()
    return df_curation, df_places, base_dir

df, df_places, base_dir = load_data()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2) * np.sin(dlambda/2)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1-a)))

def calculate_custom_difficulty(row):
    """지시하신 5가지 가중치 기반 난이도 스코어 산출 (결측치는 평균치로 대체)"""
    # 임의/기존 데이터로 스케일링
    slope_score = min((row.get('Max_Slope_%', 15) / 30) * 100, 100) * 0.30
    rock_score = row.get('암반비율', 20) * 0.30  # 추후 API 대체, 현재 고정값
    ele_score = min((row.get('Elevation_Gain_m', 400) / 1000) * 100, 100) * 0.20
    dist_score = min((row.get('Total_Distance_km', 5) / 15) * 100, 100) * 0.10
    review_score = row.get('볼거리_점수', 3) / 5 * 100 * 0.10
    
    total = slope_score + rock_score + ele_score + dist_score + review_score
    
    if total <= 35: return "입문 (Beginner)"
    elif total <= 60: return "초급 (Novice)"
    else: return "중급 (Intermediate)"

def parse_gpx_for_viz(mountain, filename):
    """GPX 데이터를 읽어 지도/고도 차트용 DataFrame 반환"""
    # 산 이름에 괄호가 있다면 원본 폴더명 매칭을 위해 확인 필요. 여기선 단순 매핑.
    gpx_path = os.path.join(base_dir, "data", "raw", "100대명산", mountain, filename)
    if not os.path.exists(gpx_path):
        # 괄호 포함된 원본 폴더 탐색 로직 (간이)
        dirs = os.listdir(os.path.join(base_dir, "data", "raw", "100대명산"))
        for d in dirs:
            if d.startswith(mountain):
                gpx_path = os.path.join(base_dir, "data", "raw", "100대명산", d, filename)
                break
                
    if not os.path.exists(gpx_path): return pd.DataFrame()
    
    points = []
    try:
        with open(gpx_path, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
        dist = 0
        prev = None
        for track in gpx.tracks:
            for segment in track.segments:
                for p in segment.points:
                    if prev: dist += p.distance_2d(prev)
                    points.append({'lat': p.latitude, 'lon': p.longitude, 'ele': p.elevation, 'dist_km': dist/1000})
                    prev = p
    except:
        pass
    return pd.DataFrame(points)

# --- Sidebar ---
st.sidebar.title("🏔️ PeakFit")
st.sidebar.markdown("2030 입문자 맞춤형 등산 큐레이션")

st.sidebar.subheader("1. 난이도 선택")
diff_filter = st.sidebar.selectbox("타겟팅 코스 난이도", ["전체보기", "입문 (Beginner)", "초급 (Novice)", "중급 (Intermediate)"])

st.sidebar.subheader("2. 이동 수단")
transport = st.sidebar.radio("어떻게 이동하시나요?", ["대중교통 (뚜벅이)", "자차 (주차장 필요)"])

st.sidebar.subheader("3. 하산 후 활동")
apres_hike = st.sidebar.radio("하산 후 가장 원하는 것은?", ["맛집 탐방", "카페 휴식"])

# --- Data Processing & Filtering ---
df['Custom_Diff'] = df.apply(calculate_custom_difficulty, axis=1)

if diff_filter != "전체보기":
    df = df[df['Custom_Diff'] == diff_filter]

if transport == "대중교통 (뚜벅이)":
    df = df[df['대중교통접근'] == 'O']

# 서울 테스트 데이터 필터링 기능
region_test = st.sidebar.checkbox("서울/경기 지역만 보기 (테스트용)", value=True)
if region_test:
    df = df[df['소재지'].str.contains('서울|경기', na=False)]

# Sort by Foodie Index
df = df.sort_values('Foodie_Index_100', ascending=False)

if df.empty:
    st.error("조건에 맞는 코스가 없습니다. 필터를 조정해주세요.")
    st.stop()

# Select top course for One-Page
target_course = df.iloc[0]
mountain_name = target_course.get('join_key', target_course.get('Mountain'))

# --- Main Section: Summary Card ---
st.markdown(f'<div class="main-header">{mountain_name} - {target_course["Filename"].replace(".gpx","")}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">당신의 주말을 책임질 완벽한 큐레이션</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    
    # Tags
    tags = str(target_course.get('Final_Curation_Tags', '#풍경맛집')).split()
    tag_html = "".join([f'<span class="tag-bubble">{t}</span>' for t in tags])
    st.markdown(tag_html, unsafe_allow_html=True)
    st.write("")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 난이도", target_course['Custom_Diff'].split()[0])
    c2.metric("📏 총 거리", f"{target_course['Total_Distance_km']} km")
    c3.metric("⏱️ 예상 시간", f"{target_course.get('Estimated_Time_hrs', round(target_course['Total_Distance_km']*1.2, 1))} 시간")
    c4.metric("⛰️ 획득 고도", f"{target_course['Elevation_Gain_m']} m")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- Main Section: Route Analysis ---
st.markdown("### 🗺️ 코스 경로 및 고도 프로파일")

gpx_df = parse_gpx_for_viz(mountain_name, target_course['Filename'])

col_map, col_chart = st.columns([1, 1])

if not gpx_df.empty:
    with col_map:
        # Folium Map
        m = folium.Map(location=[gpx_df['lat'].mean(), gpx_df['lon'].mean()], zoom_start=13, tiles="CartoDB Positron")
        # Line
        route_coords = list(zip(gpx_df['lat'], gpx_df['lon']))
        folium.PolyLine(route_coords, color="#2E7D32", weight=4, opacity=0.8).add_to(m)
        
        # Markers
        folium.Marker(route_coords[0], popup="들머리(Start)", icon=folium.Icon(color='green', icon='play')).add_to(m)
        folium.Marker(route_coords[-1], popup="날머리(End)", icon=folium.Icon(color='red', icon='stop')).add_to(m)
        peak_idx = gpx_df['ele'].idxmax()
        folium.Marker(route_coords[peak_idx], popup=f"정상({gpx_df.iloc[peak_idx]['ele']}m)", icon=folium.Icon(color='orange', icon='star')).add_to(m)
        
        st_folium(m, width=500, height=350, returned_objects=[])

    with col_chart:
        # Plotly Elevation
        gpx_df['slope'] = gpx_df['ele'].diff() / (gpx_df['dist_km'].diff() * 1000) * 100
        gpx_df['slope'] = gpx_df['slope'].fillna(0)
        
        fig = px.area(gpx_df, x='dist_km', y='ele', color_discrete_sequence=['#A5D6A7'])
        
        # 가파른 구간 (경사도 20% 이상) 붉은색 강조
        steep_df = gpx_df[gpx_df['slope'] >= 20]
        if not steep_df.empty:
            fig.add_trace(go.Scatter(x=steep_df['dist_km'], y=steep_df['ele'], mode='markers', 
                                     marker=dict(color='#D32F2F', size=5), name='위험/급경사(>20%)'))
                                     
        fig.update_layout(title="구간별 고도 및 급경사 주의 구간", xaxis_title="거리 (km)", yaxis_title="해발 고도 (m)", 
                          margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("GPX 경로 데이터를 불러올 수 없습니다.")

# --- Bottom Section: Logistics & Apres-Hike ---
st.markdown("---")
st.markdown("### 🚌 접근성 및 하산 후 큐레이션")

c_logistics, c_apres = st.columns([1, 1])

with c_logistics:
    st.subheader("📍 이동 동선 가이드")
    if transport == "대중교통 (뚜벅이)":
        st.success("✅ **대중교통 접근성 우수 코스입니다.**")
        st.write(f"가까운 지하철역/버스 정류장에서 들머리(출발점)까지 도보로 원활하게 이동 가능합니다. (교통수단: {target_course.get('교통수단_목록', '정보 없음')})")
    else:
        st.info("🚗 **자차 이용 가이드**")
        st.write("들머리 부근 공영/민영 주차장 정보를 확인하세요. 주말에는 만차가 빠를 수 있으니 오전 8시 이전 도착을 권장합니다.")

with c_apres:
    st.subheader(f"🍲 날머리 기준 반경 1km 추천 {apres_hike.split()[0]}")
    
    if not df_places.empty:
        poi_type = '음식점' if '맛집' in apres_hike else '카페'
        df_places['거리(m)'] = haversine(target_course['End_Lat'], target_course['End_Lon'], df_places['장소위도'].values, df_places['장소경도'].values)
        
        recs = df_places[(df_places['장소유형'] == poi_type) & (df_places['거리(m)'] <= 1000) & (df_places['맛집점수'] >= 60)]
        recs = recs.sort_values('맛집점수', ascending=False).head(3)
        
        if not recs.empty:
            for _, p in recs.iterrows():
                st.markdown(f"""
                <div class="poi-card">
                    <strong><a href="{p['카카오지도URL']}" target="_blank" style="color:#2E7D32; text-decoration:none;">{p['장소명']}</a></strong> (★ {p['맛집점수']}점)<br>
                    <span style="color:#757575; font-size:0.9rem;">{p['카테고리']} | 날머리에서 도보 {int(p['거리(m)']/75)}분 ({int(p['거리(m)'])}m)</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write(f"안타깝게도 날머리 근처 1km 내에 고득점 {apres_hike.split()[0]}이 없습니다.")
    else:
        st.write("POI 데이터를 불러오지 못했습니다.")
