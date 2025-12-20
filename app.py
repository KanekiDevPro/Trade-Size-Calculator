import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional
from decimal import Decimal, InvalidOperation
import re

st.set_page_config(
    page_title="ماشین حساب مدیریت سرمایه",
    page_icon="🤖",
    layout="centered"
)

# -------------------- ثابت‌ها --------------------
MAX_LEVERAGE = 125
MIN_STOP_LOSS_PERCENTAGE = 0.01

# -------------------- ابزار کمکی --------------------
def fa_to_en_numbers(text: str) -> str:
    fa_digits = "۰۱۲۳۴۵۶۷۸۹"
    en_digits = "0123456789"
    return text.translate(str.maketrans(fa_digits, en_digits))


@st.cache_data
def inject_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

        html, body, [class*="st-"] {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
            text-align: right;
        }

        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextInput"] input {
            direction: ltr !important;
            text-align: center !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# -------------------- اعتبارسنجی --------------------
def validate_inputs(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float
) -> Optional[str]:

    if capital <= 0:
        return "سرمایه باید بیشتر از صفر باشد."

    if stop_loss_percentage <= 0 or stop_loss_percentage >= 100:
        return "درصد حد ضرر باید بین ۰ و ۱۰۰ باشد."

    if stop_loss_percentage < MIN_STOP_LOSS_PERCENTAGE:
        return f"حد ضرر نمی‌تواند کمتر از {MIN_STOP_LOSS_PERCENTAGE:.2f}% باشد."

    if leverage < 1 or leverage > MAX_LEVERAGE:
        return f"اهرم باید بین ۱ تا {MAX_LEVERAGE} باشد."

    if not risk_levels:
        return "حداقل یک سطح ریسک وارد کنید."

    for r in risk_levels:
        if r <= 0 or r >= 100:
            return "سطوح ریسک باید بین ۰ و ۱۰۰ باشند."

    return None


def parse_risk_levels(risk_input: str) -> Tuple[Optional[List[float]], Optional[str]]:
    if not risk_input or not risk_input.strip():
        return None, "سطوح ریسک وارد نشده است."

    try:
        risk_input = fa_to_en_numbers(risk_input)
        parts = re.split(r"[،,\s]+", risk_input)
        risks = [float(p) for p in parts if p.strip()]
        return sorted(set(risks)), None
    except ValueError:
        return None, "فرمت سطوح ریسک نادرست است."


def calculate_sl_percentage(
    entry: float,
    stop: float,
    trade_type: str
) -> Tuple[Optional[float], Optional[str]]:

    if entry <= 0 or stop <= 0:
        return None, "قیمت‌ها باید بزرگ‌تر از صفر باشند."

    if trade_type == "Long" and stop >= entry:
        return None, "در Long حد ضرر باید پایین‌تر از ورود باشد."

    if trade_type == "Short" and stop <= entry:
        return None, "در Short حد ضرر باید بالاتر از ورود باشد."

    sl_percent = abs(entry - stop) / entry * 100
    return sl_percent, None


def calculate_risk_management(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:

    error = validate_inputs(capital, stop_loss_percentage, risk_levels, leverage)
    if error:
        return None, error

    try:
        capital_dec = Decimal(str(capital))
        sl_factor = Decimal(str(stop_loss_percentage)) / Decimal("100")
        leverage_dec = Decimal(str(leverage))

        data = {}
        for r in risk_levels:
            risk_factor = Decimal(str(r)) / Decimal("100")
            dollar_risk = float(capital_dec * risk_factor)
            position_size_dec = (capital_dec * risk_factor) / sl_factor
            margin = float(position_size_dec / leverage_dec)

            col = f"{r}%"
            data[col] = (
                [dollar_risk, float(position_size_dec), margin]
                if leverage > 1
                else [dollar_risk, float(position_size_dec)]
            )

        index = (
            ["💰 میزان ریسک", "📊 سایز پوزیشن", "💳 مارجین لازم"]
            if leverage > 1
            else ["💰 میزان ریسک", "📊 سایز پوزیشن"]
        )

        return pd.DataFrame(data, index=index), None

    except (InvalidOperation, ZeroDivisionError):
        return None, "خطا در محاسبات."


# -------------------- UI اصلی --------------------
def main():
    inject_custom_css()

    st.title("🤖 ماشین حساب مدیریت سرمایه")
    st.markdown("محاسبه حرفه‌ای سایز پوزیشن با مدیریت ریسک")

    st.subheader("📈 تنظیمات معامله")
    trade_type = st.radio("نوع معامله", ["Long", "Short"], horizontal=True)
    use_price_sl = st.checkbox("🎯 محاسبه حد ضرر از روی قیمت")

    entry_price = stop_price = None
    if use_price_sl:
        c1, c2 = st.columns(2)
        with c1:
            entry_price = st.number_input("قیمت ورود", min_value=0.0000001, format="%.6f")
        with c2:
            stop_price = st.number_input("قیمت حد ضرر", min_value=0.0000001, format="%.6f")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        capital = st.number_input("سرمایه کل (USD)", min_value=0.01, value=1000.0)
    with c2:
        stop_loss_percentage = st.number_input("حد ضرر (%)", min_value=0.01, value=1.5)

    if use_price_sl:
        sl, err = calculate_sl_percentage(entry_price, stop_price, trade_type)
        if err:
            st.error(err)
            return
        stop_loss_percentage = sl
        st.success(f"حد ضرر محاسبه شد: {stop_loss_percentage:.2f}%")

    use_leverage = st.checkbox("⚡ استفاده از اهرم")
    leverage = 1.0
    if use_leverage:
        leverage = st.number_input("اهرم", min_value=1.0, max_value=MAX_LEVERAGE, value=10.0)

    risk_input = st.text_input("سطوح ریسک (%)", value="0.5, 1, 2")
    risks, err = parse_risk_levels(risk_input)
    if err:
        st.error(err)
        return

    df, err = calculate_risk_management(capital, stop_loss_percentage, risks, leverage)
    if err:
        st.error(err)
        return

    st.subheader("📊 جدول سایز پوزیشن")
    st.dataframe(df.style.format("${:,.2f}"), use_container_width=True)


if __name__ == "__main__":
    main()
