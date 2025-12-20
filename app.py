import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional
from decimal import Decimal, InvalidOperation

st.set_page_config(
    page_title="ماشین حساب مدیریت سرمایه",
    page_icon="🤖",
    layout="centered"
)

# ===================== CSS =====================
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

        .stMarkdown, .stText, div[data-testid="stAlert"] {
            direction: rtl !important;
            text-align: right !important;
        }

        table {
            direction: ltr !important;
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background-color: #f0f2f6;
            font-weight: 600;
            padding: 10px;
            text-align: center;
            white-space: nowrap;
        }

        td {
            padding: 10px;
            text-align: right;
            white-space: nowrap;
            unicode-bidi: plaintext;
        }

        td:first-child, th:first-child {
            text-align: left;
            font-weight: 600;
        }

        div[data-testid="stNumberInput"] input {
            direction: ltr !important;
            text-align: center !important;
        }

        div[data-testid="stTextInput"] input {
            direction: ltr !important;
            text-align: left !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ===================== Validation =====================
def validate_inputs(capital, stop_loss_percentage, risk_levels, leverage):
    if capital <= 0:
        return "سرمایه باید بیشتر از صفر باشد."
    if stop_loss_percentage < 0.01 or stop_loss_percentage >= 100:
        return "حد ضرر باید بین ۰.۰۱٪ تا ۱۰۰٪ باشد."
    if leverage < 1 or leverage > 125:
        return "اهرم باید بین ۱ تا ۱۲۵ باشد."
    if not risk_levels:
        return "حداقل یک سطح ریسک وارد کنید."
    return None

def parse_risk_levels(text):
    try:
        parts = text.replace('،', ',').split(',')
        return sorted(set(float(p.strip()) for p in parts if p.strip())), None
    except:
        return None, "فرمت سطوح ریسک نادرست است."

# ===================== Core Logic =====================
def create_risk_management_table(capital, sl_pct, risks, leverage):
    err = validate_inputs(capital, sl_pct, risks, leverage)
    if err:
        return None, err

    capital_dec = Decimal(str(capital))
    sl_factor = Decimal(str(sl_pct)) / Decimal("100")
    leverage_dec = Decimal(str(leverage))

    rows = []

    for label, calc in [
        ("میزان ریسک ($)", lambda r: capital_dec * Decimal(r) / 100),
        ("سایز پوزیشن ($)", lambda r: (capital_dec * Decimal(r) / 100) / sl_factor),
        ("مارجین لازم ($)", lambda r: ((capital_dec * Decimal(r) / 100) / sl_factor) / leverage_dec),
    ]:
        row = {"شرح": label}
        for r in risks:
            row[f"{r}%"] = f"${calc(r):,.2f}"
        rows.append(row)

    return pd.DataFrame(rows), None

# ===================== UI =====================
def main():
    inject_custom_css()

    st.title("🤖 ماشین حساب مدیریت سرمایه")
    st.markdown("محاسبه دقیق **سایز پوزیشن** بر اساس مدیریت ریسک")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        capital = st.number_input("سرمایه کل (USD)", min_value=0.01, value=1000.0)
    with c2:
        stop_loss = st.number_input("حد ضرر (%)", min_value=0.01, value=1.5)

    use_leverage = st.checkbox("⚡ استفاده از اهرم")
    leverage = 1.0
    if use_leverage:
        leverage = st.number_input("اهرم", min_value=1.0, max_value=125.0, value=10.0)

    risk_text = st.text_input("سطوح ریسک (%)", value="0.25, 0.5, 1, 2")

    if st.button("🧮 محاسبه کن", type="primary"):
        risks, err = parse_risk_levels(risk_text)
        if err:
            st.error(err)
            return

        df, err = create_risk_management_table(capital, stop_loss, risks, leverage)
        if err:
            st.error(err)
            return

        st.success("✅ محاسبات انجام شد")
        st.subheader("📊 جدول سایز پوزیشن")

        st.table(df)

if __name__ == "__main__":
    main()
