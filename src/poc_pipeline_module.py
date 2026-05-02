import pandas as pd
import numpy as np
import math
import json
import plotly.express as px
import plotly.graph_objects as go
import gpxpy

class PeakFitPoCPipeline:
    def __init__(self, course_db_path, poi_db_path, gpx_base_dir):
        self.course_df = pd.read_csv(course_db_path) if course_db_path else pd.DataFrame()
        self.poi_df = pd.read_csv(poi_db_path) if poi_db_path else pd.DataFrame()
        self.gpx_base_dir = gpx_base_dir

    # ---------------------------------------------------------
    # 1. 데이터 결합 로직 (들머리/날머리 공간 조인)
    # ---------------------------------------------------------
    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2) * np.sin(dlambda/2)**2
        return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1-a)))

    def match_pois_to_course(self, course_row, poi_type='맛집', radius_m=1000, condition='하산점'):
        """
        들머리(시작점) 또는 날머리(하산점) 기준으로 POI를 매칭합니다.
        """
        if self.poi_df.empty: return []
        
        # 들머리(교통/주차장) vs 날머리(맛집/카페) 분기
        ref_lat = course_row['Start_Lat'] if condition == '시작점' else course_row['End_Lat']
        ref_lon = course_row['Start_Lon'] if condition == '시작점' else course_row['End_Lon']
        
        # 카카오 평점 3.5 이상 필터링 (맛집/카페 한정)
        valid_pois = self.poi_df.copy()
        if poi_type in ['음식점', '카페']:
            valid_pois = valid_pois[(valid_pois['장소유형'] == poi_type) & (valid_pois['맛집점수'] >= 60)] # 점수 환산 기준 반영
            
        valid_pois['거리(m)'] = self._haversine(ref_lat, ref_lon, valid_pois['장소위도'].values, valid_pois['장소경도'].values)
        matched = valid_pois[valid_pois['거리(m)'] <= radius_m].sort_values('거리(m)')
        
        return matched[['장소명', '카테고리', '거리(m)', '카카오지도URL']].to_dict('records')

    # ---------------------------------------------------------
    # 2. 난이도 라벨링 및 고도 프로필 시각화
    # ---------------------------------------------------------
    def label_difficulty(self, elevation_gain, total_distance):
        """총 거리와 누적 고도를 바탕으로 2030 입문자 맞춤형 직관적 난이도 라벨링"""
        if elevation_gain <= 400 and total_distance <= 5:
            return "입문 (산책 같은 코스)"
        elif elevation_gain <= 800 and total_distance <= 10:
            return "초급 (오운완 땀샘폭발)"
        else:
            return "중급 (무릎 보호대 필수)"

    def plot_elevation_profile(self, gpx_file_path):
        """GPX를 파싱하여 Plotly로 직관적인 고도 차트(위험도 구간 표시) 생성"""
        try:
            with open(gpx_file_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)
        except Exception as e:
            return None

        points = []
        distance = 0
        prev_point = None

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if prev_point:
                        distance += point.distance_2d(prev_point)
                    points.append({'거리(km)': distance / 1000, '해발고도(m)': point.elevation})
                    prev_point = point

        df_profile = pd.DataFrame(points)
        
        # 경사도(Slope)가 급한 구간을 시각적으로 붉게 표시하기 위한 로직
        df_profile['경사도'] = df_profile['해발고도(m)'].diff() / df_profile['거리(km)'].diff() / 1000 * 100
        
        fig = px.area(df_profile, x='거리(km)', y='해발고도(m)', 
                      title="🗺️ 코스 고도 프로파일 (빨간색: 급경사 주의 구간)",
                      color_discrete_sequence=['#3B82F6'])
        
        # 급경사 구역(15% 이상) 하이라이팅
        steep_zones = df_profile[df_profile['경사도'] > 15]
        if not steep_zones.empty:
            fig.add_trace(go.Scatter(x=steep_zones['거리(km)'], y=steep_zones['해발고도(m)'], 
                                     mode='markers', marker=dict(color='red', size=4), name='급경사'))
        return fig

    # ---------------------------------------------------------
    # 3. 페르소나별 출력 (Dashboard Output - JSON)
    # ---------------------------------------------------------
    def get_curation_card_json(self, region, transit_only=False, activity_type='음식점'):
        """유저의 선택 필터에 맞춰 원페이지 JSON 응답을 생성"""
        df = self.course_df.copy()
        
        # 1. 지역 필터링
        if region:
            df = df[df['소재지'].str.contains(region, na=False)]
            
        # 2. 이동 수단 필터링 (대중교통 여부)
        if transit_only and '대중교통접근' in df.columns:
            df = df[df['대중교통접근'] == 'O']
            
        # 3. 미식/액티비티 지수 높은 순으로 정렬 후 최적 1개 코스 추출
        df = df.sort_values(by=['Foodie_Index_100', 'Score_Endurance'], ascending=[False, True])
        
        if df.empty:
            return json.dumps({"error": "조건에 맞는 코스가 없습니다."})
            
        best_course = df.iloc[0]
        
        # 날머리 기준 맛집/카페 매칭
        poi_list = self.match_pois_to_course(best_course, poi_type=activity_type, radius_m=1000, condition='하산점')
        
        # 최종 JSON 페이로드 조립
        payload = {
            "mountain_name": best_course['Mountain'],
            "course_summary": {
                "distance_km": round(best_course['Total_Distance_km'], 1),
                "elevation_gain_m": round(best_course['Elevation_Gain_m'], 1),
                "difficulty_label": self.label_difficulty(best_course['Elevation_Gain_m'], best_course['Total_Distance_km']),
                "tags": str(best_course.get('Final_Curation_Tags', '')).split()
            },
            "transit_info": {
                # 추후 들머리 매칭 로직으로 채워질 부분
                "accessible_by_bus": "O" if best_course.get('대중교통접근') == 'O' else "X"
            },
            "after_hike_curation": {
                "activity_type": activity_type,
                "recommended_spots": poi_list[:3] # 상위 3개만 응답
            }
        }
        
        return json.dumps(payload, ensure_ascii=False, indent=2)

# Usage Example:
# pipeline = PeakFitPoCPipeline(course_db_path='...', poi_db_path='...', gpx_base_dir='...')
# result_json = pipeline.get_curation_card_json(region='서울', transit_only=True, activity_type='음식점')
# fig = pipeline.plot_elevation_profile(gpx_file_path='...')
