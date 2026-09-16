import math
import re
import unicodedata

import pandas as pd
import streamlit as st
from decimal import Decimal, ROUND_DOWN, InvalidOperation
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


# ─── پشتیبانی از اعداد فارسی/عربی ───
DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def normalize_risk_input(text: str) -> str:
    """تبدیل ورودی فارسی/عربی به فرمت قابل پردازش."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200c\u200d\u200e\u200f\ufeff]", "", text)
    text = text.translate(DIGIT_TRANSLATION)
    text = text.replace("٫", ".")
    text = re.sub(r"(?<=\d)/(?=\d)", ".", text)
    text = text.replace("،", ",")

    if "٬" in text:
        raise ValueError("از جداکننده هزارگان (٬) استفاده نکنید؛ سطوح ریسک را با کاما جدا کنید.")

    return text.strip()


def fmt_money(value: Decimal) -> str:
    return f"${float(value):,.2f}"


def validate_inputs(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float,
    take_profit_percentage: Optional[float] = None,
    mmr_percentage: Optional[float] = None,
    entry_price: Optional[float] = None,
    quantity_step: Optional[float] = None,
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

    if mmr_percentage is not None:
        if not math.isfinite(mmr_percentage) or mmr_percentage < 0:
            return "نرخ مارجین نگهداری باید عددی معتبر و حداقل صفر باشد."
        if mmr_percentage >= 100:
            return "نرخ مارجین نگهداری نمی‌تواند بیشتر یا مساوی ۱۰۰٪ باشد."

    if entry_price is not None:
        if not math.isfinite(entry_price) or entry_price <= 0:
            return "قیمت ورود باید عددی معتبر و بیشتر از صفر باشد."

    if quantity_step is not None:
        if not math.isfinite(quantity_step) or quantity_step <= 0:
            return "stepSize باید عددی معتبر و بیشتر از صفر باشد."

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
        risk_input = normalize_risk_input(risk_input)
    except ValueError as e:
        return None, str(e)

    try:
        risk_levels = []
        parts = risk_input.split(',')

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
    mmr_percentage: Optional[float] = None,
    entry_price: Optional[float] = None,
    quantity_step: Optional[float] = None,
) -> dict:
    """جدول نمایشی + هشدارها + لیکویید + گرد کردن حجم به stepSize صرافی."""

    capital_dec = Decimal(str(capital))
    sl_factor = Decimal(str(stop_loss_percentage)) / Decimal('100')
    leverage_dec = Decimal(str(leverage))
    tp_factor = (
        Decimal(str(take_profit_percentage)) / Decimal('100')
        if take_profit_percentage is not None
        else None
    )

    # تنظیمات گرد کردن حجم (فقط وقتی قیمت ورود و step هر دو داده شده باشند)
    qty_enabled = entry_price is not None and quantity_step is not None
    entry_dec = Decimal(str(entry_price)) if qty_enabled else None
    step_dec = Decimal(str(quantity_step)) if qty_enabled else None
    # تعداد اعشار نمایش حجم از exponent خود step درمی‌آید (0.001 → ۳ اعشار)
    qty_decimals = max(0, -step_dec.as_tuple().exponent) if qty_enabled else 0

    warnings: List[str] = []
    data = {}

    for risk_percent in risk_levels:
        risk_factor = Decimal(str(risk_percent)) / Decimal('100')
        dollar_risk = capital_dec * risk_factor          # ریسک برنامه‌ریزی‌شده
        position_size = dollar_risk / sl_factor          # سایز پوزیشن محاسباتی

        col_name = f"{risk_percent}%"
        values = [fmt_money(dollar_risk)]

        if qty_enabled:
            # حجم = سایز ÷ قیمت ورود، گرد شده به پایین تا مضرب step
            raw_qty = position_size / entry_dec
            units = (raw_qty / step_dec).to_integral_value(rounding=ROUND_DOWN)
            qty = units * step_dec
            qty_str = f"{float(qty):.{qty_decimals}f}"

            if qty == 0:
                warnings.append(
                    f"⚠️ سطح ریسک {risk_percent}%: حجم پوزیشن از حداقل stepSize صرافی "
                    f"({quantity_step}) کمتر است و قابل اجرا نیست!"
                )
                values += [qty_str, fmt_money(Decimal('0')), fmt_money(Decimal('0'))]
                actual_size = Decimal('0')
                actual_risk = Decimal('0')
            else:
                actual_size = qty * entry_dec            # سایز واقعی قابل اجرا
                actual_risk = actual_size * sl_factor    # ریسک واقعی بعد از گرد کردن
                values += [qty_str, fmt_money(actual_size), fmt_money(actual_risk)]
        else:
            actual_size = position_size
            values.append(fmt_money(position_size))

        if leverage > 1:
            margin_required = actual_size / leverage_dec
            values.append(fmt_money(margin_required))

        if tp_factor is not None:
            reward = actual_size * tp_factor
            values.append(fmt_money(reward))
            if actual_risk > 0:
                rr = reward / actual_risk
                values.append(f"{float(rr):.2f}R")
            else:
                values.append("—")

        data[col_name] = values

    # ساخت برچسب ردیف‌ها هماهنگ با ستون‌ها
    index_labels = ['💰 ریسک برنامه‌ریزی‌شده']
    if qty_enabled:
        index_labels += [
            f'🪙 حجم (واحد ارز، گرد به {quantity_step})',
            '📏 سایز واقعی بعد از گرد کردن',
            '⚠️ ریسک واقعی بعد از گرد کردن',
        ]
    else:
        index_labels.append('📊 سایز پوزیشن')

    if leverage > 1:
        index_labels.append('💳 مارجین لازم (با اهرم)')
    if tp_factor is not None:
        index_labels += ['💵 میزان سود', '⚖️ نسبت ریوارد/ریسک']

    # 💀 فاصله تقریبی تا لیکویید: 100/اهرم − MMR
    liq_distance_pct = None
    liq_status = None
    liq_message = None
    mmr_used_pct = None
    if leverage > 1:
        mmr_used_pct = mmr_percentage

        if mmr_used_pct is not None:
            mmr_factor = Decimal(str(mmr_used_pct)) / Decimal('100')
            liq_distance_pct = float((Decimal('1') / leverage_dec - mmr_factor) * Decimal('100'))
        else:
            liq_distance_pct = 100.0 / leverage

        mmr_note = f" (با MMR {mmr_used_pct:.2f}٪)" if mmr_used_pct is not None else ""

        if liq_distance_pct <= 0:
            liq_status = "danger"
            liq_message = (
                f"🚨 ترکیب اهرم {leverage:.0f}× و MMR {mmr_used_pct:.2f}٪ هیچ حاشیه تقریبی "
                f"برای لیکویید باقی نمی‌گذارد. این پوزیشن عملاً قابل معامله نیست."
            )
        elif stop_loss_percentage >= liq_distance_pct:
            liq_status = "danger"
            liq_message = (
                f"🚨 فاصله لیکویید (~{liq_distance_pct:.2f}٪{mmr_note}) کمتر یا مساوی حد ضرر "
                f"({stop_loss_percentage:.2f}٪) است! پوزیشن قبل از فعال شدن SL لیکویید می‌شود."
            )
        elif stop_loss_percentage >= 0.8 * liq_distance_pct:
            liq_status = "caution"
            liq_message = (
                f"⚠️ حد ضرر ({stop_loss_percentage:.2f}٪) خیلی نزدیک به فاصله لیکویید "
                f"(~{liq_distance_pct:.2f}٪{mmr_note}) است. حاشیه خطای کمی دارید."
            )
        else:
            liq_status = "ok"
            liq_message = (
                f"✅ حد ضرر ({stop_loss_percentage:.2f}٪) قبل از لیکویید تقریبی "
                f"(~{liq_distance_pct:.2f}٪{mmr_note}) فعال می‌شود."
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
            "mmr": mmr_used_pct,
            "qty_enabled": qty_enabled,
            "entry_price": entry_price,
            "qty_step": quantity_step,
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
    mmr_percentage = None
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

        use_mmr = st.checkbox('🧯 وارد کردن نرخ مارجین نگهداری صرافی (MMR)', value=False)

        mmr_input = st.number_input(
            'نرخ مارجین نگهداری (MMR ٪)',
            min_value=0.0,
            max_value=99.99,
            value=0.5,
            step=0.1,
            format="%.2f",
            disabled=not use_mmr,
            help="نرخ مارجین نگهداری صرافی شما (درصدی از ارزش پوزیشن). عدد دقیق را از صفحه ریسک صرافی خودتان چک کنید."
        )
        if use_mmr:
            mmr_percentage = mmr_input

    # ─── اطلاعات صرافی برای گرد کردن حجم ───
    use_qty = st.checkbox(
        '🪙 گرد کردن حجم به stepSize صرافی (نیاز به قیمت ورود دارد)',
        value=False,
        help="برای اینکه عدد جدول مستقیماً قابل اجرا باشد. stepSize را از مشخصات نماد در صرافی (فیلد LOT_SIZE) بردارید."
    )

    entry_price = None
    quantity_step = None
    if use_qty:
        entry_price = st.number_input(
            'قیمت ورود (USD)',
            min_value=0.0001,
            value=100.0,
            step=0.1,
            format="%.6f",
            help="قیمتی که قصد ورود به معامله را دارید. حجم = سایز پوزیشن ÷ این قیمت"
        )

        quantity_step = st.number_input(
            'stepSize حجم (مثلاً 0.001)',
            min_value=0.000001,
            value=0.001,
            step=0.001,
            format="%.6f",
            help="کوچک‌ترین گام مجاز حجم در صرافی. مثلاً 0.001 یعنی حجم باید مضربی از 0.001 باشد."
        )

    risk_inputs_str = st.text_input(
        "سطوح ریسک مورد نظر (٪) - با کاما جدا کنید:",
        value="0.25, 0.5, 1.0, 2.0",
        help="اعداد انگلیسی یا فارسی، ممیز (.) یا (٫) یا (/)، کامای فارسی (،) هم قبول است. مثال: ۰/۲۵، ۰/۵، ۱، ۲"
    )

    if st.button('🧮 محاسبه کن', type="primary"):
        risk_levels, parse_error = parse_risk_levels(risk_inputs_str)

        if parse_error:
            st.session_state.result = {"error": parse_error}
        else:
            validation_error = validate_inputs(
                capital, stop_loss_percentage, risk_levels, leverage,
                take_profit_percentage, mmr_percentage, entry_price, quantity_step
            )
            if validation_error:
                st.session_state.result = {"error": validation_error}
            else:
                try:
                    st.session_state.result = compute_results(
                        capital, stop_loss_percentage, risk_levels, leverage,
                        take_profit_percentage, mmr_percentage, entry_price, quantity_step
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

    st.dataframe(table_df, use_container_width=True, hide_index=False)

    # ⚠️ هشدارها (سایز/مارجین > سرمایه، حجم صفر)
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

        mmr_part = (
            f"فرمول: 100 ÷ اهرم − MMR ({snap['mmr']:.2f}٪)."
            if snap["mmr"] is not None
            else "فرمول: 100 ÷ اهرم (بدون MMR — برای دقت بیشتر MMR صرافی‌تان را وارد کنید)."
        )
        st.caption(
            f"💡 {mmr_part} مقدار واقعی به سطح ریسک پوزیشن، کارمزد، فاندینگ و "
            "مارجین اضافه‌شده هم بستگی دارد. صرافی‌ها معمولاً بر اساس قیمت Mark لیکویید می‌کنند."
        )

    # 📖 توضیح ردیف‌ها — بسته به فعال بودن گرد کردن حجم
    if snap["qty_enabled"]:
        st.info("💰 ردیف اول: ریسک دلاری برنامه‌ریزی‌شده (حداکثر ضرر مجاز، قبل از گرد کردن).")
        st.info(
            f"🪙 ردیف حجم: سایز پوزیشن ÷ قیمت ورود ({snap['entry_price']:g}) و گرد شده به پایین "
            f"تا مضرب stepSize ({snap['qty_step']:g}) — دقیقاً همان عددی که در صرافی وارد می‌کنید."
        )
        st.info(
            "📏 سایز واقعی، ریسک واقعی، مارجین، سود و R:R همه بر اساس همین حجم قابل اجرا محاسبه شده‌اند؛ "
            "چون گرد کردن به سمت پایین است، ریسک واقعی هرگز از برنامه بیشتر نمی‌شود."
        )
    else:
        st.info("💡 ردیف اول (میزان ریسک دلاری): حداکثر مبلغی که در صورت رسیدن به حد ضرر از دست می‌دهید.")
        st.info("🚀 ردیف دوم (سایز پوزیشن): ارزش کل دلاری معامله. برای عدد قابل اجرا در صرافی، گزینه «گرد کردن حجم به stepSize» را فعال کنید.")

    if snap["use_leverage"]:
        st.info(f"💳 مارجین لازم با اهرم {snap['leverage']:.0f}×: سایز پوزیشن ÷ {snap['leverage']:.0f}")

    if snap["tp"] is not None:
        st.info(f"💵 ردیف سود: اگر قیمت به حد سود ({snap['tp']:.2f}٪) برسد، این مبلغ را سود می‌کنید.")
        st.info("⚖️ نسبت ریوارد/ریسک: سود تقسیم بر ریسک (معادل حد سود ÷ حد ضرر). عدد بالاتر بهتر است، اما به‌تنهایی تضمین سودآوری نیست؛ نرخ برد و کارمزد هم مهم‌اند.")

    st.caption(
        "💡 محاسبات برای بازارهای Spot و فیوچرز خطی (Linear) است؛ قراردادهای دارای ضریب (Inverse/Multiplier) "
        "به فرمول اضافه نیاز دارند. کارمزد و اسلیپیج لحاظ نشده‌اند."
    )


if __name__ == "__main__":
    main()
