import os
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="WWRI - 세계 전쟁 위험 모니터",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DB 경로 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "data", "wwri.db")


def load_data():
    if not os.path.exists(DB_PATH):
        return None, None, None, None, None

    conn = sqlite3.connect(DB_PATH)
    try:
        df_scores = pd.read_sql_query("SELECT * FROM risk_scores ORDER BY date ASC", conn)
        df_alerts = pd.read_sql_query("SELECT * FROM alerts ORDER BY id DESC LIMIT 10", conn)
        df_market = pd.read_sql_query("SELECT * FROM market_data WHERE date = (SELECT MAX(date) FROM market_data)", conn)
        df_conflict = pd.read_sql_query("SELECT * FROM conflict_data WHERE date = (SELECT MAX(date) FROM conflict_data)", conn)
        df_news = pd.read_sql_query("SELECT * FROM news_events ORDER BY id DESC LIMIT 15", conn)
    except Exception:
        df_scores, df_alerts, df_market, df_conflict, df_news = None, None, None, None, None
    finally:
        conn.close()

    return df_scores, df_alerts, df_market, df_conflict, df_news


# --- UI 시작 ---
st.title("🌐 WORLD WAR RISK MONITOR")
st.caption("매일 같은 기준으로 데이터를 축적하여 장기적 위험 변화를 추적·감지하는 시스템")

df_scores, df_alerts, df_market, df_conflict, df_news = load_data()

if df_scores is None or df_scores.empty:
    st.warning("⚠️ 아직 축적된 데이터가 없습니다. 오른쪽 사이드바에서 수집 파이프라인을 실행해 주세요.")
    if st.sidebar.button("🚀 지금 데이터 수집 파이프라인 실행"):
        from src.main import run_pipeline
        with st.spinner("데이터를 수집하고 WWRI 위험도를 계산 중입니다..."):
            run_pipeline()
        st.success("데이터 수집 완료! 페이지를 새로고침합니다.")
        st.rerun()
    st.stop()

# 최신 점수 데이터
latest = df_scores.iloc[-1]
score = latest["wwri_score"]
level = latest["risk_level"]
change_7d = latest.get("score_change_7d", 0.0)
change_30d = latest.get("score_change_30d", 0.0)

# 1. 상단 핵심 요약 메트릭
col1, col2, col3, col4 = st.columns(4)

level_colors = {
    "안정": "#28a745",
    "관심": "#ffc107",
    "주의": "#fd7e14",
    "경계": "#dc3545",
    "심각": "#6f42c1"
}
badge_color = level_colors.get(level, "#6c757d")

with col1:
    st.metric(
        label="🛡️ 종합 전쟁 위험지수 (WWRI)",
        value=f"{score:.1f} 점",
        delta=f"{change_7d:+.1f} 점 (7일 전 대비)"
    )

with col2:
    st.markdown(f"""
    <div style="background-color: {badge_color}22; border-left: 5px solid {badge_color}; padding: 12px; border-radius: 5px;">
        <span style="font-size: 14px; color: #888;">현재 위험 판정</span><br>
        <b style="font-size: 24px; color: {badge_color};">{level} 단계</b>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.metric(
        label="📅 최근 갱신 일자",
        value=latest["date"],
        delta=f"{change_30d:+.1f} 점 (30일 전 대비)"
    )

with col4:
    recent_alert_count = len(df_alerts) if df_alerts is not None else 0
    st.metric(
        label="⚠️ 최근 감지된 경고",
        value=f"{recent_alert_count} 건"
    )

st.divider()

# 2. 메인 차트 및 지역별 현황 (2열 배치)
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📈 최근 30일 위험지수 추세선 (WWRI Trend)")
    fig_trend = px.line(
        df_scores,
        x="date",
        y="wwri_score",
        markers=True,
        labels={"date": "날짜", "wwri_score": "위험 점수"},
        title="세계 전쟁 위험 종합지수 일별 변화"
    )
    # 위험 구간 기준선 추가
    fig_trend.add_hline(y=40, line_dash="dot", line_color="#fd7e14", annotation_text="주의(40)")
    fig_trend.add_hline(y=60, line_dash="dash", line_color="#dc3545", annotation_text="경계(60)")
    fig_trend.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_trend, use_container_width=True)

with c_right:
    st.subheader("📍 관찰 지역별 상태")
    if df_conflict is not None and not df_conflict.empty:
        st.dataframe(
            df_conflict[["region", "conflict_level", "incident_count", "notes"]].rename(
                columns={"region": "지역", "conflict_level": "위험 상태", "incident_count": "보도/충돌수", "notes": "세부"}
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("지역별 데이터 준비 중")

    st.subheader("⚖️ 5대 세부 영역별 점수")
    categories = ["무력충돌(30%)", "군사동원(25%)", "지정학(20%)", "금융시장(15%)", "방위산업(10%)"]
    scores = [
        latest.get("conflict_score", 0),
        latest.get("military_score", 0),
        latest.get("geopolitical_score", 0),
        latest.get("market_score", 0),
        latest.get("defense_score", 0)
    ]
    fig_bar = go.Figure(go.Bar(
        x=scores,
        y=categories,
        orientation='h',
        marker=dict(color=['#e63946', '#f4a261', '#e76f51', '#2a9d8f', '#264653'])
    ))
    fig_bar.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# 3. 시장 지표 & 최근 경고
c_market, c_alert = st.columns(2)

with c_market:
    st.subheader("📊 주요 금융·원자재 및 방산 지표")
    if df_market is not None and not df_market.empty:
        st.dataframe(
            df_market[["name", "price", "change_1d", "change_7d", "change_30d"]].rename(
                columns={
                    "name": "항목", "price": "현재가",
                    "change_1d": "1일 변동(%)", "change_7d": "7일 변동(%)", "change_30d": "30일 변동(%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("시장 데이터 준비 중")

with c_alert:
    st.subheader("🔔 감지된 경고 및 이상 신호")
    if df_alerts is not None and not df_alerts.empty:
        for _, alert in df_alerts.iterrows():
            with st.expander(f"[{alert['alert_level']}] {alert['title']} ({alert['date']})", expanded=True):
                st.write(alert.get("description", ""))
                st.markdown(f"```\n{alert.get('triggers', '')}\n```")
    else:
        st.success("최근 발생한 이상 신호가 없습니다. 평온한 상태입니다.")

# 4. 수집된 주요 뉴스
st.divider()
st.subheader("📰 최근 감지된 군사·분쟁 주요 뉴스")
if df_news is not None and not df_news.empty:
    for _, item in df_news.iterrows():
        st.markdown(f"- **[{item['source']}]** [{item['title']}]({item['link']}) ({item['date']}) — *태그: {item.get('keywords', '')}*")
