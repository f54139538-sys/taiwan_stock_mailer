import streamlit as st
import yfinance as yf
import google.generativeai as genai
from dotenv import load_dotenv
from email.message import EmailMessage
import os
import smtplib


st.set_page_config(page_title="台股分析與寄送小幫手", layout="wide")
load_dotenv(override=True)

if "email_body" not in st.session_state:
    st.session_state.email_body = ""

st.title("台股分析與寄送小幫手")

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.header("查詢區")
stock_code = st.text_input("請輸入台股代碼", placeholder="例如：2330")

SYSTEM_PROMPT = """
你是一位精通台灣股市的資深分析師。請根據我提供的股票名稱與今日價格資訊，產出一份簡潔的金融報告書。
報告必須包含：
1. 該公司的產業地位簡介（一句話）。
2. 今日價格的市場心理面簡評。
3. 給新手的風險提示（一句話）。
請使用繁體中文，語氣專業但白話，長度控制在 300 字以內，不要使用 Markdown 表格。
"""

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
GEMINI_TIMEOUT_SECONDS = 20


@st.cache_data(ttl=600)
def get_tw_stock_data(code):
    symbols = [f"{code}.TW", f"{code}.TWO"]
    errors = []

    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="5d")

            if not data.empty:
                try:
                    name = stock.info.get("longName", symbol)
                except Exception:
                    name = symbol

                return symbol, name, data, None
        except Exception as e:
            errors.append(str(e))

    error_text = "；".join(errors)
    if "RateLimit" in error_text or "Too Many Requests" in error_text:
        return None, None, None, "Yahoo Finance 暫時限制查詢次數，請等幾分鐘後再試"

    return None, None, None, "查無資料，請確認股票代碼是否正確"


def send_email(to_email, subject, body):
    gmail_user = (os.getenv("GMAIL_USER") or "").strip()
    gmail_password = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()

    if not gmail_user or not gmail_password:
        return False, "找不到 GMAIL_USER 或 GMAIL_APP_PASSWORD，請先設定 .env 檔案"

    if len(gmail_password) != 16:
        return False, "GMAIL_APP_PASSWORD 看起來不是 Google 產生的 16 碼應用程式密碼"

    msg = EmailMessage()
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail 登入失敗：請使用 Google 產生的 16 碼「應用程式密碼」，不要使用 Gmail 登入密碼"

    return True, "寄送成功"


if st.button("查詢當日股價"):
    if not stock_code:
        st.warning("請先輸入台股代碼")
    else:
        symbol, name, data, error_message = get_tw_stock_data(stock_code)

        if data is None:
            st.error(error_message)
        else:
            latest = data.iloc[-1]
            st.success(f"查詢成功：{name}（{symbol}）")
            st.write(f"開盤價：{latest['Open']:.2f}")
            st.write(f"最高價：{latest['High']:.2f}")
            st.write(f"最低價：{latest['Low']:.2f}")
            st.write(f"收盤價：{latest['Close']:.2f}")
            st.write(f"成交量：{int(latest['Volume']):,}")

            st.session_state.stock_name = name
            st.session_state.stock_symbol = symbol
            st.session_state.stock_price_text = f"""
股票名稱：{name}
股票代號：{symbol}
開盤價：{latest['Open']:.2f}
最高價：{latest['High']:.2f}
最低價：{latest['Low']:.2f}
收盤價：{latest['Close']:.2f}
成交量：{int(latest['Volume']):,}
"""

st.header("分析區")

if st.button("生成分析報告"):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("找不到 GEMINI_API_KEY，請先設定 .env 檔案")
    elif "stock_price_text" not in st.session_state:
        st.warning("請先查詢當日股價")
    else:
        try:
            genai.configure(api_key=api_key)
            response = None
            errors = []

            with st.spinner("正在生成分析報告，請稍候..."):
                for model_name in GEMINI_MODELS:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(
                            f"{SYSTEM_PROMPT}\n\n{st.session_state.stock_price_text}",
                            request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
                        )
                        break
                    except Exception as e:
                        errors.append(f"{model_name}: {e}")

            if response is None:
                raise RuntimeError("目前設定的 Gemini 模型都無法使用：" + " | ".join(errors))

            st.session_state.report = response.text
            st.session_state.email_body = response.text
        except Exception as e:
            st.error(f"生成分析報告失敗：{e}")

if "report" in st.session_state:
    st.subheader("分析報告")
    st.write(st.session_state.report)

st.header("寄送區")

recipient_gmail = st.text_input("收件者 Gmail")
email_subject = st.text_input("信件主旨", value="台股分析報告")
email_body = st.text_area("信件內文（可編輯）", key="email_body", height=260)

if st.button("寄出報告"):
    if not email_body.strip():
        st.warning("請先生成分析報告，或填寫信件內文")
    elif not recipient_gmail or not email_subject:
        st.warning("請填寫收件者 Gmail 與信件主旨")
    elif not recipient_gmail.strip().lower().endswith("@gmail.com"):
        st.warning("收件者 Gmail 格式可能有誤，請確認結尾是 @gmail.com")
    else:
        try:
            ok, message = send_email(recipient_gmail, email_subject, email_body)

            if ok:
                st.success(message)
            else:
                st.error(message)
        except Exception as e:
            st.error(f"寄送失敗：{e}")
