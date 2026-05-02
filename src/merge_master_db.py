import pandas as pd
import os

def create_master_db():
    print("=== 데이터 병합(Join) 및 Master DB 생성 시작 ===")
    
    data_dir = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data"
    seasonal_csv = os.path.join(data_dir, "raw", "100mountains_seasonal.csv")
    gpx_csv = os.path.join(data_dir, "processed", "gpx_analysis_results.csv")
    api_csv = os.path.join(data_dir, "processed", "mountain_surface_api_results.csv") # 향후 수집될 API 데이터
    
    # 1. 원본 데이터 로드
    try:
        df_seasonal = pd.read_csv(seasonal_csv)
        df_gpx = pd.read_csv(gpx_csv)
    except FileNotFoundError as e:
        print(f"필수 파일을 찾을 수 없습니다: {e}")
        return
        
    # 2. Join Key 표준화 작업
    # df_seasonal 의 '산이름' 에는 '가야산(충남)', '가야산(경남)' 처럼 지역이 붙어있는 경우가 있음.
    # df_gpx 의 'Mountain' 에는 '가야산' 처럼 괄호가 없는 경우가 섞여 있음.
    # 이를 통합하기 위해 모든 산 이름을 정제하여 'join_key' 컬럼을 생성.
    def clean_mountain_name(name):
        if pd.isna(name): return ""
        # 괄호 안의 내용을 제외한 순수 산 이름만 추출 (필요 시 더 정교한 매핑 필요)
        clean_name = str(name).split('(')[0].strip()
        return clean_name
        
    df_seasonal['join_key'] = df_seasonal['산이름'].apply(clean_mountain_name)
    df_gpx['join_key'] = df_gpx['Mountain'].apply(clean_mountain_name)
    
    # 3. 데이터 병합 (GPX 데이터를 기준으로 Seasonal 데이터를 Left Join)
    # 한 산에 여러 GPX(코스)가 있으므로 1:N 조인 형태가 됨.
    df_master = pd.merge(df_gpx, df_seasonal, on='join_key', how='left')
    
    # 4. API 노면 데이터가 존재할 경우 추가 병합 시도
    if os.path.exists(api_csv):
        print("API 노면 데이터가 발견되어 병합을 시도합니다.")
        df_api = pd.read_csv(api_csv)
        if 'Target_Mountain' in df_api.columns:
            df_api['join_key'] = df_api['Target_Mountain'].apply(clean_mountain_name)
            # 여기서는 산 이름 단위로만 병합(단순화)
            df_api_agg = df_api.groupby('join_key').first().reset_index()
            df_master = pd.merge(df_master, df_api_agg, on='join_key', how='left')
    else:
        print("API 노면 데이터 파일이 아직 없습니다. GPX + Seasonal 데이터만 병합합니다.")
        
    # 5. 결과 저장
    out_path = os.path.join(data_dir, "processed", "PeakFit_Master_DB.csv")
    df_master.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Master DB 생성 완료! 저장 경로: {out_path}")
    print(f"총 {len(df_master)}개의 코스(GPX) 데이터가 통합되었습니다.")

if __name__ == "__main__":
    create_master_db()
