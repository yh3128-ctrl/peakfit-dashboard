import pandas as pd
import numpy as np
import math
import os

def haversine(lat1, lon1, lat2, lon2):
    """두 위경도 좌표 사이의 거리를 계산 (단위: 미터)"""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def perform_hybrid_curation():
    print("=== PeakFit 하이브리드 추천(Spatial Join) 로직 실행 시작 ===")
    
    processed_dir = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\processed"
    raw_share_dir = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\raw\team-share"
    
    clustered_db_path = os.path.join(processed_dir, "PeakFit_Clustered_DB.csv")
    master_info_path = os.path.join(raw_share_dir, "100mountains_master.csv")
    places_path = os.path.join(raw_share_dir, "mountain_places_v3.csv")
    
    # 1. 데이터 로드
    df_gpx = pd.read_csv(clustered_db_path)
    df_master = pd.read_csv(master_info_path)
    df_places = pd.read_csv(places_path)
    
    # 2. 산 이름 정제 (조인키)
    def clean_name(name):
        if pd.isna(name): return ""
        return str(name).split('(')[0].strip()
        
    df_master['join_key'] = df_master['산이름'].apply(clean_name)
    # df_gpx는 이미 이전 스텝에서 join_key가 있거나 Mountain 기반으로 처리됨.
    # 만약 join_key가 없다면 새로 생성
    if 'join_key' not in df_gpx.columns:
        df_gpx['join_key'] = df_gpx['Mountain'].apply(clean_name)
        
    # 산 단위 특성(볼거리, 계단, 위험요인 등)을 GPX 데이터에 결합 (Left Join)
    # 마스터 데이터는 동일 산이라도 코스별로 중복이 있을 수 있으니, 산 단위 평균/첫값만 가져옴
    master_agg = df_master.groupby('join_key').agg({
        '볼거리_점수': 'mean',
        '접근성_점수': 'mean',
        '계단_시설수': 'max',
        '위험요인_목록': 'first'
    }).reset_index()
    
    df_merged = pd.merge(df_gpx, master_agg, on='join_key', how='left')
    
    # 3. 공간 조인 (Spatial Join): 하산 지점 기준 미식 지수 계산
    print("하산 지점(End_Lat, End_Lon) 기준 맛집 데이터 탐색 중...")
    
    foodie_scores = []
    cafe_counts = []
    
    # Places 데이터 정제
    df_places['장소위도'] = pd.to_numeric(df_places['장소위도'], errors='coerce')
    df_places['장소경도'] = pd.to_numeric(df_places['장소경도'], errors='coerce')
    df_places['맛집점수'] = pd.to_numeric(df_places['맛집점수'], errors='coerce')
    
    for idx, row in df_merged.iterrows():
        end_lat = row.get('End_Lat')
        end_lon = row.get('End_Lon')
        mountain = row.get('join_key')
        
        score = 0
        cafe_cnt = 0
        
        if pd.notna(end_lat) and pd.notna(end_lon):
            # 해당 산 주변의 맛집만 필터링 (계산량 감소)
            # 산 이름이 완전히 일치하지 않을 수 있으니 필터링 없이 전체 계산하거나, 산이름 포함 여부로 필터
            target_places = df_places[df_places['산이름'].str.contains(mountain, na=False, regex=False)]
            
            for _, place in target_places.iterrows():
                plat = place['장소위도']
                plon = place['장소경도']
                if pd.notna(plat) and pd.notna(plon):
                    dist = haversine(end_lat, end_lon, plat, plon)
                    # 하산 지점 기준 1.5km 이내의 검증된 맛집(60점 이상) 카운팅
                    if dist <= 1500 and place['맛집점수'] >= 60:
                        if place['장소유형'] == '음식점':
                            score += 1
                        elif place['장소유형'] == '카페':
                            cafe_cnt += 1
                            
        foodie_scores.append(score)
        cafe_counts.append(cafe_cnt)
        
    df_merged['Foodie_Score'] = foodie_scores
    df_merged['Cafe_Count'] = cafe_counts
    
    # 미식 지수 스케일링 (100점 만점)
    max_foodie = max(foodie_scores) if max(foodie_scores) > 0 else 1
    df_merged['Foodie_Index_100'] = np.round((df_merged['Foodie_Score'] / max_foodie) * 100, 1)
    
    # 4. 최종 XAI 태그 고도화
    def enhance_tags(row):
        existing_tags = str(row.get('Persona_Tags', ''))
        new_tags = []
        if row['Foodie_Index_100'] >= 70:
            new_tags.append("#하산후맛집천국")
        if row.get('볼거리_점수', 0) >= 4.0:
            new_tags.append("#볼거리눈호강")
        if row.get('계단_시설수', 0) > 10:
            new_tags.append("#계단지옥")
            
        final_tags = existing_tags + " " + " ".join(new_tags)
        return final_tags.strip()

    df_merged['Final_Curation_Tags'] = df_merged.apply(enhance_tags, axis=1)
    
    # 5. 최종 큐레이션 파일 저장
    out_path = os.path.join(processed_dir, "PeakFit_Final_Curation_DB.csv")
    df_merged.to_csv(out_path, index=False, encoding='utf-8-sig')
    
    print("\n공간 조인 기반 하이브리드 추천 로직 완성!")
    print(f"최종 큐레이션 DB 저장 완료: {out_path}")
    print(f"-> 음식점 매핑 성공 코스 수: {len(df_merged[df_merged['Foodie_Score'] > 0])}개")

if __name__ == "__main__":
    perform_hybrid_curation()
