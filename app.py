import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional
from decimal import Decimal, InvalidOperation

st.set_page_config(
    page_title="ماشین حساب مدیریت سرمایه",
    page_icon="🤖",
    layout="centered"
)

# -------------------- CSS --------------------
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

        h1, h2, h3, h4 {
            text-align: right !important;
        }

        .stMarkdown, .stText, div[data-testid="stAlert"] {
            direction: rtl !important;
            text-align: right !important;
        }

        /* ---------- DataFrame RTL/LTR FIX ---------- */
        div[data-testid="stDataFrame"] {
            direction: ltr !important;
        }

        div[data-testid="stDataFrame"] table {
            direction: ltr !important;
            border-collapse: collapse !important;
        }

        div[data-testid="stDataFrame"] table thead th {
            text-align: center !important;
            background-color: #f0f2f6 !important;
            font-weight: 600 !important;
            padding: 12px 8px !important;
            white-space: nowrap;
        }

        div[data-testid="stDataFrame"] table tbody th {
            text-align: left !important;
            font-weight: 600 !important;
            white-space: nowrap;
            unicode-bidi: plaintext;
        }

        div[data-testid="stDataFrame"] table tbody td {
            text-align: right !important;
            padding: 10px 8px !important;
            white-space: nowrap;
            unicode-bidi: plaintext;
        }

        div[data-testid="stNumberInput"] input {
            direction: ltr !important;
            text-align: center !important;
        }

        div[data-testid="stTextInput"] input {
            direction: ltr !important;
            text-align: left !important;
        }

        div[data-testid="stMetric"] {
            direction: rtl !important;
            text-align: right !important;
        }

        div[data-testid="stCheckbox"] {
            direction: rtl !important;
            text-align: right !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# -------------------- Validation --------------------
def validate_inputs(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float
) -> Optional[str]:

    if capital <= 0:
        return "سرمایه باید بیشتر از صفر باشد."

    if stop_loss_percentage < 0.01:
        return "حد ضرر نمی‌تواند کمتر از ۰.۰۱٪ باشد."

    if stop_loss_percentage >= 100:
        return "درصد حد ضرر نمی‌تواند بیشتر یا مساوی ۱۰۰٪ باشد."

    if leverage < 1 or leverage > 125:
        return "اهرم باید بین ۱ تا ۱۲۵ باشد."

    if not risk_levels:
        return "لطفاً حداقل یک سطح ریسک وارد کنید."

    for r in risk_levels:
        if r <= 0 or r >= 100:
            return "سطوح ریسک باید بین ۰ و ۱۰۰ باشند."

    return None

# -------------------- Parse Risk --------------------
def parse_risk_levels(risk_input: str) -> Tuple[Optional[List[float]], Optional[str]]:
    if not risk_input or not risk_input.strip():
        return None, "لطفاً سطوح ریسک را وارد کنید."

    try:
        parts = risk_input.replace('،', ',').split(',')
        risks = [float(p.strip()) for p in parts if p.strip()]
        return sorted(set(risks)), None
    except ValueError:
        return None, "فرمت سطوح ریسک نادرست است."

# -------------------- Core Logic --------------------
def create_risk_management_table(
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
            margin_required = float(position_size_dec / leverage_dec)

            col = f"{r}%"
            data[col] = (
                [dollar_risk, float(position_size_dec), margin_required]
                if leverage > 1
                else [dollar_risk, float(position_size_dec)]
            )

        index = (
            ["میزان ریسک ($)", "سایز پوزیشن ($)", "مارجین لازم ($)"]
            if leverage > 1
            else ["میزان ریسک ($)", "سایز پوزیشن ($)"]
        )

        return pd.DataFrame(data, index=index), None

    except (InvalidOperation, ZeroDivisionError):
        return None, "خطا در محاسبات."

# -------------------- UI --------------------
def main():
    inject_custom_css()

    st.title("🤖 ماشین حساب مدیریت سرمایه")
    st.markdown("محاسبه دقیق **سایز پوزیشن** بر اساس سرمایه، ریسک و حد ضرر")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        capital = st.number_input("سرمایه کل (USD)", min_value=0.01, value=1000.0, step=100.0)
    with c2:
        stop_loss_percentage = st.number_input(
            "حد ضرر معامله (%)",
            min_value=0.01,
            max_value=99.99,
            value=1.5,
            step=0.1
        )

    use_leverage = st.checkbox("⚡ استفاده از اهرم", value=False)
    leverage = 1.0
    if use_leverage:
        leverage = st.number_input("اهرم (×)", min_value=1.0, max_value=125.0, value=10.0)
        st.warning(f"⚠️ با اهرم {leverage:.0f}×، ریسک شما به همان نسبت افزایش می‌یابد.")

    risk_input = st.text_input(
        "سطوح ریسک (%) - با کاما جدا کنید:",
        value="0.25, 0.5, 1, 2"
    )

    if st.button("🧮 محاسبه کن", type="primary"):
        risks, err = parse_risk_levels(risk_input)
        if err:
            st.error(err)
            return

        df, err = create_risk_management_table(
            capital,
            stop_loss_percentage,
            risks,
            leverage
        )

        if err:
            st.error(err)
            return

        st.success("✅ محاسبات انجام شد")

        st.subheader("📊 جدول سایز پوزیشن")
        st.dataframe(df.style.format("${:,.2f}"), use_container_width=True)

        st.info("💡 ردیف اول نشان‌دهنده حداکثر زیان مجاز در هر معامله است.")

if __name__ == "__main__":
    main()
