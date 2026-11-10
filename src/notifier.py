import os
import datetime
import requests
from typing import Dict, Any, List


def format_daily_briefing(
    score_data: Dict[str, Any],
    alerts: List[Dict[str, Any]],
    dashboard_url: str = None
) -> str:
    """스마트폰으로 받아볼 텔레그램 일일 브리핑 메시지 포맷팅 (오전/오후 시간대 반영)"""
    date = score_data.get("date")
    wwri = score_data.get("wwri_score")
    level = score_data.get("risk_level")
    change_7d = score_data.get("score_change_7d", 0.0)

    # 한국 시간(UTC+9) 기준 시간대 반영
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    period_str = "오전 브리핑" if kst_now.hour < 13 else "오후 브리핑"
    time_str = kst_now.strftime("%H:%M")

    # 이모지 매핑
    level_icons = {
        "안정": "🟢",
        "관심": "🟡",
        "주의": "🟠",
        "경계": "🔴",
        "심각": "🚨"
    }
    icon = level_icons.get(level, "⚪")

    msg = f"<b>[WWRI 전쟁 위험 모니터 - {period_str}]</b> {icon}\n"
    msg += f"📅 <b>일시:</b> {date} {time_str} (KST)\n"
    msg += f"📊 <b>종합 위험지수:</b> <b>{wwri}점</b> ({level})\n"
    msg += f"📈 <b>지난주 대비:</b> {change_7d:+.1f}점\n\n"

    # 세부 지표
    msg += "<b>[세부 영역별 평가]</b>\n"
    msg += f"• 무력충돌(30%): {score_data.get('conflict_score', 0):.1f}점\n"
    msg += f"• 군사동원(25%): {score_data.get('military_score', 0):.1f}점\n"
    msg += f"• 지정학(20%): {score_data.get('geopolitical_score', 0):.1f}점\n"
    msg += f"• 금융·에너지(15%): {score_data.get('market_score', 0):.1f}점\n"
    msg += f"• 방위산업(10%): {score_data.get('defense_score', 0):.1f}점\n\n"

    # 경고 내역
    if alerts:
        msg += "<b>⚠️ 감지된 주요 이상 신호:</b>\n"
        for a in alerts:
            msg += f"• [{a.get('alert_level')}] {a.get('title')}\n"
            triggers = a.get("triggers", "")
            if triggers:
                for t in triggers.split("\n")[:3]:
                    msg += f"  - {t}\n"
        msg += "\n"
    else:
        msg += "✅ 감지된 특이 이상 징후 없음 (평온 유지)\n\n"

    if dashboard_url:
        msg += f"🌐 <a href='{dashboard_url}'>실시간 대시보드 바로가기</a>"

    return msg


def send_telegram_alert(
    message: str,
    bot_token: str = None,
    chat_id: str = None
) -> bool:
    """
    텔레그램 봇으로 메시지를 발송합니다.
    토큰이 설정되지 않은 경우 콘솔에 모의 발송(Dry-run) 결과를 출력합니다.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not cid:
        print("[Notifier Dry-Run] Telegram Bot Token or Chat ID not configured.")
        print("------- [Pre-view Message] -------")
        print(message.replace("<b>", "").replace("</b>", "").replace("<a href='", "").replace("'>", " - ").replace("</a>", ""))
        print("----------------------------------")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": cid,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram alert sent successfully.")
            return True
        else:
            print(f"Failed to send Telegram alert: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")
        return False
