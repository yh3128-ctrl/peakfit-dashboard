import pandas as pd
import numpy as np
import os

def calculate_peakfit_scores():
    print("=== PeakFit 난이도 지수 분석 모델링 시작 ===")
    
    data_dir = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\processed"
    master_db_path = os.path.join(data_dir, "PeakFit_Master_DB.csv")
    
    if not os.path.exists(master_db_path):
        print(f"Master DB 파일을 찾을 수 없습니다: {master_db_path}")
        return
        
    df = pd.read_csv(master_db_path)
    
    # NaN 결측치 처리 (0으로 채움)
    features = ['Total_Distance_km', 'Elevation_Gain_m', 'Average_Slope_%', 'Max_Slope_%']
    df[features] = df[features].fillna(0)
    
    # 스케일링 준비 (이상치가 있을 수 있으므로 상위 99% 윈저라이징 적용 후 Min-Max 스케일링)
    def apply_winsorize_and_scale(column):
        upper_limit = df[column].quantile(0.99)
        clipped_data = df[column].clip(upper=upper_limit)
        min_val = clipped_data.min()
        max_val = clipped_data.max()
        if max_val == min_val:
            return pd.Series(1, index=clipped_data.index) # 모든 값이 같으면 1점
        scaled = ((clipped_data - min_val) / (max_val - min_val)) * 99 + 1
        return np.round(scaled, 1)

    # 1. 체력 소모도 (Endurance Score) 산출
    # 획득 고도(60%) + 이동 거리(40%) 가중치
    scaled_distance = apply_winsorize_and_scale('Total_Distance_km')
    scaled_elevation = apply_winsorize_and_scale('Elevation_Gain_m')
    
    df['Score_Endurance'] = np.round((scaled_elevation * 0.6) + (scaled_distance * 0.4), 1)
    
    # 2. 관절 무리도 (Joint Strain Score) 산출
    # 추후 노면 데이터(API)가 들어오면 업데이트됨. 현재는 평균 경사도(40%) + 최대 경사도(60%)
    scaled_avg_slope = apply_winsorize_and_scale('Average_Slope_%')
    scaled_max_slope = apply_winsorize_and_scale('Max_Slope_%')
    
    df['Score_Joint_Strain'] = np.round((scaled_max_slope * 0.6) + (scaled_avg_slope * 0.4), 1)
    
    # 3. 종합 난이도 (Total Difficulty Score)
    df['Score_Total_Difficulty'] = np.round((df['Score_Endurance'] + df['Score_Joint_Strain']) / 2, 1)
    
    # 4. 설명 가능한 AI (XAI) 기초 태그 생성 (초보자용 텍스트 매핑)
    def generate_xai_tag(row):
        tags = []
        if row['Score_Endurance'] <= 30:
            tags.append("#산책같은코스")
        elif row['Score_Endurance'] >= 80:
            tags.append("#체력방전주의")
            
        if row['Score_Joint_Strain'] <= 30:
            tags.append("#관절보호")
        elif row['Score_Joint_Strain'] >= 80:
            tags.append("#무릎보호대필수")
            
        if row['Total_Distance_km'] < 5 and row['Score_Total_Difficulty'] > 60:
            tags.append("#짧고굵게")
            
        if not tags:
            tags.append("#무난한오운완")
            
        return " ".join(tags)

    df['PeakFit_Tags'] = df.apply(generate_xai_tag, axis=1)
    
    # 결과 저장
    out_path = os.path.join(data_dir, "PeakFit_Scored_DB.csv")
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    
    print("스코어링 완료!")
    print("산출된 통계 요약:")
    print(df[['Score_Endurance', 'Score_Joint_Strain', 'Score_Total_Difficulty']].describe().round(1))
    print(f"\n최종 결과물 저장 완료: {out_path}")

if __name__ == "__main__":
    calculate_peakfit_scores()
