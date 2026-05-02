# PeakFit 데이터 개요 리포트 (Data Overview Report)

본 문서는 **PeakFit** 프로젝트 팀원들이 데이터 구조를 쉽게 파악하고 원활하게 협업할 수 있도록 돕기 위해 작성된 '데이터 통합 관리 가이드'입니다. 수집된 원본(Raw) 데이터와 파이썬 스크립트로 가공된(Processed) 데이터가 엄격하게 분리되어 관리됩니다.

---

## 📂 1. 데이터 폴더 구조 (Data Directory Structure)

모든 데이터는 `tracking-pjt/data/` 경로 하위에 목적별로 분리되어 저장됩니다.

```text
tracking-pjt/
└── data/
    ├── raw/              # (원본 데이터) 외부에서 수집한 원본 데이터 보관 (수정 금지)
    │   ├── 100mountains_seasonal.csv
    │   ├── public-data-api.md / .local
    │   ├── 100대명산/       # 100개 산의 원본 GPX 파일들이 담긴 폴더
    │   └── team-share/      # 다른 팀원이 공유해준 데이터 보관 폴더 (맛집, 통합 마스터 등)
    │
    └── processed/        # (가공 데이터) 파이썬 스크립트로 정제/추출/병합된 최종 데이터
        ├── gpx_analysis_results.csv
        ├── PeakFit_Master_DB.csv 
        ├── PeakFit_Scored_DB.csv (체력/관절 난이도 지수 추가본)
        ├── PeakFit_Clustered_DB.csv (페르소나 군집화 추가본)
        └── PeakFit_Final_Curation_DB.csv (🌟최종 하이브리드 추천 마스터🌟)
```

---

## 📝 2. 원본 데이터 (Raw Data) 설명

데이터의 출처와 가공 전 최초 형태를 보관하는 곳입니다. **절대 원본 파일을 직접 수정하지 마세요.**

### `100mountains_seasonal.csv`
*   **출처**: 산림청 및 공공데이터 포털 기반 자체 수집/정리본
*   **내용**: 산 이름, 높이, 지역, 계절별 추천 여부(봄/여름/가을/겨울 추천), 그리고 정성적인 난이도(★) 및 특징 메모가 담긴 베이스 데이터입니다.
*   **특징**: 산 이름 뒤에 괄호로 지역명이 붙어있는 경우가 있어, 향후 데이터 조인(Join) 시 괄호를 제거하는 전처리가 필요합니다.
*   **비고**: 예진님이 올려주신 자료임. 어떻게 나온건지 확인 필요

### `100대명산/` (GPX 폴더)
*   **내용**: 산별로 1개~수십 개의 등산로 궤적(GPX) 파일이 들어있는 디렉토리입니다.
*   **특징**: 위도(Lat), 경도(Lon), 고도(Ele), 시간(Time) 포인트 데이터로 이루어져 있으며 노면 정보(흙길/계단 등)는 포함되어 있지 않습니다.
*   **출처**: https://komount.or.kr/html/index.do?html=public_data2 
3. 산림청 100대명산 (GPX) → 핵심 산 목록 + 지도 좌표

### `public-data-api.md`
*   **내용**: 노면 정보 및 맛집 등 추가 POI 데이터를 불러오기 위한 공공데이터 API 인증 키 및 엔드포인트 정보 명세서입니다.
*   **출처**: https://komount.or.kr/html/index.do?html=public_data2
9. 한국등산트레킹지원센터_100대명산 숲길입구노면정보 서비스
10. 100대명산 숲길노면 정보 조회
14. 100대명산 관광POI 정보 조회
15. 한국등산트레킹지원센터_100대명산 교통시설POI정보 서비스

### `team-share/` (팀원 공유 데이터 폴더)
*   **`100mountains_master.csv`**: 공공데이터 API 9종을 통합하여 만든 319행 규모의 산 단위 마스터 데이터 (계단 수, 위험 요인, 볼거리 점수 등 포함).
*   **`mountain_places_v3.csv`**: 카카오맵/네이버블로그 API 기반 전국 100대 산 반경 3km 이내 맛집/카페 2,740건 데이터 (맛집점수 산정 완료).
*   **비고**: 맛집 데이터는 정상 기준 좌표이므로, 실제 추천 시에는 GPX의 하산 지점 좌표와 다시 계산해야 합니다.

---

## 📊 3. 가공 데이터 (Processed Data) 설명

파이썬 스크립트(`tracking-pjt/src/`)에 의해 자동 추출, 연산, 병합되어 생성된 데이터입니다. 모델링 및 대시보드 시각화에 **직접적으로 사용되는 최종본**입니다.

### `gpx_analysis_results.csv`
*   **생성 스크립트**: `src/analyze_gpx.py`
*   **내용**: 600여 개의 원본 GPX 파일들을 병렬 처리하여 입문자 난이도 측정에 필수적인 '정량 지표'를 추출한 결과물입니다.
*   **주요 컬럼**: 
    *   `Total_Distance_km`: 3D 보정 총 이동 거리
    *   `Elevation_Gain_m`: 누적 획득 고도 (체력 소모량 측정 핵심)
    *   `Average_Slope_%`, `Max_Slope_%`: 평균/최대 경사도
    *   `Start_Lat`, `Start_Lon`, `End_Lat`, `End_Lon`: **(중요) 맛집 매핑을 위한 시작/하산 지점 위경도 좌표**

### `mountain_surface_api_results.csv` (예정)
*   **생성 스크립트**: `src/collect_surface_api.py` (실행 대기 중)
*   **내용**: 공공데이터 API를 호출하여 받아온 산별 노면 비율(암릉, 계단, 흙길) 정량 정보입니다.

### `PeakFit_Master_DB.csv` ~ `PeakFit_Final_Curation_DB.csv` (단계별 큐레이션 DB)
*   **생성 스크립트**: `src/merge_master_db.py` ➡️ `src/calculate_peakfit_score.py` ➡️ `src/clustering_peakfit.py` ➡️ `src/spatial_join_curation.py`
*   **내용**: GPX 정량 지표와 API 정성 지표를 통합한 뒤, 다음 3단계 분석을 거친 데이터들입니다.
    1.  **Scored_DB**: 1~100점 척도의 `체력 소모도` 및 `관절 무리도` 산출 추가.
    2.  **Clustered_DB**: K-Means 알고리즘 기반 3가지 유저 페르소나 매핑 추가.
    3.  **Final_Curation_DB (🌟최종 완성본🌟)**: 팀원 맛집 데이터와 하산 지점(End_Lat/Lon) 간의 실제 거리를 계산해 `미식 지수` 및 XAI 확장 태그를 결합한 최종 마스터 테이블입니다.
*   **활용**: 대시보드의 메인 데이터셋으로 활용되어 맞춤형 필터링, 정렬, 지도 시각화를 담당합니다.

---

## 💡 4. 팀원 협업 규칙 (Action Items)

1.  **맛집/POI 데이터 병합 시**: 다른 팀원이 수집한 카카오/네이버 맛집 데이터 역시 원본은 `raw/`에 보관하고, `PeakFit_Master_DB.csv`의 `End_Lat`, `End_Lon` (하산 지점 좌표)를 기준으로 **공간 조인(Spatial Join)**을 수행하는 스크립트를 작성하여 `processed/`에 병합본을 저장해 주세요.
2.  **데이터 업데이트 시**: 원본(Raw)에 변동이 생길 경우, 엑셀/CSV를 직접 수정하지 말고 `src/merge_master_db.py` 스크립트를 재실행하여 자동으로 마스터 DB가 최신화되게 유지해 주세요.
3.  **로드맵 확인**: 데이터 전략 진행 상황은 항상 `docs/plan/data_strategy_roadmap.md` 파일 하단을 참고해 주세요.

---

## 💻 5. 최종 시각화 결과물 (Outputs)

가공된 `PeakFit_Final_Curation_DB.csv`를 기반으로 제작된 인터랙티브 대시보드 프로토타입입니다. 다른 프론트엔드 팀원이 이 로직과 UI를 가져가 최종 서비스에 이식할 수 있습니다.

*   **실행 파일**: `tracking-pjt/src/dashboard_app.py`
*   **실행 방법**: 터미널에서 `uv run streamlit run tracking-pjt/src/dashboard_app.py` 실행
*   **주요 기능**:
    *   **동적 필터링**: 체력/무릎 부담 슬라이더 조절 및 페르소나, 맛집 여부 실시간 선택.
    *   **XAI(설명 가능한 AI) 태그**: `#하산후맛집천국`, `#계단지옥` 등 코스의 특징을 직관적인 UI 태그로 렌더링.
    *   **공간 조인(Spatial Join) 연동**: 추천된 코스의 '실제 하산 지점 20분 거리 내 찐맛집'을 실시간 벡터 연산으로 찾아내어 리스트업 및 카카오맵 연동.
    *   **지도 시각화**: 하산 지점 좌표를 지도에 마커로 자동 표시.
