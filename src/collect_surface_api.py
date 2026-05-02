import os
import requests
import pandas as pd
import time
from urllib.parse import urlencode, quote_plus

# -------------------------------------------------------------
# [설정] API 인증키 및 기본 정보
# `tracking-pjt/data/public-data-api.md`에 기재된 일반 인증 키
# -------------------------------------------------------------
API_KEY = "b7297c0c5f33c273a92212f19d53e1072d777c2541cd627a4676afc16919538c"

# 주의: 공공데이터포털(data.go.kr) 또는 한국등산트레킹지원센터 제공 정확한 Endpoint URL로 변경 필요.
# 예시 URL (가상): "http://apis.data.go.kr/100mountains/surfaceInfo/getSurfaceList"
API_ENDPOINT = "http://apis.data.go.kr/100mountains/surfaceInfo/getSurfaceList" 

def fetch_mountain_surface_data(mountain_name):
    """
    특정 산 이름에 대한 숲길 노면 정보를 API로 요청합니다.
    """
    queryParams = '?' + urlencode({ 
        quote_plus('ServiceKey'): API_KEY, 
        quote_plus('mntnNm'): mountain_name, # 산 이름 파라미터 (명세서에 따라 다를 수 있음)
        quote_plus('pageNo'): '1', 
        quote_plus('numOfRows'): '100',
        quote_plus('type'): 'json' # 응답 포맷을 JSON으로 요청
    })
    
    url = API_ENDPOINT + queryParams
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # JSON 응답 파싱 (명세서 구조에 따라 수정 필요)
        data = response.json()
        
        # 예: data['response']['body']['items'] 형태를 띤다고 가정
        items = data.get('response', {}).get('body', {}).get('items', [])
        return items
    
    except Exception as e:
        print(f"[{mountain_name}] 데이터 수집 실패: {e}")
        return []

def main():
    print("=== 한국등산트레킹지원센터_100대명산 숲길노면 정보 수집 시작 ===")
    
    # 앞서 분석된 GPX 파일에서 대상 산 목록을 가져옵니다.
    gpx_result_path = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\processed\gpx_analysis_results.csv"
    if not os.path.exists(gpx_result_path):
        print("GPX 분석 결과 파일을 찾을 수 없습니다. (analyze_gpx.py 먼저 실행 필요)")
        return
        
    df_gpx = pd.read_csv(gpx_result_path)
    mountains = df_gpx['Mountain'].unique()
    
    print(f"총 {len(mountains)}개 산에 대한 노면 정보를 요청합니다.")
    
    all_surface_data = []
    
    for mnt in mountains:
        print(f"'{mnt}' 데이터 요청 중...")
        items = fetch_mountain_surface_data(mnt)
        
        # 각 응답 아이템에 원래 산 이름을 매핑
        for item in items:
            item['Target_Mountain'] = mnt
            all_surface_data.append(item)
            
        # API 과부하 방지를 위한 딜레이
        time.sleep(0.5) 
        
    if all_surface_data:
        df_surface = pd.DataFrame(all_surface_data)
        out_path = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\processed\mountain_surface_api_results.csv"
        df_surface.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"\n데이터 수집 완료! 총 {len(df_surface)}건의 노면 데이터가 저장되었습니다.")
        print(f"저장 경로: {out_path}")
    else:
        print("\n수집된 데이터가 없습니다. Endpoint URL, 파라미터명, 또는 API 인증키를 확인해주세요.")

if __name__ == "__main__":
    main()
