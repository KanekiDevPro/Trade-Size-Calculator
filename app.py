import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- تنظیمات صفحه ---
st.set_page_config(
    page_title="مدیریت سرمایه پرو",
    page_icon="💎",
    layout="centered"
)

# --- استایل CSS تمیز و بدون باگ ---
st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

    /* فونت کل صفحه */
    html, body, [class*="st-"] {
        font-family: "Vazirmatn", sans-serif !important;
    }

    /* تیترها وسط چین */
    h1, h2, h3 {
        text-align: center !important;
        direction: rtl !important;
    }

    /* متن‌های عادی راست چین */
    .stMarkdown p, .stText, .stAlert {
        direction: rtl !important;
        text-align: right !important;
        line-height: 1.8 !important;
    }

    /* تب‌ها */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: bold;
    }

    /* اینپوت‌ها: اعداد وسط چین باشند تا تایپ راحت باشد */
    div[data-testid="stNumberInput"] input {
        text-align: center !important;
        direction: ltr !important; 
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    /* لیبل اینپوت‌ها (عنوان بالای کادر) */
    div[data-testid="stNumberInput"] label {
        display: block;
        text-align: center !important; /* وسط چین برای زیبایی */
        width: 100%;
        font-size: 0.9rem;
    }

    /* متریک‌ها */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center !important;
    }
    div[data-testid="stMetricLabel"] {
        justify-content: center !important;
        direction: rtl;
    }
    div[data-testid="stMetricValue"] {
        direction: ltr; /* اعداد انگلیسی نمایش داده شوند */
    }

    /* دکمه */
    div[data-testid="stButton"] button {
        width: 100%;
        border-radius: 12px;
        padding: 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- منطق محاسبات ---
def calculate_trade(capital, leverage, entry, sl, tp, fee):
    if entry <= 0 or sl <= 0: return None, "قیمت‌ها باید بیشتر از صفر باشند"
    if entry == sl: return None, "نقطه ورود و استاپ نمی‌توانند برابر باشند"

    is_long = entry > sl
    direction = "LONG 🟢" if is_long else "SHORT 🔴"
    
    # فاصله استاپ به درصد
    diff = abs(entry - sl)
    sl_percent_raw = diff / entry
    
    # ریسک مدیریت شده (مثلاً ۱ درصد سرمایه)
    # اینجا برای سادگی فرض میکنیم کاربر ریسک ۱٪ ثابت میخواهد، یا میتوانیم اسلایدر بگذاریم
    # فعلا بر اساس اهرم محاسبه میکنیم:
    
    # سایز پوزیشن خام
    # فرمول ساده: ما میخواهیم اهرم فقط قدرت خرید بدهد. 
    # اما روش درست: Capital * Leverage = Total Buying Power
    # ولی ما اینجا برعکس عمل میکنیم: چقدر بخریم که اگر استاپ خوردیم، X دلار ضرر کنیم؟
    
    return {
        "dir": direction,
        "sl_pct": sl_percent_raw * 100,
        "diff": diff
    }, None

# --- بدنه اصلی ---

st.title("💎 ماشین حساب ترید")
st.caption("ورود، استاپ و تارگت را وارد کنید | محاسبه خودکار لانگ/شورت")

st.markdown("---")

# بخش ورودی‌ها (به صورت کارتی و مرتب)
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        capital = st.number_input("سرمایه (USDT)", value=1000.0, step=100.0, format="%.0f")
    with c2:
        leverage = st.number_input("اهرم (Lev)", value=10, min_value=1, max_value=125)
    with c3:
        risk_pct = st.number_input("ریسک (%)", value=1.0, step=0.1, format="%.1f")

st.markdown("<br>", unsafe_allow_html=True) # فاصله

col_entry, col_sl, col_tp = st.columns(3)
with col_entry:
    entry = st.number_input("قیمت ورود", value=0.0, format="%.4f", step=0.0001)
with col_sl:
    sl = st.number_input("حد ضرر (SL)", value=0.0, format="%.4f", step=0.0001)
with col_tp:
    tp = st.number_input("تارگت (TP)", value=0.0, format="%.4f", step=0.0001)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("✨ محاسبه کن", type="primary"):
    if entry == 0 or sl == 0:
        st.error("لطفاً قیمت ورود و حد ضرر را وارد کنید.")
    else:
        # محاسبات ریاضی
        is_long = entry > sl
        direction_text = "LONG (خرید)" if is_long else "SHORT (فروش)"
        direction_color = "green" if is_long else "red"
        
        # درصد فاصله استاپ
        price_diff = abs(entry - sl)
        sl_percent = (price_diff / entry) # اعشاری
        
        # ریسک دلاری (چقدر حاضریم ببازیم؟)
        risk_dollar = capital * (risk_pct / 100)
        
        # حجم پوزیشن (تتر) = ریسک دلاری تقسیم بر درصد استاپ
        # فرمول: PositionSize = RiskAmount / StopLoss%
        position_size = risk_dollar / sl_percent
        
        # مارجین (پول درگیر)
        margin = position_size / leverage
        
        # مقدار کوین (Qty)
        qty = position_size / entry
        
        # خروجی R/R
        rr_val = 0
        pnl_win = 0
        if tp > 0:
            tp_diff = abs(tp - entry)
            rr_val = tp_diff / price_diff
            pnl_win = position_size * (tp_diff / entry)

        # --- نمایش نتایج ---
        st.success(f"سیگنال تشخیص داده شده: **{direction_text}**")
        
        # ردیف اول: اطلاعات اصلی
        m1, m2, m3 = st.columns(3)
        m1.metric("حجم پوزیشن (Total)", f"${position_size:,.1f}")
        m2.metric("مارجین (Cost)", f"${margin:,.1f}")
        m3.metric("مقدار دارایی (Qty)", f"{qty:.4f}")
        
        st.divider()
        
        # ردیف دوم: اطلاعات ریسک و سود
        r1, r2, r3 = st.columns(3)
        r1.metric("ریسک شما (Loss)", f"${risk_dollar:,.1f}", f"-{sl_percent*100:.2f}% Stop", delta_color="inverse")
        
        if tp > 0:
            r2.metric("سود احتمالی (Win)", f"${pnl_win:,.1f}", f"+{rr_val:.2f} R/R")
            
            # نمودار گرافیکی R/R
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = rr_val,
                title = {'text': "R/R Ratio"},
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [0, 5]},
                    'bar': {'color': "#2ecc71" if rr_val >= 2 else "#f1c40f"},
                    'steps': [{'range': [0, 1], 'color': "#ffdad9"}]
                }
            ))
            fig.update_layout(height=200, margin=dict(t=30, b=10, l=30, r=30))
            r3.plotly_chart(fig, use_container_width=True)
        else:
            r2.info("تارگت وارد نشده")

st.markdown(
    """
    <div style="text-align: center; margin-top: 50px; color: #aaa; font-size: 12px;">
    طراحی شده برای ترید حرفه‌ای
    </div>
    """, unsafe_allow_html=True
)
