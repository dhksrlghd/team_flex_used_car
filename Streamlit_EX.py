# #pip install streamlit pandas numpy plotly.express

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 페이지 레이아웃 설정
st.set_page_config(page_title="Used Car Value Analyzer", layout="wide")


@st.cache_data
def load_and_clean_data():
    """
    CSV 파일을 읽어오고 숫자 계산이 가능하도록 데이터를 정제하는 함수입니다.
    """
    raw_data = pd.read_csv('used_cars_bobaedream_final.csv')

    # [가격 정제] '만원' 글자를 지우고 숫자로 변환합니다.
    raw_data['price_numeric'] = raw_data['price'].str.replace('만원', '').str.replace(',', '').str.extract(
        '(\d+)').astype(float).fillna(0)

    # [이상치 제거] 가격 데이터 오류 필터링
    cleaned_data = raw_data[raw_data['price_numeric'] < 1000000].copy()

    # [주행거리 정제] 숫자 변환
    cleaned_data['mileage_numeric'] = cleaned_data['mileage'].str.replace('만km', '0000').str.replace('km',
                                                                                                     '').str.replace(
        ',', '').str.extract('(\d+)').astype(float).fillna(0)

    # [연식 정제] 숫자 변환
    cleaned_data['year_numeric'] = cleaned_data['year'].str[:2].astype(int).apply(
        lambda x: 2000 + x if x < 30 else 1900 + x)

    # [결측치 처리]
    cleaned_data['brand'] = cleaned_data['brand'].fillna("기타")
    cleaned_data['model_name'] = cleaned_data['model_name'].fillna("기타")
    cleaned_data['fuel'] = cleaned_data['fuel'].fillna("미분류")

    # --- 가성비 점수 계산 로직 ---
    # 가격, 주행거리, 연식을 0~1 사이로 정규화하여 '가성비 점수'를 산출합니다.
    # 낮은 가격(1), 낮은 주행거리(1), 최신 연식(1) 일수록 높은 점수를 갖게 설계합니다.

    df = cleaned_data.copy()
    # 가격이 0인 상담 매물 제외하고 계산
    calc_df = df[df['price_numeric'] > 0].copy()

    if not calc_df.empty:
        p_min, p_max = calc_df['price_numeric'].min(), calc_df['price_numeric'].max()
    else:
        p_min, p_max = 0, 1

    # 점수화: 낮을수록 좋은 지표(가격, 주행거리)는 역산하고, 높을수록 좋은 지표(연식)는 그대로 사용
    price_score = 1 - ((calc_df['price_numeric'] - p_min) / (p_max - p_min + 1))
    mile_score = 1 - ((calc_df['mileage_numeric'] - calc_df['mileage_numeric'].min()) / (
                calc_df['mileage_numeric'].max() - calc_df['mileage_numeric'].min() + 1))
    year_score = (calc_df['year_numeric'] - calc_df['year_numeric'].min()) / (
                calc_df['year_numeric'].max() - calc_df['year_numeric'].min() + 1)

    # 가성비 점수 산출 (가중치: 가격 50%, 주행거리 25%, 연식 25%)
    calc_df['value_score'] = (price_score * 0.5 + mile_score * 0.25 + year_score * 0.25) * 100

    # 원본 데이터와 결합
    df = df.merge(calc_df[['value_score']], left_index=True, right_index=True, how='left')
    df['value_score'] = df['value_score'].fillna(0)

    return df


def format_currency(amount):
    """
    숫자를 한국식 '억/만원' 단위 문자열로 변환해주는 함수입니다.
    """
    if amount >= 10000:
        return f"{int(amount // 10000)}억 {int(amount % 10000):,}만원"
    return f"{int(amount):,}만원"


# 데이터 로드
car_list = load_and_clean_data()

st.title("🚗 중고차 가성비 랭킹 및 가격 분석")

# --- 사이드바 검색 필터 ---
with st.sidebar:
    st.header("🔍 검색 및 필터")

    if 'brand_sel' not in st.session_state: st.session_state.brand_sel = []
    if 'model_sel' not in st.session_state: st.session_state.model_sel = []

    min_p = st.number_input("최소 금액 (만원)", value=int(car_list['price_numeric'].min()))
    max_p = st.number_input("최대 금액 (만원)", value=int(car_list['price_numeric'].max()))
    inc_consult = st.checkbox("0원 및 상담 가격 포함")


    def apply_price_logic(target_df):
        if inc_consult:
            return target_df[(target_df['price_numeric'].between(min_p, max_p)) | (target_df['price_numeric'] == 0)]
        return target_df[target_df['price_numeric'].between(min_p, max_p)]


    # 브랜드 필터 (실시간 카운트 포함)
    b_calc = apply_price_logic(car_list)
    b_counts = b_calc['brand'].value_counts()
    b_options = [f"{b} ({b_counts.get(b, 0)})" for b in sorted(car_list['brand'].unique())]
    b_ui = st.multiselect("차량 브랜드", options=b_options, key='brand_input')
    st.session_state.brand_sel = [val.split(" (")[0] for val in b_ui]

    # 모델 필터
    m_calc = b_calc.copy()
    if st.session_state.brand_sel: m_calc = m_calc[m_calc['brand'].isin(st.session_state.brand_sel)]
    m_counts = m_calc['model_name'].value_counts()
    m_options = [f"{m} ({m_counts.get(m, 0)})" for m in sorted(m_calc['model_name'].unique())]
    m_ui = st.multiselect("차량 모델", options=m_options, key='model_input')
    st.session_state.model_sel = [val.split(" (")[0] for val in m_ui]

# --- 필터링 및 분석 데이터 준비 ---
final_result = apply_price_logic(car_list)
if st.session_state.brand_sel: final_result = final_result[final_result['brand'].isin(st.session_state.brand_sel)]
if st.session_state.model_sel: final_result = final_result[final_result['model_name'].isin(st.session_state.model_sel)]

# 가성비 순위 매기기 (필터링된 결과 내에서)
final_result = final_result.sort_values(by='value_score', ascending=False)
final_result['가성비 순위'] = range(1, len(final_result) + 1)

# 시각화용 데이터: 선택된 것(Red) vs 전체(Gray)
analysis_df = car_list.copy()
analysis_df['is_selected'] = analysis_df.index.isin(final_result.index)
analysis_df['status'] = analysis_df['is_selected'].map({True: '선택한 조건의 매물', False: '기타 시장 매물'})
# 빨간색 점이 위로 오도록 정렬
analysis_df = analysis_df.sort_values('is_selected')

# --- 화면 출력 ---
col_stats, col_graph = st.columns([1, 2])

with col_stats:
    st.subheader("📌 검색 요약")
    if not final_result.empty:
        st.metric("필터링된 매물", f"{len(final_result)} 대")
        valid_prices = final_result[final_result['price_numeric'] > 0]['price_numeric']
        if not valid_prices.empty:
            st.metric("평균 시세", format_currency(int(valid_prices.mean())))

        st.write("---")
        st.success("🏆 가성비 Top 3 매물")
        for i, row in final_result.head(3).iterrows():
            st.write(f"**{row['가성비 순위']}위.** {row['brand']} {row['model_name']}")
            st.write(f"({row['price']} / {row['year']} / {row['mileage']})")
    else:
        st.info("왼쪽 필터에서 차량을 선택해주세요.")

with col_graph:
    st.subheader("📈 주행거리 대비 가격 분포")
    fig = px.scatter(
        analysis_df[analysis_df['price_numeric'] > 0],
        x='mileage_numeric',
        y='price_numeric',
        color='status',
        color_discrete_map={'선택한 조건의 매물': '#FF0000', '기타 시장 매물': '#E5ECF6'},
        hover_data=['brand', 'model_name', 'year', 'value_score'],
        labels={'mileage_numeric': '주행거리 (km)', 'price_numeric': '가격 (만원)', 'value_score': '가성비 점수'},
        template='plotly_white'
    )
    fig.update_traces(marker=dict(size=9, opacity=0.8, line=dict(width=0.5, color='DarkSlateGrey')))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 상세 리스트 (가성비 순위순 정렬) ---
st.subheader("📑 가성비 랭킹 상세 리스트")
if not final_result.empty:
    # 보여줄 컬럼들만 정의 (가성비 순위와 점수를 맨 앞으로)
    display_cols = ['가성비 순위', 'brand', 'model_name', 'price', 'year', 'mileage', 'fuel', 'region', 'link']

    # 정렬은 이미 위에서 value_score 기준으로 완료됨
    st.dataframe(
        final_result[display_cols],
        use_container_width=True,
        height=500
    )
else:
    st.warning("조건에 맞는 매물이 없습니다.")

# streamlit run Streamlit_EX.py