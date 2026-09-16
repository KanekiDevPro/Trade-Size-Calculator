import math
import re
import unicodedata

import pandas as pd
import streamlit as st
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import List, Optional, Tuple

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    ccxt = None
    CCXT_AVAILABLE = False

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

        /* دکمه‌های مرتب و هم‌عرض */
        div[data-testid="stButton"] {
            text-align: center !important;
            width: 100%;
        }

        .stButton button {
            direction: rtl;
            width: 100%;
            border-radius: 10px;
            font-weight: bold;
            padding: 0.5rem 1rem;
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #1f77b4, #2a9d8f);
            color: white;
            border: none;
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

        /* ظاهر بهتر expanderها */
        div[data-testid="stExpander"] {
            border: 1px solid #e6e6e6;
            border-radius: 10px;
            background-color: #fafafa;
        }

        div[data-testid="stExpander"] summary {
            font-weight: bold;
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


# ─── اتصال به صرافی‌ها (فقط داده عمومی بازار؛ بدون API key) ───
# ترتیب: صرافی‌های معتبر آمریکایی اول (بدون geo-block)، بعد بقیه
EXCHANGE_OPTIONS = ["kraken", "coinbase", "binanceus", "bybit", "kucoin", "mexc", "okx", "binance"]

FUTURES_CCXT_ID = {
    "binance": "binanceusdm",
    "kucoin": "kucoinfutures",
}


def _make_exchange(exchange_id: str, market_type: str):
    if market_type == "future":
        ccxt_id = FUTURES_CCXT_ID.get(exchange_id, exchange_id)
    else:
        ccxt_id = exchange_id
    exchange = getattr(ccxt, ccxt_id)({
        "enableRateLimit": True,
        "timeout": 12000,   # میلی‌ثانیه
    })
    if market_type == "future":
        exchange.options["defaultType"] = "swap"
    return exchange


@st.cache_data(ttl=3600, show_spinner="در حال دریافت لیست نمادها از صرافی...")
def fetch_symbols(exchange_id: str, market_type: str) -> List[str]:
    """لیست نمادهای فعال USDT — کش ۱ ساعته، بر اساس (صرافی، نوع بازار)."""
    exchange = _make_exchange(exchange_id, market_type)
    exchange.load_markets()

    symbols = set()
    for m in exchange.markets.values():
        if not m.get("active") or m.get("option"):
            continue
        if market_type == "spot" and m.get("quote") == "USDT":
            base = m.get("base", "")
            if base.endswith(("UP", "DOWN")):   # توکن‌های اهرمی
                continue
            symbols.add(m["symbol"])
        elif market_type == "future" and m.get("settle") == "USDT":
            symbols.add(m["symbol"])   # مثل BTC/USDT:USDT

    return sorted(symbols)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_rules(exchange_id: str, market_type: str, symbol: str):
    """stepSize و minQty حجم — قوانین صرافی که به‌ندرت عوض می‌شوند."""
    exchange = _make_exchange(exchange_id, market_type)
    exchange.load_markets()
    if symbol not in exchange.markets:
        raise ValueError(f"نماد '{symbol}' در این صرافی پیدا نشد.")
    market = exchange.market(symbol)

    prec = market["precision"].get("amount")
    if prec is None:
        raise ValueError("این صرافی اطلاعات دقت حجم را ارائه نمی‌دهد.")

    # precisionMode تعیین می‌کند prec یعنی چه (تعداد اعشار یا اندازه گام)
    if exchange.precisionMode == ccxt.TICK_SIZE:
        step = Decimal(str(prec))
    elif exchange.precisionMode == ccxt.DECIMAL_PLACES:
        step = Decimal("1").scaleb(-int(prec))
    else:
        # SIGNIFICANT_DIGITS و بقیه: حدس زدن step خطرناک است
        raise ValueError(
            "حالت دقت (precisionMode) این نماد پشتیبانی نمی‌شود؛ stepSize را دستی وارد کنید."
        )

    min_qty = market["limits"]["amount"].get("min")
    return step, (Decimal(str(min_qty)) if min_qty else None)


@st.cache_data(ttl=15, show_spinner=False)
def fetch_current_price(exchange_id: str, market_type: str, symbol: str):
    """آخرین قیمت نماد (کش ۱۵ ثانیه — قیمت باید تازه باشد)."""
    exchange = _make_exchange(exchange_id, market_type)
    exchange.load_markets()
    if symbol not in exchange.markets:
        raise ValueError(f"نماد '{symbol}' در این صرافی پیدا نشد.")
    ticker = exchange.fetch_ticker(symbol)
    if ticker.get("last") is None:
        raise ValueError("قیمتی برای این نماد دریافت نشد.")
    return Decimal(str(ticker["last"]))


@st.cache_data(ttl=300, show_spinner=False)
def test_exchange_access(exchange_id: str, market_type: str) -> Tuple[bool, str]:
    """تست سبک دسترسی به صرافی از سرور فعلی — خطا را برنمی‌گرداند."""
    try:
        exchange = _make_exchange(exchange_id, market_type)
        exchange.load_markets()
        return True, f"در دسترس — {len(exchange.markets):,} بازار"
    except Exception as exc:
        detail = str(exc)
        if "451" in detail or "403" in detail or "banned" in detail.lower():
            detail += " (به‌احتمال زیاد geo-block از سرور فعلی)"
        return False, detail[:120]


def validate_inputs(
    capital: float,
    stop_loss_percentage: float,
    risk_levels: List[float],
    leverage: float,
    take_profit_percentage: Optional[float] = None,
    mmr_percentage: Optional[float] = None,
    entry_price: Optional[float] = None,
    quantity_step: Optional[float] = None,
    fee_percentage: Optional[float] = None,
    slippage_percentage: Optional[float] = None,
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

    if fee_percentage is not None:
        if not math.isfinite(fee_percentage) or fee_percentage < 0:
            return "کارمزد باید عددی معتبر و حداقل صفر باشد."
        if fee_percentage >= 10:
            return "کارمزد نمی‌تواند بیشتر یا مساوی ۱۰٪ باشد."

    if slippage_percentage is not None:
        if not math.isfinite(slippage_percentage) or slippage_percentage < 0:
            return "اسلیپیج باید عددی معتبر و حداقل صفر باشد."
        if slippage_percentage >= 10:
            return "اسلیپیج نمی‌تواند بیشتر یا مساوی ۱۰٪ باشد."

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
    direction: str = "long",
    mmr_percentage: Optional[float] = None,
    entry_price: Optional[float] = None,
    quantity_step: Optional[float] = None,
    fee_percentage: Optional[float] = None,
    slippage_percentage: Optional[float] = None,
    min_qty: Optional[float] = None,
) -> dict:
    """جدول + هشدارها + لیکویید + گرد کردن حجم (+چک minQty) + کارمزد/اسلیپیج."""

    capital_dec = Decimal(str(capital))
    sl_factor = Decimal(str(stop_loss_percentage)) / Decimal('100')
    leverage_dec = Decimal(str(leverage))
    tp_factor = (
        Decimal(str(take_profit_percentage)) / Decimal('100')
        if take_profit_percentage is not None
        else None
    )
    fee_factor = (
        Decimal(str(fee_percentage)) / Decimal('100')
        if fee_percentage is not None
        else None
    )
    slip_factor = (
        Decimal(str(slippage_percentage)) / Decimal('100')
        if slippage_percentage is not None
        else None
    )
    fees_on = fee_factor is not None and slip_factor is not None

    qty_enabled = entry_price is not None and quantity_step is not None
    entry_dec = Decimal(str(entry_price)) if qty_enabled else None
    step_dec = Decimal(str(quantity_step)) if qty_enabled else None
    min_qty_dec = Decimal(str(min_qty)) if (min_qty is not None and min_qty > 0) else None
    qty_decimals = max(0, -step_dec.as_tuple().exponent) if qty_enabled else 0

    is_short = direction == "short"

    warnings: List[str] = []
    data = {}

    for risk_percent in risk_levels:
        risk_factor = Decimal(str(risk_percent)) / Decimal('100')
        dollar_risk = capital_dec * risk_factor
        position_size = dollar_risk / sl_factor

        col_name = f"{risk_percent}%"
        values = [fmt_money(dollar_risk)]

        real_loss: Optional[Decimal] = None
        qty: Optional[Decimal] = None
        actual_size: Optional[Decimal] = None
        entry_eff: Optional[Decimal] = None

        if qty_enabled:
            raw_qty = position_size / entry_dec
            units = (raw_qty / step_dec).to_integral_value(rounding=ROUND_DOWN)
            qty = units * step_dec
            qty_str = f"{float(qty):.{qty_decimals}f}"

            if qty == 0:
                # حجم قابل اجرا صفر است → همه مقادیر واقعی هم صفر می‌مانند
                warnings.append(
                    f"⚠️ سطح ریسک {risk_percent}%: حجم پوزیشن از حداقل stepSize صرافی "
                    f"({quantity_step}) کمتر است و قابل اجرا نیست!"
                )
                actual_size = Decimal('0')
                real_loss = Decimal('0')
                values += [qty_str, fmt_money(Decimal('0')), fmt_money(Decimal('0'))]
            else:
                if min_qty_dec is not None and qty < min_qty_dec:
                    min_qty_text = f"{float(min_qty_dec):g}"   # فرمت قبل از f-string اصلی
                    warnings.append(
                        f"⚠️ سطح ریسک {risk_percent}%: حجم {qty_str} از حداقل حجم مجاز صرافی "
                        f"(minQty = {min_qty_text}) کمتر است — سفارش رد می‌شود!"
                    )

                actual_size = qty * entry_dec
                entry_eff = entry_dec * (Decimal('1') - slip_factor) if fees_on else entry_dec
                E = entry_dec
                s, sl = slip_factor, sl_factor

                if fees_on:
                    # Short: ورود بدتر = ارزان‌تر، خروج بدتر = گران‌تر
                    exit_sl = E * (Decimal('1') + sl) * (Decimal('1') + s)
                    loss_per_unit = exit_sl - entry_eff + fee_factor * (entry_eff + exit_sl)
                    real_loss = qty * loss_per_unit
                else:
                    real_loss = actual_size * sl_factor

                values += [qty_str, fmt_money(actual_size), fmt_money(real_loss)]
        else:
            values.append(fmt_money(position_size))

            if fees_on:
                # بدون قیمت ورود: قیمت نمادین E=1 — ریسک دلاری دقیق می‌ماند
                E = Decimal('1')
                s, sl = slip_factor, sl_factor
                entry_eff = E * (Decimal('1') - s)
                exit_sl = E * (Decimal('1') + sl) * (Decimal('1') + s)
                loss_per_unit = exit_sl - entry_eff + fee_factor * (entry_eff + exit_sl)
                qty_base = position_size / entry_eff
                real_loss = qty_base * loss_per_unit
                values.append(fmt_money(real_loss))

        if leverage > 1:
            # حجم صفر → مارجین هم صفر (نه سایز نظری!)
            if qty_enabled and qty is not None:
                margin_base = actual_size
            else:
                margin_base = position_size
            values.append(fmt_money(margin_base / leverage_dec))

        if tp_factor is not None:
            if fees_on and real_loss is not None and real_loss > 0:
                E = entry_dec if qty_enabled else Decimal('1')
                s, sl, tp = slip_factor, sl_factor, tp_factor
                exit_tp = E * (Decimal('1') - tp) * (Decimal('1') + s)
                reward_per_unit = (
                    entry_eff - exit_tp - fee_factor * (entry_eff + exit_tp)
                )
                qty_exec = qty if (qty_enabled and qty is not None) else position_size / entry_eff
                net_reward = qty_exec * reward_per_unit

                if net_reward > 0:
                    values.append(fmt_money(net_reward))
                    rr = net_reward / real_loss
                    values.append(f"{float(rr):.2f}R")
                else:
                    values.append("❌ منفی")
                    values.append("—")
                    warnings.append(
                        f"❌ سطح ریسک {risk_percent}%: با کارمزد {fee_percentage}٪ و اسلیپیج "
                        f"{slippage_percentage}٪، حتی رسیدن به حد سود هم سود خالص ندارد!"
                    )
            elif fees_on:
                values += [fmt_money(Decimal('0')), "—"]
            else:
                reward_base = actual_size if qty_enabled else position_size
                reward = reward_base * tp_factor
                values.append(fmt_money(reward))
                denom = real_loss if real_loss else dollar_risk
                rr = reward / denom
                values.append(f"{float(rr):.2f}R")

        data[col_name] = values

    # ─── برچسب ردیف‌ها ───
    direction_label = '🔻 پوزیشن Short' if is_short else '🔺 پوزیشن Long'
    index_labels = [f'{direction_label} — 💰 ریسک برنامه‌ریزی‌شده']
    if qty_enabled:
        index_labels += [
            f'🪙 حجم (واحد ارز، گرد به {quantity_step})',
            '📏 سایز واقعی بعد از گرد کردن',
            '⚠️ ریسک واقعی' + (' (با کارمزد/اسلیپیج)' if fees_on else ''),
        ]
    else:
        index_labels.append('📊 سایز پوزیشن')
        if fees_on:
            index_labels.append('💸 ضرر واقعی با کارمزد/اسلیپیج')

    if leverage > 1:
        index_labels.append('💳 مارجین لازم (با اهرم)')
    if tp_factor is not None:
        index_labels += [
            '🪙 سود خالص بعد از هزینه‌ها' if fees_on else '💵 میزان سود',
            '📉 R:R خالص' if fees_on else '⚖️ نسبت ریوارد/ریسک',
        ]

    # 💀 فاصله تقریبی تا لیکویید: 100/اهرم − MMR
    liq_distance_pct = None
    liq_status = None
    liq_message = None
    if leverage > 1:
        if mmr_percentage is not None:
            mmr_factor = Decimal(str(mmr_percentage)) / Decimal('100')
            liq_distance_pct = float((Decimal('1') / leverage_dec - mmr_factor) * Decimal('100'))
        else:
            liq_distance_pct = 100.0 / leverage

        mmr_note = f" (با MMR {mmr_percentage:.2f}٪)" if mmr_percentage is not None else ""
        move_word = "رشد قیمت" if is_short else "افت قیمت"

        if liq_distance_pct <= 0:
            liq_status = "danger"
            liq_message = (
                f"🚨 ترکیب اهرم {leverage:.0f}× و MMR {mmr_percentage:.2f}٪ هیچ حاشیه تقریبی "
                f"برای لیکویید باقی نمی‌گذارد. این پوزیشن عملاً قابل معامله نیست."
            )
        elif stop_loss_percentage >= liq_distance_pct:
            liq_status = "danger"
            liq_message = (
                f"🚨 فاصله لیکویید (~{liq_distance_pct:.2f}٪{mmr_note} {move_word}) کمتر یا مساوی "
                f"حد ضرر ({stop_loss_percentage:.2f}٪) است! پوزیشن قبل از فعال شدن SL لیکویید می‌شود."
            )
        elif stop_loss_percentage >= 0.8 * liq_distance_pct:
            liq_status = "caution"
            liq_message = (
                f"⚠️ حد ضرر ({stop_loss_percentage:.2f}٪) خیلی نزدیک به فاصله لیکویید "
                f"(~{liq_distance_pct:.2f}٪{mmr_note} {move_word}) است. حاشیه خطای کمی دارید."
            )
        else:
            liq_status = "ok"
            liq_message = (
                f"✅ حد ضرر ({stop_loss_percentage:.2f}٪) قبل از لیکویید تقریبی "
                f"(~{liq_distance_pct:.2f}٪{mmr_note} {move_word}) فعال می‌شود."
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
            "direction": direction,
            "tp": take_profit_percentage,
            "mmr": mmr_percentage,
            "qty_enabled": qty_enabled,
            "entry_price": entry_price,
            "qty_step": quantity_step,
            "min_qty": min_qty,
            "fees_on": fees_on,
            "fee": fee_percentage,
            "slippage": slippage_percentage,
            "fetched_from": st.session_state.get("fetched_from"),
            "n_levels": len(risk_levels),
        },
    }


def main():
    inject_custom_css()

    if "result" not in st.session_state:
        st.session_state.result = None

    st.title('🤖 ماشین حساب مدیریت سرمایه')
    st.markdown("محاسبه دقیق سایز پوزیشن بر اساس سرمایه کل، درصد ریسک و اهرم.")

    st.divider()

    # ═══════════ تنظیمات اصلی ═══════════
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
                help="درصد حرکت نامساعد قیمت تا حد ضرر (Long: افت؛ Short: رشد)"
            )

    direction = st.radio(
        'جهت پوزیشن',
        options=['long', 'short'],
        format_func=lambda d: '🔺 لانگ (خرید)' if d == 'long' else '🔻 شورت (فروش)',
        horizontal=True,
        help="مدل هزینه‌ها برای هر دو جهت یکسان است: اسلیپیج نامساعد در ورود و خروج + کارمزد taker دو طرف."
    )

    # ═══════════ اهرم و لیکویید ═══════════
    leverage = 1.0
    mmr_percentage = None

    with st.expander("⚡️ اهرم، مارجین و لیکویید", expanded=False):
        use_leverage = st.checkbox('استفاده از اهرم (Leverage)', value=False)

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
            liq_word = "رشد قیمت" if direction == "short" else "افت قیمت"
            st.warning(f"⚠️ با اهرم {leverage:.0f}×، {liq_word} کمتر منجر به لیکویید می‌شود!")

            use_mmr = st.checkbox('وارد کردن نرخ مارجین نگهداری صرافی (MMR)', value=False)

            mmr_input = st.number_input(
                'نرخ مارجین نگهداری (MMR ٪)',
                min_value=0.0,
                max_value=99.99,
                value=0.5,
                step=0.1,
                format="%.2f",
                disabled=not use_mmr,
                help="نرخ مارجین نگهداری صرافی شما (درصدی از ارزش پوزیشن). عدد دقیق را از صفحه ریسک صرافی چک کنید."
            )
            if use_mmr:
                mmr_percentage = mmr_input

    # ═══════════ حد سود ═══════════
    with st.expander("🎯 حد سود (TP)", expanded=True):
        use_tp = st.checkbox('محاسبه حد سود', value=True)

        take_profit_percentage = None
        tp_input = st.number_input(
            'حد سود معامله (٪)',
            min_value=0.01,
            value=3.0,
            step=0.5,
            format="%.2f",
            disabled=not use_tp,
            help="درصد حرکت مطلوب قیمت تا حد سود (Long: رشد؛ Short: افت)"
        )
        if use_tp:
            take_profit_percentage = tp_input

    # ═══════════ گرد کردن حجم + صرافی ═══════════
    use_qty = False
    entry_price = None
    quantity_step = None
    exchange_id = None
    market_type = "spot"
    symbol = None
    symbols_list = []
    current_symbol = None

    with st.expander("🪙 گرد کردن حجم به stepSize صرافی (دریافت خودکار از صرافی)", expanded=False):
        use_qty = st.checkbox(
            'فعال کردن گرد کردن حجم',
            value=False,
            help="حجم را به مضرب stepSize صرافی گرد می‌کند تا عدد جدول مستقیماً قابل اجرا باشد. قیمت ورود و stepSize را می‌توانید خودکار از صرافی بگیرید یا دستی وارد کنید."
        )

        if use_qty:
            if not CCXT_AVAILABLE:
                st.info("📦 برای دریافت خودکار از صرافی، پکیج ccxt را نصب کنید: `pip install ccxt` — فعلاً می‌توانید دستی وارد کنید.")
            else:
                fc1, fc2 = st.columns(2)

                with fc1:
                    exchange_id = st.selectbox(
                        'صرافی',
                        EXCHANGE_OPTIONS,
                        index=0,
                        format_func=lambda x: x.title(),
                        help="Kraken و Coinbase از سرورهای آمریکایی (مثل Streamlit Cloud) در دسترس‌ترند. بایننس معمولاً geo-block است."
                    )

                with fc2:
                    market_type = st.selectbox(
                        'نوع بازار',
                        ['spot', 'future'],
                        format_func=lambda x: 'اسپات' if x == 'spot' else 'فیوچرز (پایپرپچوال)'
                    )

                symbols_key = f"symbols_{exchange_id}_{market_type}"

                b1, b2 = st.columns(2)
                with b1:
                    if st.button('📋 دریافت لیست نمادها', key=f"load_symbols_{exchange_id}_{market_type}"):
                        try:
                            st.session_state[symbols_key] = fetch_symbols(exchange_id, market_type)
                        except Exception as e:
                            st.session_state[symbols_key] = []
                            st.error(
                                f"❌ دریافت لیست نمادها ناموفق بود: {e}\n\n"
                                f"💡 اگر خطای شبکه/دسترسی است، صرافی دیگری را امتحان کنید."
                            )

                with b2:
                    if st.button('🌐 تست دسترسی صرافی‌ها', key="test_all"):
                        results = []
                        progress = st.progress(0.0, text="در حال تست صرافی‌ها...")
                        for i, ex_id in enumerate(EXCHANGE_OPTIONS):
                            ok, detail = test_exchange_access(ex_id, market_type)
                            results.append({
                                "صرافی": ex_id.title(),
                                "وضعیت": "✅ در دسترس" if ok else "❌ بلاک/خطا",
                                "جزئیات": detail,
                            })
                            progress.progress((i + 1) / len(EXCHANGE_OPTIONS))
                        progress.empty()
                        st.session_state["exchange_tests"] = results

                # نمایش نتایج تست ذخیره‌شده
                if "exchange_tests" in st.session_state:
                    st.dataframe(
                        pd.DataFrame(st.session_state["exchange_tests"]),
                        use_container_width=True,
                        hide_index=True,
                    )

                symbols_list = st.session_state.get(symbols_key, [])

                if symbols_list:
                    symbol = st.selectbox(
                        'نماد (برای جستجو شروع به تایپ کنید)',
                        options=symbols_list,
                        index=0,
                        key=f"symbol_sel_{exchange_id}_{market_type}",
                        help="لیست فقط شامل نمادهای فعال USDT است. فیوچرزها به شکل BTC/USDT:USDT نمایش داده می‌شوند."
                    )
                    current_symbol = symbol

                    if st.button('🔄 دریافت قیمت و stepSize', key=f"fetch_data_{exchange_id}_{market_type}"):
                        try:
                            step_fetched, min_q = fetch_market_rules(exchange_id, market_type, symbol)
                            price_dec = fetch_current_price(exchange_id, market_type, symbol)

                            # مقداردهی قبل از ساخت widgetها → بدون rerun
                            st.session_state["entry_price_input"] = float(price_dec)
                            st.session_state["quantity_step_input"] = float(step_fetched)
                            st.session_state["min_qty_fetched"] = float(min_q) if min_q else None
                            st.session_state["fetched_symbol"] = symbol

                            min_qty_text = f"{float(min_q):g}" if min_q else "—"
                            st.session_state["fetched_from"] = (
                                f"{exchange_id.title()} • {symbol} • قیمت {float(price_dec):g} • "
                                f"stepSize {float(step_fetched):g} • minQty {min_qty_text}"
                            )
                            st.success(
                                f"✅ {symbol}: قیمت {float(price_dec):g} | "
                                f"stepSize {float(step_fetched):g} | minQty {min_qty_text}"
                            )
                        except Exception as e:
                            st.error(
                                f"❌ دریافت اطلاعات ناموفق بود: {e}\n\n"
                                f"💡 مقادیر را می‌توانید دستی وارد کنید."
                            )

                    if st.session_state.get("fetched_symbol") and st.session_state["fetched_symbol"] != current_symbol:
                        st.warning("⚠️ نماد عوض شده — دوباره «دریافت قیمت و stepSize» بزنید.")
                    elif st.session_state.get("fetched_from"):
                        st.caption(f"📡 {st.session_state['fetched_from']}")
                else:
                    st.info("ابتدا «📋 دریافت لیست نمادها» را بزنید (لیست کش می‌شود و بار دوم فوری است) — یا مقادیر را دستی وارد کنید.")

            entry_price = st.number_input(
                'قیمت ورود (USD)',
                min_value=0.0001,
                value=100.0,
                step=0.1,
                format="%.6f",
                key="entry_price_input",
                help="قیمتی که قصد ورود به معامله را دارید. حجم = سایز پوزیشن ÷ این قیمت. عدد دریافت‌شده قابل ویرایش است."
            )

            quantity_step = st.number_input(
                'stepSize حجم (مثلاً 0.001)',
                min_value=0.000001,
                value=0.001,
                step=0.001,
                format="%.6f",
                key="quantity_step_input",
                help="کوچک‌ترین گام مجاز حجم در صرافی (فیلد LOT_SIZE). عدد دریافت‌شده قابل ویرایش است."
            )

    # ═══════════ کارمزد و اسلیپیج ═══════════
    fee_percentage = None
    slippage_percentage = None

    with st.expander("📝 کارمزد و اسلیپیج (اختیاری)", expanded=False):
        use_fees = st.checkbox(
            'لحاظ کردن کارمزد و اسلیپیج',
            value=False,
            help="ضرر واقعی و سود خالص را با کارمزد taker دو طرف معامله و اسلیپیج نامساعد در ورود و خروج محاسبه می‌کند. برای هر دو جهت Long و Short درست کار می‌کند."
        )

        if use_fees:
            colf1, colf2 = st.columns(2)

            with colf1:
                fee_percentage = st.number_input(
                    'کارمزد هر طرف (٪)',
                    min_value=0.0,
                    max_value=9.99,
                    value=0.05,
                    step=0.01,
                    format="%.2f",
                    help="کارمزد taker برای هر طرف معامله (ورود و خروج جداگانه محاسبه می‌شود). مثلاً بایننس فیوچرز حدود ۰.۰۵٪."
                )

            with colf2:
                slippage_percentage = st.number_input(
                    'اسلیپیج هر طرف (٪)',
                    min_value=0.0,
                    max_value=9.99,
                    value=0.0,
                    step=0.05,
                    format="%.2f",
                    help="اختلاف قیمت اجرا شده با قیمت دلخواه؛ در ورود و خروج هر دو به ضرر شما اعمال می‌شود."
                )

    # ═══════════ سطوح ریسک ═══════════
    risk_inputs_str = st.text_input(
        "سطوح ریسک مورد نظر (٪) - با کاما جدا کنید:",
        value="0.25, 0.5, 1.0, 2.0",
        help="اعداد انگلیسی یا فارسی، ممیز (.) یا (٫) یا (/)، کامای فارسی (،) هم قبول است. مثال: ۰/۲۵، ۰/۵، ۱، ۲"
    )

    # ═══════════ دکمه محاسبه ═══════════
    if st.button('🧮 محاسبه کن', type="primary"):
        risk_levels, parse_error = parse_risk_levels(risk_inputs_str)

        if parse_error:
            st.session_state.result = {"error": parse_error}
        else:
            validation_error = validate_inputs(
                capital, stop_loss_percentage, risk_levels, leverage,
                take_profit_percentage, mmr_percentage, entry_price, quantity_step,
                fee_percentage, slippage_percentage
            )
            if validation_error:
                st.session_state.result = {"error": validation_error}
            else:
                try:
                    # minQty فقط وقتی معتبر است که به نماد فعلی تعلق داشته باشد
                    min_qty_to_use = (
                        st.session_state.get("min_qty_fetched")
                        if use_qty
                        and st.session_state.get("fetched_symbol") == current_symbol
                        else None
                    )
                    st.session_state.result = compute_results(
                        capital, stop_loss_percentage, risk_levels, leverage,
                        take_profit_percentage, direction, mmr_percentage,
                        entry_price, quantity_step, fee_percentage, slippage_percentage,
                        min_qty=min_qty_to_use
                    )
                except (InvalidOperation, ValueError, ZeroDivisionError) as e:
                    st.session_state.result = {"error": f"خطا در محاسبات: {str(e)}"}

    # ═══════════ نمایش نتیجه ═══════════
    result = st.session_state.result

    if result is not None and "error" in result:
        st.error(f"❌ {result['error']}")
        return

    if result is None:
        st.info("📝 مقادیر را وارد کنید و روی «محاسبه کن» بزنید.")
        return

    table_df = result["df"]
    snap = result["inputs"]
    dir_label = "🔻 Short" if snap["direction"] == "short" else "🔺 Long"

    st.success(f"✅ محاسبات پوزیشن {dir_label} با موفقیت انجام شد.")

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

    for warning in result["warnings"]:
        st.error(warning)

    # 💀 لیکویید داخل expander خودش
    if snap["use_leverage"]:
        with st.expander("💀 فاصله تا لیکویید — جزئیات", expanded=bool(result["liq_status"] != "ok")):
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
                f"💡 {mmr_part} در Short، لیکویید با رشد قیمت رخ می‌دهد؛ در Long با افت قیمت. "
                "مقدار واقعی به سطح ریسک پوزیشن، کارمزد، فاندینگ و مارجین اضافه‌شده هم بستگی دارد."
            )

    # 📖 توضیح ردیف‌ها — جمع و جور در یک expander
    with st.expander("📖 توضیح ردیف‌های جدول", expanded=False):
        if snap["qty_enabled"]:
            st.markdown("💰 **ردیف اول:** ریسک دلاری برنامه‌ریزی‌شده (حداکثر ضرر مجاز، قبل از گرد کردن و هزینه‌ها).")
            st.markdown(
                f"🪙 **ردیف حجم:** سایز پوزیشن ÷ قیمت ورود ({snap['entry_price']:g}) و گرد شده به پایین "
                f"تا مضرب stepSize ({snap['qty_step']:g}) — دقیقاً همان عددی که در صرافی وارد می‌کنید."
                + (f" چک minQty ({snap['min_qty']:g}) هم انجام شده است." if snap["min_qty"] else "")
            )
        else:
            st.markdown("💡 **ردیف اول (ریسک دلاری):** حداکثر مبلغی که در صورت رسیدن به حد ضرر از دست می‌دهید.")
            st.markdown("🚀 **ردیف دوم (سایز پوزیشن):** ارزش کل دلاری معامله. برای عدد قابل اجرا در صرافی، گزینه «گرد کردن حجم به stepSize» را فعال کنید.")

        if snap["fees_on"]:
            st.markdown(
                f"📝 ردیف‌های «واقعی/خالص» شامل کارمزد taker ({snap['fee']:.2f}٪ هر طرف) و اسلیپیج "
                f"({snap['slippage']:.2f}٪ هر طرف، نامساعد در ورود و خروج) هستند — برای {dir_label} هم درست کار می‌کند. "
                "سایز پوزیشن تغییر نکرده — فقط اثر هزینه‌ها جداگانه نشان داده شده است."
            )

        if snap["use_leverage"]:
            st.markdown(f"💳 **مارجین لازم** با اهرم {snap['leverage']:.0f}×: سایز پوزیشن ÷ {snap['leverage']:.0f}")

        if snap["tp"] is not None:
            if snap["fees_on"]:
                st.markdown(f"🪙 **سود خالص:** بعد از کسر کارمزد و اسلیپیج. R:R خالص = سود خالص ÷ ضرر واقعی.")
            else:
                st.markdown(f"💵 **ردیف سود:** اگر قیمت به حد سود ({snap['tp']:.2f}٪) برسد، این مبلغ را سود می‌کنید.")
                st.markdown("⚖️ **R:R:** سود تقسیم بر ریسک. بالاتر بهتر است، اما به‌تنهایی تضمین سودآوری نیست؛ نرخ برد و کارمزد هم مهم‌اند.")

        if snap["direction"] == "short":
            st.caption("💡 مدل Short برای فیوچرز/مارژین است. شورت اسپات هزینه قرض‌گیری (Borrow) جداگانه دارد که لحاظ نشده.")
        elif snap["fees_on"]:
            st.caption("💡 مدل هزینه‌ها: کارمزد taker روی ارزش واقعی ورود و خروج + اسلیپیج نامساعد در هر دو طرف. maker fee، فاندینگ و هزینه لیکویید لحاظ نشده‌اند.")
        else:
            st.caption("💡 محاسبات برای بازارهای Spot و فیوچرز خطی (Linear) است؛ کارمزد و اسلیپیج لحاظ نشده‌اند — برای دیدن اثر واقعی، بخش «کارمزد و اسلیپیج» را فعال کنید.")


if __name__ == "__main__":
    main()
