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

# ثابت‌ها
MAX_LEVERAGE = 125
MIN_STOP_LOSS_PERCENTAGE = 0.01


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
        </style>
        """,
        unsafe_allow_html=True,
    )


def validate_inputs(capital: float, stop_loss_percentage: float, risk_levels: List[float], leverage: float) -> Optional[str]:
    if capital <= 0:
        return "سرمایه باید بیشتر از صفر باشد."
    if stop_loss_percentage <= 0:
        return "درصد حد ضرر باید بیشتر از صفر باشد."
    if stop_loss_percentage >= 100:
        return "درصد حد ضرر نمی‌تواند بیشتر یا مساوی ۱۰۰٪ باشد."
    if stop_loss_percentage < MIN_STOP_LOSS_PERCENTAGE:
        return f"حد ضرر نمی‌تواند کمتر از {MIN_STOP_LOSS_PERCENTAGE:.2f}% باشد."
    if leverage < 1:
        return "اهرم باید حداقل ۱ باشد."
    if leverage > MAX_LEVERAGE:
        return f"اهرم نمی‌تواند بیشتر از {MAX_LEVERAGE} باشد."
    if not risk_levels:
        return "لطفاً حداقل یک سطح ریسک وارد کنید."
    for risk in risk_levels:
        if risk <= 0:
            return "تمام سطوح ریسک باید بیشتر از صفر باشند."
        if risk >= 100:
            return "سطوح ریسک نمی‌توانند بیشتر یا مساوی ۱۰۰٪ باشند."
    return None


def parse_risk_levels(risk_input: str) -> Tuple[Optional[List[float]], Optional[str]]:
    if not risk_input or not risk_input.strip():
        return None, "لطفاً سطوح ریسک را وارد کنید."
    try:
        risk_input = arabic_numerals.to_decimal(risk_input)
        parts = re.split(r'[،,\s]+', risk_input)
        risk_levels = [float(p) for p in parts if p.strip()]
        return sorted(set(risk_levels)), None
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
        return None, "در معامله Long، حد ضرر باید پایین‌تر از قیمت ورود باشد."

    if trade_type == "Short" and stop <= entry:
        return None, "در معامله Short، حد ضرر باید بالاتر از قیمت ورود باشد."

    sl_percent = abs(entry - stop) / entry * 100
    return sl_percent, None


def calculate_risk_management(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float = 1.0
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:

    error = validate_inputs(capital, stop_loss_percentage, risk_levels, leverage)
    if error:
        return None, error

    try:
        capital_dec = Decimal(str(capital))
        sl_factor = Decimal(str(stop_loss_percentage)) / Decimal('100')
        leverage_dec = Decimal(str(leverage))

        data = {}
        for risk_percent in risk_levels:
            risk_factor = Decimal(str(risk_percent)) / Decimal('100')
            dollar_risk = float(capital_dec * risk_factor)
            position_size_dec = (capital_dec * risk_factor) / sl_factor
            position_size = float(position_size_dec)
            margin_required = float(position_size_dec / leverage_dec)

            col_name = f"{risk_percent}%"
            if leverage > 1:
                data[col_name] = [dollar_risk, position_size, margin_required]
            else:
                data[col_name] = [dollar_risk, position_size]

        index_labels = (
            ['💰 میزان ریسک', '📊 سایز پوزیشن', '💳 مارجین لازم (با اهرم)']
            if leverage > 1
            else ['💰 میزان ریسک', '📊 سایز پوزیشن']
        )

        df = pd.DataFrame(data, index=index_labels)
        return df, None

    except (InvalidOperation, ZeroDivisionError):
        return None, "خطا در محاسبات."


def main():
    inject_custom_css()

    st.title('🤖 ماشین حساب مدیریت سرمایه')
    st.markdown("محاسبه سایز پوزیشن با مدیریت ریسک حرفه‌ای")

    st.subheader("📈 تنظیمات معامله")

    trade_type = st.radio("نوع معامله", ["Long", "Short"], horizontal=True)
    use_price_sl = st.checkbox("🎯 محاسبه حد ضرر از روی قیمت")

    entry_price = stop_loss_price = None

    if use_price_sl:
        c1, c2 = st.columns(2)
        with c1:
            entry_price = st.number_input("قیمت ورود", min_value=0.0000001, format="%.6f")
        with c2:
            stop_loss_price = st.number_input("قیمت حد ضرر", min_value=0.0000001, format="%.6f")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        capital = st.number_input("سرمایه کل (USD)", min_value=0.01, value=1000.0)
    with col2:
        stop_loss_percentage = st.number_input("حد ضرر (%)", min_value=0.01, value=1.5)

    if use_price_sl:
        sl_percent, sl_error = calculate_sl_percentage(entry_price, stop_loss_price, trade_type)
        if sl_error:
            st.error(sl_error)
            return
        stop_loss_percentage = sl_percent
        st.success(f"حد ضرر محاسبه شد: {stop_loss_percentage:.2f}%")

    use_leverage = st.checkbox("⚡ استفاده از اهرم")
    leverage = 1.0
    if use_leverage:
        leverage = st.number_input("اهرم", min_value=1.0, max_value=MAX_LEVERAGE, value=10.0)

    risk_inputs_str = st.text_input("سطوح ریسک (%)", value="0.5,1,2")
    risk_levels, err = parse_risk_levels(risk_inputs_str)
    if err:
        st.error(err)
        return

    df, calc_err = calculate_risk_management(capital, stop_loss_percentage, risk_levels, leverage)
    if calc_err:
        st.error(calc_err)
        return

    st.dataframe(df.style.format("${:,.2f}"), use_container_width=True)


if __name__ == "__main__":
    main()
