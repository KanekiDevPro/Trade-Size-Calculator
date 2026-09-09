import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional
from decimal import Decimal, InvalidOperation

st.set_page_config(
    page_title="ماشین حساب مدیریت سرمایه",
    page_icon="🤖",
    layout="centered"
)


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
            font-family: "Vazirmatn", sans-serif !important;
            text-align: right !important;
        }

        .stMarkdown, .stText, div[data-testid="stAlert"] {
            text-align: right !important;
            direction: rtl !important;
        }

        div[data-testid="stDataFrame"] table thead tr th,
        div[data-testid="stDataFrame"] table tbody tr th,
        div[data-testid="stDataFrame"] table tbody tr td {
            font-family: "Vazirmatn", sans-serif !important;
            text-align: center !important;
            font-size: 15px !important;
        }

        div[data-testid="stDataFrame"] table tbody tr th {
            text-align: right !important;
            font-weight: 600 !important;
        }

        div[data-testid="stDataFrame"] table {
            border-collapse: collapse !important;
        }

        div[data-testid="stDataFrame"] table thead tr th {
            background-color: #f0f2f6 !important;
            font-weight: 600 !important;
            padding: 12px 8px !important;
        }

        div[data-testid="stDataFrame"] table tbody tr td {
            padding: 10px 8px !important;
        }

        div[data-testid="stNumberInput"] input {
            direction: ltr !important;
            text-align: center !important;
        }

        div[data-testid="stTextInput"] input {
            direction: ltr !important;
            text-align: left !important;
        }

        div[data-testid="stButton"] {
            text-align: right !important;
            width: 100%;
        }

        .stButton button {
            direction: rtl;
            margin-left: auto;
            margin-right: 0;
            width: auto;
            border-radius: 8px;
            font-weight: bold;
        }

        div[data-testid="stMetric"] {
            direction: rtl !important;
            text-align: right !important;
            font-family: "Vazirmatn", sans-serif !important;
        }

        div[data-testid="stCheckbox"] {
            direction: rtl !important;
            text-align: right !important;
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

    if leverage < 1:
        return "اهرم باید حداقل ۱ باشد."

    if leverage > 125:
        return "اهرم نمی‌تواند بیشتر از ۱۲۵ باشد."

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
        risk_levels = []
        parts = risk_input.replace('،', ',').split(',')

        for part in parts:
            part = part.strip()
            if part:
                try:
                    value = float(part)
                    risk_levels.append(value)
                except ValueError:
                    return None, f"مقدار '{part}' معتبر نیست. لطفاً فقط اعداد وارد کنید."

        if not risk_levels:
            return None, "لطفاً حداقل یک سطح ریسک معتبر وارد کنید."

        risk_levels = sorted(set(risk_levels))

        return risk_levels, None

    except Exception as e:
        return None, f"خطا در پردازش: {str(e)}"

def create_risk_management_table(
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
                data[col_name] = [
                    dollar_risk,
                    position_size,
                    margin_required
                ]
            else:
                data[col_name] = [dollar_risk, position_size]

        if leverage > 1:
            index_labels = [
                '💰 میزان ریسک',
                '📊 سایز پوزیشن',
                '💳 مارجین لازم (با اهرم)'
            ]
        else:
            index_labels = ['💰 میزان ریسک', '📊 سایز پوزیشن']

        df = pd.DataFrame(data, index=index_labels)

        return df, None

    except (InvalidOperation, ValueError, ZeroDivisionError) as e:
        return None, f"خطا در محاسبات: {str(e)}"

def main():
    inject_custom_css()

    st.title('🤖 ماشین حساب مدیریت سرمایه')
    st.markdown("محاسبه دقیق سایز پوزیشن بر اساس سرمایه کل، درصد ریسک و اهرم.")

    st.divider()

    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            capital = st.number_input(
                'سرمایه کل (USD)',
                min_value=0.01,
                value=1000.0,
                step=100.0,
                format="%.0f",
                help="مجموع سرمایه‌ای که برای معامله در اختیار دارید"
            )

        with col2:
            stop_loss_percentage = st.number_input(
                'حد ضرر معامله (٪)',
                min_value=0.01,
                max_value=99.99,
                value=1.5,
                step=0.1,
                format="%.2f",
                help="درصد افت قیمت تا حد ضرر (مثلاً ۱.۵٪ یعنی SL در ۱.۵٪ پایین‌تر از قیمت ورود)"
            )

    use_leverage = st.checkbox('⚡️ استفاده از اهرم (Leverage)', value=False)

    leverage = 1.0
    if use_leverage:
        leverage = st.number_input(
            'مقدار اهرم (×)',
            min_value=1.0,
            max_value=125.0,
            value=10.0,
            step=1.0,
            format="%.0f",
            help="اهرم معاملاتی (مثلاً 10× یعنی ده برابر قدرت خرید)"
        )

        st.warning(f"⚠️ هشدار: با اهرم {leverage:.0f}×، فاصله تا لیکویید شدن کمتر می‌شود. سایز پوزیشن را حتماً طبق جدول تنظیم کنید!")

    risk_inputs_str = st.text_input(
        "سطوح ریسک مورد نظر (٪) - با کاما جدا کنید:",
        value="0.25, 0.5, 1.0, 2.0",
        help="مثال: 0.5, 1, 2 یا 0.25, 0.5, 1, 1.5, 2, 3"
    )

    if st.button('🧮 محاسبه کن', type="primary"):
        risk_levels, parse_error = parse_risk_levels(risk_inputs_str)

        if parse_error:
            st.error(f"❌ {parse_error}")
            return

        table_df, calc_error = create_risk_management_table(
            capital,
            stop_loss_percentage,
            risk_levels,
            leverage
        )

        if calc_error:
            st.error(f"❌ {calc_error}")
        else:
            st.success("✅ محاسبات با موفقیت انجام شد.")

            if use_leverage:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("سرمایه", f"${capital:,.0f}")
                c2.metric("حد ضرر", f"{stop_loss_percentage:.2f}%")
                c3.metric("اهرم", f"{leverage:.0f}×")
                c4.metric("تعداد سطوح", len(risk_levels))
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("سرمایه", f"${capital:,.0f}")
                c2.metric("حد ضرر", f"{stop_loss_percentage:.2f}%")
                c3.metric("تعداد سطوح", len(risk_levels))

            st.divider()

            st.subheader("📊 جدول سایز پوزیشن")

            st.dataframe(
                table_df.style.format("${:,.2f}"),
                use_container_width=True
            )

            st.info("💡 ردیف اول (میزان ریسک دلاری): این مقدار نشان‌دهنده حداکثر مبلغی است که شما مجازید در این معامله، در صورت رسیدن به حد ضرر، از دست بدهید.")

            if use_leverage:
                st.info("📊 ردیف دوم (سایز پوزیشن): ارزش کل معامله‌ای که باید باز کنید.")
                st.info(f"💳 ردیف سوم (مارجین لازم با اهرم {leverage:.0f}×): با استفاده از اهرم {leverage:.0f}×، فقط کافیه این مقدار (سایز پوزیشن ÷ {leverage:.0f}) از سرمایه‌ات رو وارد کنی!")
            else:
                st.info("🚀 ردیف دوم (سایز پوزیشن): این مقدار نشان‌دهنده ارزش کل دلاری است که باید با آن وارد معامله شوید تا در صورت فعال شدن حد ضرر، دقیقا مبلغ ردیف اول را از دست بدهید.")

            st.caption("💡 این محاسبات بر اساس فرمول‌های استاندارد مدیریت ریسک در بازارهای مالی انجام شده‌اند.")

if __name__ == "__main__":
    main()
