import math
import pandas as pd
import streamlit as st
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

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


def fmt_money(value: Decimal) -> str:
    return f"${float(value):,.2f}"


def validate_inputs(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float,
    take_profit_percentage: Optional[float] = None,
) -> Optional[str]:
    if not math.isfinite(capital) or capital <= 0:
        return "سرمایه باید عددی معتبر و بیشتر از صفر باشد."

    if not math.isfinite(stop_loss_percentage) or stop_loss_percentage <= 0:
        return "درصد حد ضرر باید عددی معتبر و بیشتر از صفر باشد."

    if stop_loss_percentage >= 100:
        return "درصد حد ضرر نمی‌تواند بیشتر یا مساوی ۱۰۰٪ باشد."

    if take_profit_percentage is not None:
        if not math.isfinite(take_profit_percentage) or take_profit_percentage <= 0:
            return "درصد حد سود باید عددی معتبر و بیشتر از صفر باشد."

    if not math.isfinite(leverage) or leverage < 1:
        return "اهرم باید عددی معتبر و حداقل ۱ باشد."

    if leverage > 125:
        return "اهرم نمی‌تواند بیشتر از ۱۲۵ باشد."

    if not risk_levels:
        return "لطفاً حداقل یک سطح ریسک وارد کنید."

    for risk in risk_levels:
        if not math.isfinite(risk) or risk <= 0:
            return "تمام سطوح ریسک باید اعدادی معتبر و بیشتر از صفر باشند."
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
                except ValueError:
                    return None, f"مقدار '{part}' معتبر نیست. لطفاً فقط اعداد وارد کنید."
                if not math.isfinite(value):
                    return None, f"مقدار '{part}' باید عددی متناهی باشد."
                risk_levels.append(value)

        if not risk_levels:
            return None, "لطفاً حداقل یک سطح ریسک معتبر وارد کنید."

        risk_levels = sorted(set(risk_levels))
        return risk_levels, None

    except Exception as e:
        return None, f"خطا در پردازش: {str(e)}"


def compute_results(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float,
    take_profit_percentage: Optional[float],
) -> dict:
    """محاسبه جدول نمایشی (تمام مقادیر رشته) + هشدارهای سایز/مارجین + فاصله لیکویید."""

    capital_dec = Decimal(str(capital))
    sl_factor = Decimal(str(stop_loss_percentage)) / Decimal('100')
    leverage_dec = Decimal(str(leverage))
    tp_factor = (
        Decimal(str(take_profit_percentage)) / Decimal('100')
        if take_profit_percentage is not None
        else None
    )

    warnings: List[str] = []
    data = {}

    for risk_percent in risk_levels:
        risk_factor = Decimal(str(risk_percent)) / Decimal('100')
        dollar_risk = capital_dec * risk_factor
        position_size = dollar_risk / sl_factor
        margin_required = position_size / leverage_dec

        # ⚠️ هشدار سایز/مارجین بیشتر از سرمایه (مقایسه Decimal دقیق، قبل از گرد کردن)
        if leverage > 1 and margin_required > capital_dec:
            warnings.append(
                f"⚠️ سطح ریسک {risk_percent}%: مارجین لازم ({fmt_money(margin_required)}) "
                f"از سرمایه ({fmt_money(capital_dec)}) بیشتر است!"
            )
        elif leverage == 1 and position_size > capital_dec:
            warnings.append(
                f"⚠️ سطح ریسک {risk_percent}%: سایز پوزیشن ({fmt_money(position_size)}) "
                f"از سرمایه ({fmt_money(capital_dec)}) بیشتر است! بدون اهرم این معامله قابل اجرا نیست."
            )

        col_name = f"{risk_percent}%"
        values = [fmt_money(dollar_risk), fmt_money(position_size)]

        if leverage > 1:
            values.append(fmt_money(margin_required))

        if tp_factor is not None:
            reward = position_size * tp_factor
            rr = reward / dollar_risk
            values.append(fmt_money(reward))
            values.append(f"{float(rr):.2f}R")

        data[col_name] = values

    index_labels = ['💰 میزان ریسک', '📊 سایز پوزیشن']
    if leverage > 1:
        index_labels.append('💳 مارجین لازم (با اهرم)')
    if tp_factor is not None:
        index_labels += ['💵 میزان سود', '⚖️ نسبت ریوارد/ریسک']

    # 💀 فاصله تقریبی تا لیکویید (مارجین ایزوله؛ بدون MMR، کارمزد و فاندینگ)
    liq_distance_pct = None
    liq_status = None
    liq_message = None
    if leverage > 1:
        liq_distance_pct = 100.0 / leverage

        if stop_loss_percentage >= liq_distance_pct:
            liq_status = "danger"
            liq_message = (
                f"🚨 فاصله لیکویید (~{liq_distance_pct:.2f}٪) کمتر یا مساوی حد ضرر "
                f"({stop_loss_percentage:.2f}٪) است! پوزیشن قبل از فعال شدن SL لیکویید می‌شود."
            )
        elif stop_loss_percentage >= 0.8 * liq_distance_pct:
            liq_status = "caution"
            liq_message = (
                f"⚠️ حد ضرر ({stop_loss_percentage:.2f}٪) خیلی نزدیک به فاصله لیکویید "
                f"(~{liq_distance_pct:.2f}٪) است. حاشیه خطای کمی دارید."
            )
        else:
            liq_status = "ok"
            liq_message = (
                f"✅ حد ضرر ({stop_loss_percentage:.2f}٪) قبل از لیکویید تقریبی "
                f"(~{liq_distance_pct:.2f}٪) فعال می‌شود."
            )

    return {
        "df": pd.DataFrame(data, index=index_labels),
        "warnings": warnings,
        "liq_distance_pct": liq_distance_pct,
        "liq_status": liq_status,
        "liq_message": liq_message,
        "inputs": {
            "capital": capital,
            "sl": stop_loss_percentage,
            "leverage": leverage,
            "use_leverage": leverage > 1,
            "tp": take_profit_percentage,
            "n_levels": len(risk_levels),
        },
    }


def main():
    inject_custom_css()

    if "result" not in st.session_state:
        st.session_state.result = None  # {"error": str} یا خروجی compute_results

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

    use_tp = st.checkbox('🎯 محاسبه حد سود (TP)', value=True)

    take_profit_percentage = None
    tp_input = st.number_input(
        'حد سود معامله (٪)',
        min_value=0.01,
        value=3.0,
        step=0.5,
        format="%.2f",
        disabled=not use_tp,
        help="درصد رشد قیمت تا حد سود (مثلاً ۳٪ یعنی TP در ۳٪ بالاتر از قیمت ورود)"
    )
    if use_tp:
        take_profit_percentage = tp_input

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
            st.session_state.result = {"error": parse_error}
        else:
            validation_error = validate_inputs(
                capital, stop_loss_percentage, risk_levels, leverage, take_profit_percentage
            )
            if validation_error:
                st.session_state.result = {"error": validation_error}
            else:
                try:
                    st.session_state.result = compute_results(
                        capital, stop_loss_percentage, risk_levels, leverage, take_profit_percentage
                    )
                except (InvalidOperation, ValueError, ZeroDivisionError) as e:
                    st.session_state.result = {"error": f"خطا در محاسبات: {str(e)}"}

    # ─── نمایش نتیجه (خارج از دکمه تا با rerun پاک نشود) ───
    result = st.session_state.result

    if result is not None and "error" in result:
        st.error(f"❌ {result['error']}")
        return

    if result is None:
        st.info("📝 مقادیر را وارد کنید و روی «محاسبه کن» بزنید.")
        return

    table_df = result["df"]
    snap = result["inputs"]

    st.success("✅ محاسبات با موفقیت انجام شد.")

    if snap["use_leverage"]:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("سرمایه", f"${snap['capital']:,.0f}")
        c2.metric("حد ضرر", f"{snap['sl']:.2f}%")
        c3.metric("اهرم", f"{snap['leverage']:.0f}×")
        c4.metric("تا لیکویید (تقریبی)", f"~{result['liq_distance_pct']:.2f}%")
        c5.metric("تعداد سطوح", snap["n_levels"])
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("سرمایه", f"${snap['capital']:,.0f}")
        c2.metric("حد ضرر", f"{snap['sl']:.2f}%")
        c3.metric("تعداد سطوح", snap["n_levels"])

    st.divider()
    st.subheader("📊 جدول سایز پوزیشن")

    # جدول نمایشی تمام-رشته‌ای است؛ بدون Styler
    st.dataframe(table_df, use_container_width=True, hide_index=False)

    # ⚠️ هشدارهای سایز/مارجین بیشتر از سرمایه
    for warning in result["warnings"]:
        st.error(warning)

    # 💀 وضعیت لیکویید در مقایسه با SL
    if snap["use_leverage"]:
        st.subheader("💀 فاصله تا لیکویید")
        if result["liq_status"] == "danger":
            st.error(result["liq_message"])
        elif result["liq_status"] == "caution":
            st.warning(result["liq_message"])
        else:
            st.info(result["liq_message"])

        st.caption(
            "💡 فرمول تقریبی: 100 ÷ اهرم. مقدار واقعی به Maintenance Margin صرافی، کارمزد، "
            "فاندینگ و مارجین اضافه‌شده بستگی دارد (تقریب دقیق‌تر: 100/اهرم − MMR). "
            "همچنین صرافی‌ها معمولاً بر اساس قیمت Mark لیکویید می‌کنند، نه قیمت Last."
        )

    st.info("💡 ردیف اول (میزان ریسک دلاری): این مقدار نشان‌دهنده حداکثر مبلغی است که شما مجازید در این معامله، در صورت رسیدن به حد ضرر، از دست بدهید.")

    if snap["use_leverage"]:
        st.info("📊 ردیف دوم (سایز پوزیشن): ارزش کل معامله‌ای که باید باز کنید.")
        st.info(f"💳 ردیف سوم (مارجین لازم با اهرم {snap['leverage']:.0f}×): با استفاده از اهرم {snap['leverage']:.0f}×، فقط کافیه این مقدار (سایز پوزیشن ÷ {snap['leverage']:.0f}) از سرمایه‌ات رو وارد کنی!")
    else:
        st.info("🚀 ردیف دوم (سایز پوزیشن): این مقدار نشان‌دهنده ارزش کل دلاری است که باید با آن وارد معامله شوید تا در صورت فعال شدن حد ضرر، دقیقا مبلغ ردیف اول را از دست بدهید.")

    if snap["tp"] is not None:
        st.info(f"💵 ردیف سود: اگر قیمت به حد سود ({snap['tp']:.2f}٪) برسد، این مبلغ را سود می‌کنید.")
        st.info("⚖️ نسبت ریوارد/ریسک: سود تقسیم بر ریسک (معادل حد سود ÷ حد ضرر). عدد بالاتر بهتر است، اما به‌تنهایی تضمین سودآوری نیست؛ نرخ برد و کارمزد هم مهم‌اند.")

    st.caption("💡 این محاسبات بر اساس فرمول‌های استاندارد مدیریت ریسک در بازارهای مالی انجام شده‌اند و کارمزد و اسلیپیج را لحاظ نمی‌کنند.")


if __name__ == "__main__":
    main()
