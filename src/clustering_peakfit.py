import pandas as pd
import numpy as np
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def perform_clustering():
    print("=== PeakFit 등산로 K-Means 군집화 및 페르소나 매핑 시작 ===")
    
    data_dir = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\processed"
    scored_db_path = os.path.join(data_dir, "PeakFit_Scored_DB.csv")
    
    if not os.path.exists(scored_db_path):
        print(f"Scored DB 파일을 찾을 수 없습니다: {scored_db_path}")
        return
        
    df = pd.read_csv(scored_db_path)
    
    # 1. 군집화에 사용할 핵심 피처 선정
    # 체력, 관절 무리도, 그리고 케이블카/경관 코스를 구분하기 위한 최고 고도와 거리
    features = ['Score_Endurance', 'Score_Joint_Strain', 'Max_Elevation_m', 'Total_Distance_km']
    X = df[features].fillna(0)
    
    # 2. 데이터 스케일링 (K-Means는 거리 기반 알고리즘이므로 필수)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 3. K-Means 군집화 (3개의 페르소나 유형으로 분류)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df['Cluster_ID'] = kmeans.fit_predict(X_scaled)
    
    # 4. 각 군집의 중심점(Centroid)을 분석하여 자동으로 페르소나 라벨링
    cluster_centers = pd.DataFrame(scaler.inverse_transform(kmeans.cluster_centers_), columns=features)
    cluster_centers['Cluster_ID'] = range(3)
    
    # 유형 맵핑 로직
    # A. 체력 점수가 가장 낮은 그룹 -> "산책/인스타용"
    # B. 거리에 비해 관절 점수가 높거나 전체적으로 빡센 그룹 -> "단기 성취감/땀샘폭발"
    # C. 최고 고도는 높지만 거리가 길어 완만한 장거리 또는 케이블카 연계(상대적) -> "경관/풍경맛집"
    
    # 체력 점수를 기준으로 오름차순 정렬하여 가장 쉬운 것을 A유형으로 할당
    sorted_by_endurance = cluster_centers.sort_values(by='Score_Endurance')
    
    easy_cluster = sorted_by_endurance.iloc[0]['Cluster_ID']
    hard_cluster = sorted_by_endurance.iloc[2]['Cluster_ID']
    mid_cluster = sorted_by_endurance.iloc[1]['Cluster_ID']
    
    def map_persona(cluster_id):
        if cluster_id == easy_cluster:
            return "유형 A (산책/인스타용)"
        elif cluster_id == hard_cluster:
            return "유형 B (단기 성취감/땀샘폭발)"
        else:
            return "유형 C (풍경맛집/장거리)"
            
    def generate_persona_tags(persona):
        if "유형 A" in persona:
            return "#가벼운발걸음 #오운완 #초보환영"
        elif "유형 B" in persona:
            return "#짧고굵게 #땀샘폭발 #애플워치링채우기"
        else:
            return "#케이블카찬스 #풍경맛집 #인생샷"

    df['Persona_Type'] = df['Cluster_ID'].apply(map_persona)
    df['Persona_Tags'] = df['Persona_Type'].apply(generate_persona_tags)
    
    # 5. 결과 저장
    out_path = os.path.join(data_dir, "PeakFit_Clustered_DB.csv")
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    
    print("군집화 및 페르소나 매핑 완료!")
    print("\n[군집별 중심 데이터 (평균 특성)]")
    cluster_summary = df.groupby('Persona_Type')[features].mean().round(1)
    print(cluster_summary)
    
    print(f"\n군집화 결과 파일 저장 완료: {out_path}")

if __name__ == "__main__":
    perform_clustering()
