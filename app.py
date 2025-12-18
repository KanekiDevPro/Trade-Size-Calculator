import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Tuple, Optional
from decimal import Decimal, InvalidOperation

# --- تنظیمات صفحه ---
st.set_page_config(
    page_title="مدیریت سرمایه حرفه‌ای",
    page_icon="💎",
    layout="centered"
)

# --- استایل CSS ---
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
        
        /* تب‌ها */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center;
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: bold;
        }
        
        /* متریک‌ها */
        div[data-testid="stMetric"] {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 10px;
            border-radius: 8px;
            text-align: center !important;
            direction: ltr !important; /* اعداد چپ چین */
        }
        div[data-testid="stMetricLabel"] {
            direction: rtl !important;
            text-align: center !important;
            font-size: 14px;
            font-weight: bold;
        }

        /* اینپوت‌ها */
        div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input {
            direction: ltr !important; 
            text-align: center !important;
            font-weight: 500;
        }

        /* دکمه */
        div[data-testid="stButton"] button {
            width: 100%;
            border-radius: 10px;
            font-weight: bold;
            font-size: 16px;
            padding: 0.5rem 1rem;
        }
        
        /* جداول */
        div[data-testid="stDataFrame"] table thead tr th {
            background-color: #f1f3f5 !important;
            text-align: center !important;
        }
        div[data-testid="stDataFrame"] table tbody tr td {
            text-align: center !important;
            font-family: 'Courier New', monospace !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# --- توابع کمکی ---
def validate_price_inputs(entry: float, sl: float, tp: float) -> Optional[str]:
    if entry <= 0 or sl <= 0:
        return "قیمت ورود و حد ضرر باید مثبت باشند."
    if entry == sl:
        return "قیمت ورود نمی‌تواند برابر با حد ضرر باشد."
    if tp > 0:
        if (entry > sl and tp <= entry) or (entry < sl and tp >= entry):
            return "قیمت تارگت با جهت معامله (Long/Short) همخوانی ندارد."
    return None

def calculate_advanced_position(
    capital: float, risk_percent: float, leverage: float,
    entry: float, sl: float, tp: float, fee_rate: float
):
    try:
        # تشخیص جهت
        is_long = entry > sl
        direction = "LONG 🟢" if is_long else "SHORT 🔴"
        
        # محاسبه فاصله درصدی استاپ
        price_diff = abs(entry - sl)
        sl_percent = (price_diff / entry)
        
        if sl_percent == 0: return None, "فاصله استاپ صفر است"

        # محاسبه حجم
        risk_amount = capital * (risk_percent / 100)
        # حجم کل پوزیشن (USDT) = ریسک دلاری / درصد استاپ
        position_size_usdt = risk_amount / sl_percent
        
        # مقدار کوین/ارز
        position_qty = position_size_usdt / entry
        
        # مارجین درگیر
        margin = position_size_usdt / leverage
        
        # محاسبات تارگت و R/R
        rr_ratio = 0.0
        potential_profit = 0.0
        net_profit = 0.0
        total_fee = 0.0
        
        if tp > 0:
            tp_diff = abs(tp - entry)
            rr_ratio = tp_diff / price_diff
            
            # سود ناخالص
            potential_profit = position_size_usdt * (tp_diff / entry)
            
            # تخمین کارمزد (ورود + خروج)
            # فرض: کارمزد روی حجم کل اعمال میشه
            open_fee = position_size_usdt * (fee_rate / 100)
            close_fee = (position_qty * tp) * (fee_rate / 100)
            total_fee = open_fee + close_fee
            
            net_profit = potential_profit - total_fee

        return {
            "direction": direction,
            "sl_percent": sl_percent * 100,
            "position_size_usdt": position_size_usdt,
            "position_qty": position_qty,
            "margin": margin,
            "risk_amount": risk_amount,
            "rr_ratio": rr_ratio,
            "net_profit": net_profit,
            "total_fee": total_fee,
            "potential_profit": potential_profit
        }, None

    except Exception as e:
        return None, str(e)

# --- تابع اصلی ---
def main():
    inject_custom_css()

    st.title('💎 دستیار تریدر حرفه‌ای')
    st.markdown("محاسبه دقیق سایز پوزیشن، مدیریت ریسک و کارمزدها")
    
    # تنظیمات عمومی (بالای تب‌ها)
    with st.expander("⚙️ تنظیمات سرمایه و اهرم", expanded=True):
        col_cap, col_lev, col_fee = st.columns(3)
        with col_cap:
            capital = st.number_input('سرمایه کل (USDT)', value=1000.0, step=100.0, format="%.0f")
        with col_lev:
            leverage = st.number_input('اهرم (Leverage)', value=10, min_value=1, max_value=125)
        with col_fee:
            fee_rate = st.number_input('کارمزد صرافی (%)', value=0.04, step=0.01, format="%.3f", help="مجموع کارمزد باز و بسته کردن (حدودی)")

    # تب‌بندی
    tab_price, tab_percent = st.tabs(["📊 محاسبه قیمتی (Entry/SL)", "🧮 محاسبه درصدی (کلاسیک)"])

    # --- تب اول: محاسبه قیمتی (جدید) ---
    with tab_price:
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            entry_price = st.number_input('قیمت ورود (Entry)', min_value=0.0, format="%.4f")
        with col_p2:
            sl_price = st.number_input('حد ضرر (Stop Loss)', min_value=0.0, format="%.4f")
        with col_p3:
            tp_price = st.number_input('حد سود (Take Profit)', min_value=0.0, format="%.4f", help="اختیاری")

        risk_per_trade = st.slider('ریسک در هر معامله (%)', 0.1, 5.0, 1.0, 0.1)

        if st.button('محاسبه پوزیشن', key='btn_price', type="primary"):
            val_err = validate_price_inputs(entry_price, sl_price, tp_price)
            if val_err:
                st.error(f"❌ {val_err}")
            else:
                res, err = calculate_advanced_position(capital, risk_per_trade, leverage, entry_price, sl_price, tp_price, fee_rate)
                if err:
                    st.error(f"خطا: {err}")
                else:
                    # نمایش نتایج
                    st.divider()
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("جهت معامله", res['direction'])
                    c2.metric("حجم کل (USDT)", f"${res['position_size_usdt']:,.2f}")
                    c3.metric("مارجین لازم", f"${res['margin']:,.2f}")
                    c4.metric("ریسک دلاری", f"${res['risk_amount']:,.2f}", delta=f"-{res['sl_percent']:.2f}%")

                    # ردیف دوم اطلاعات
                    st.markdown("---")
                    cc1, cc2, cc3 = st.columns(3)
                    
                    if res['rr_ratio'] > 0:
                        cc1.metric("ریسک به ریوارد (R/R)", f"1 : {res['rr_ratio']:.2f}")
                        cc2.metric("سود خالص (با کسر کارمزد)", f"${res['net_profit']:,.2f}", delta_color="normal")
                        cc3.metric("کارمزد کل (تخمینی)", f"${res['total_fee']:,.2f}")
                        
                        # گیج چارت ساده برای R/R
                        fig = go.Figure(go.Indicator(
                            mode = "gauge+number",
                            value = res['rr_ratio'],
                            title = {'text': "کیفیت معامله (R/R)"},
                            gauge = {
                                'axis': {'range': [0, 5]},
                                'bar': {'color': "#00cc96" if res['rr_ratio'] >= 2 else "#ffa600"},
                                'steps': [
                                    {'range': [0, 1], 'color': "#ffefef"},
                                    {'range': [1, 2], 'color': "#fff8e1"},
                                    {'range': [2, 5], 'color': "#e6fffa"}],
                            }
                        ))
                        fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        cc1.info("برای محاسبه سود، قیمت تارگت را وارد کنید.")
                    
                    st.code(f"{res['position_qty']:.6f}", language="text")
                    st.caption("👆 مقدار دارایی (Qty) برای کپی در صرافی")

    # --- تب دوم: محاسبه درصدی (کد بهینه‌شده قبلی) ---
    with tab_percent:
        col_sl_pct, col_risk_lvl = st.columns(2)
        with col_sl_pct:
            stop_loss_pct = st.number_input('فاصله حد ضرر (%)', 0.1, 100.0, 1.5, 0.1)
        with col_risk_lvl:
            risk_levels_str = st.text_input("سطوح ریسک (مثال: 1, 2, 3)", "0.5, 1, 2")

        if st.button('محاسبه جدول', key='btn_pct'):
            try:
                r_levels = [float(x.strip()) for x in risk_levels_str.split(',') if x.strip()]
                data = []
                for r in r_levels:
                    risk_amt = capital * (r / 100)
                    pos_size = risk_amt / (stop_loss_pct / 100)
                    margin_req = pos_size / leverage
                    data.append({
                        "ریسک (%)": f"{r}%",
                        "ریسک ($)": f"${risk_amt:,.1f}",
                        "حجم پوزیشن ($)": f"${pos_size:,.1f}",
                        "مارجین ($)": f"${margin_req:,.1f}"
                    })
                
                df = pd.DataFrame(data)
                st.table(df)
                st.info(f"💡 در این حالت، فاصله استاپ شما **{stop_loss_pct}%** از قیمت ورود فرض شده است.")
            except:
                st.error("فرمت ورودی ریسک صحیح نیست.")

    # --- فوتر ---
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888; font-size: 12px;">
            <p>این ابزار صرفاً جهت محاسبات ریاضی است و پیشنهاد مالی نیست.</p>
            <p style='opacity: 0.6;'>نسخه حرفه‌ای 2.0</p>
        </div>
        """, unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
