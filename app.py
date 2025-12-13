import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime
import json
import io

# سعی در import plotly (اختیاری)
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

st.set_page_config(
    page_title="ماشین حساب مدیریت سرمایه",
    page_icon="🤖",
    layout="wide"
)

@st.cache_data
def inject_custom_css():
    """بارگذاری CSS سفارشی"""
    st.markdown(
        """
        <style>
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

        * {
            font-family: "Vazirmatn", sans-serif !important;
        }

        html, body, [class*="st-"] {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
            text-align: right;
        }

        h1, h2, h3, h4 {
            font-family: "Vazirmatn", sans-serif !important;
            text-align: right !important;
            direction: rtl !important;
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
            font-family: "Vazirmatn", sans-serif !important;
        }
        
        div[data-testid="stTextInput"] input {
            direction: ltr !important;
            text-align: left !important;
            font-family: "Vazirmatn", sans-serif !important;
        }

        div[data-testid="stButton"] { 
            text-align: center !important;
            width: 100%;
        }
        
        .stButton button {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
            width: 100%;
            border-radius: 8px;
            font-weight: bold;
            white-space: nowrap !important;
        }
        
        button {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
            white-space: nowrap !important;
        }
        
        .stDownloadButton button {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
            width: 100%;
            white-space: nowrap !important;
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
        
        div[data-testid="stCheckbox"] label {
            font-family: "Vazirmatn", sans-serif !important;
        }
        
        .stTabs {
            direction: rtl !important;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            direction: rtl !important;
            display: flex;
            flex-direction: row-reverse;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
            white-space: nowrap !important;
        }
        
        .stTabs [data-baseweb="tab"] div {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
        }
        
        div[data-testid="stExpander"] {
            direction: rtl !important;
        }
        
        div[data-testid="stExpander"] summary {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
        }
        
        .stSelectbox label, .stNumberInput label, .stTextInput label {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
        }
        
        select {
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def init_session_state():
    """مقداردهی اولیه session state"""
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'saved_settings' not in st.session_state:
        st.session_state.saved_settings = {
            'capital': 1000.0,
            'stop_loss': 1.5,
            'leverage': 1.0,
            'risk_levels': '0.25, 0.5, 1.0, 2.0'
        }

def validate_inputs(capital: float, stop_loss_percentage: float, risk_levels: List[float], leverage: float) -> Optional[str]:
    """اعتبارسنجی ورودی‌ها"""
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
    """تبدیل رشته ورودی به لیست اعداد"""
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
                    return None, f"مقدار '{part}' معتبر نیست."
        
        if not risk_levels:
            return None, "لطفاً حداقل یک سطح ریسک معتبر وارد کنید."
        
        risk_levels = sorted(set(risk_levels))
        return risk_levels, None
        
    except Exception as e:
        return None, f"خطا در پردازش: {str(e)}"

def calculate_sl_from_prices(entry_price: float, sl_price: float, position_type: str) -> float:
    """محاسبه درصد SL از قیمت ورود و خروج"""
    if position_type == "Long":
        return abs((entry_price - sl_price) / entry_price * 100)
    else:  # Short
        return abs((sl_price - entry_price) / entry_price * 100)

def calculate_rr_ratio(entry_price: float, sl_price: float, tp_price: float, position_type: str) -> float:
    """محاسبه نسبت ریسک به ریوارد"""
    if position_type == "Long":
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
    else:  # Short
        risk = abs(sl_price - entry_price)
        reward = abs(entry_price - tp_price)
    
    if risk == 0:
        return 0
    return reward / risk

def create_risk_management_table(
    capital: float, 
    stop_loss_percentage: float, 
    risk_levels: List[float],
    leverage: float = 1.0
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """محاسبه جدول مدیریت ریسک"""
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
        
        if leverage > 1:
            index_labels = ['💰 میزان ریسک', '📊 سایز پوزیشن', '💳 مارجین لازم']
        else:
            index_labels = ['💰 میزان ریسک', '📊 سایز پوزیشن']
        
        df = pd.DataFrame(data, index=index_labels)
        return df, None
        
    except (InvalidOperation, ValueError, ZeroDivisionError) as e:
        return None, f"خطا در محاسبات: {str(e)}"

def create_visualization(df: pd.DataFrame, leverage: float):
    """ایجاد نمودار تعاملی"""
    if not PLOTLY_AVAILABLE:
        return None
    
    fig = go.Figure()
    
    risk_levels = [col.replace('%', '') for col in df.columns]
    position_sizes = df.iloc[1].values
    
    fig.add_trace(go.Scatter(
        x=risk_levels,
        y=position_sizes,
        mode='lines+markers',
        name='سایز پوزیشن',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=10)
    ))
    
    if leverage > 1:
        margin_values = df.iloc[2].values
        fig.add_trace(go.Scatter(
            x=risk_levels,
            y=margin_values,
            mode='lines+markers',
            name='مارجین لازم',
            line=dict(color='#ff7f0e', width=3, dash='dash'),
            marker=dict(size=10)
        ))
    
    fig.update_layout(
        title=dict(text='نمودار رابطه ریسک و سایز پوزیشن', font=dict(family="Vazirmatn", size=18)),
        xaxis_title='درصد ریسک (%)',
        yaxis_title='مبلغ (USD)',
        font=dict(family="Vazirmatn", size=14),
        hovermode='x unified',
        height=400
    )
    
    return fig

def save_to_history(capital, stop_loss, leverage, risk_levels, table_df):
    """ذخیره محاسبه در تاریخچه"""
    entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'capital': capital,
        'stop_loss': stop_loss,
        'leverage': leverage,
        'risk_levels': risk_levels,
        'table': table_df.to_dict()
    }
    st.session_state.history.insert(0, entry)
    if len(st.session_state.history) > 10:
        st.session_state.history = st.session_state.history[:10]

def export_to_csv(df: pd.DataFrame) -> bytes:
    """تبدیل DataFrame به CSV"""
    output = io.StringIO()
    df.to_csv(output, encoding='utf-8-sig')
    return output.getvalue().encode('utf-8-sig')

def main():
    inject_custom_css()
    init_session_state()

    st.title('🤖 ماشین حساب مدیریت سرمایه - نسخه پیشرفته')
    st.markdown("ابزار کامل محاسبه سایز پوزیشن با قابلیت‌های پیشرفته")
    
    # تب‌ها
    tab1, tab2, tab3, tab4 = st.tabs(['📊 محاسبه اصلی', '🔄 محاسبه معکوس', '📈 چند معامله', '📜 تاریخچه'])
    
    # تب 1: محاسبه اصلی
    with tab1:
        col_left, col_right = st.columns([2, 1])
        
        with col_right:
            st.subheader('⚙️ تنظیمات')
            
            if st.button('📥 بارگذاری تنظیمات ذخیره شده'):
                st.success('تنظیمات بارگذاری شد!')
            
            with st.expander('💾 ذخیره تنظیمات فعلی'):
                if st.button('ذخیره'):
                    st.session_state.saved_settings = {
                        'capital': st.session_state.get('capital', 1000.0),
                        'stop_loss': st.session_state.get('stop_loss', 1.5),
                        'leverage': st.session_state.get('leverage', 1.0),
                        'risk_levels': st.session_state.get('risk_levels', '0.25, 0.5, 1.0, 2.0')
                    }
                    st.success('✅ تنظیمات ذخیره شد!')
        
        with col_left:
            st.subheader('🔢 ورودی‌های اصلی')
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                capital = st.number_input(
                    'سرمایه کل (USD)', 
                    min_value=0.01, 
                    value=st.session_state.saved_settings['capital'],
                    step=100.0,
                    format="%.0f",
                    key='capital'
                )
            
            with col2:
                use_price_calc = st.checkbox('محاسبه SL از قیمت', value=False)
                
                if use_price_calc:
                    position_type = st.selectbox('نوع پوزیشن', ['Long', 'Short'])
                    entry_price = st.number_input('قیمت ورود', min_value=0.01, value=100.0, step=1.0)
                    sl_price = st.number_input('قیمت حد ضرر', min_value=0.01, value=98.5, step=0.1)
                    stop_loss_percentage = calculate_sl_from_prices(entry_price, sl_price, position_type)
                    st.info(f'📊 درصد SL محاسبه شده: **{stop_loss_percentage:.2f}%**')
                else:
                    stop_loss_percentage = st.number_input(
                        'حد ضرر معامله (٪)', 
                        min_value=0.01,
                        max_value=99.99,
                        value=st.session_state.saved_settings['stop_loss'],
                        step=0.1,
                        format="%.2f",
                        key='stop_loss'
                    )
            
            with col3:
                use_leverage = st.checkbox('⚡ استفاده از اهرم', value=False)
                
                if use_leverage:
                    leverage = st.number_input(
                        'مقدار اهرم (×)',
                        min_value=1.0,
                        max_value=125.0,
                        value=st.session_state.saved_settings['leverage'],
                        step=1.0,
                        format="%.0f",
                        key='leverage'
                    )
                    st.warning(f"⚠️ اهرم {leverage:.0f}× فعال است!")
                else:
                    leverage = 1.0

            # محاسبه Risk/Reward
            with st.expander('📈 محاسبه نسبت ریسک به ریوارد (اختیاری)'):
                calc_rr = st.checkbox('فعال‌سازی محاسبه R/R')
                if calc_rr:
                    rr_col1, rr_col2, rr_col3 = st.columns(3)
                    with rr_col1:
                        rr_position = st.selectbox('نوع', ['Long', 'Short'], key='rr_type')
                    with rr_col2:
                        rr_entry = st.number_input('قیمت ورود', min_value=0.01, value=100.0, key='rr_entry')
                        rr_sl = st.number_input('حد ضرر', min_value=0.01, value=98.0, key='rr_sl')
                    with rr_col3:
                        rr_tp = st.number_input('حد سود', min_value=0.01, value=106.0, key='rr_tp')
                    
                    rr_ratio = calculate_rr_ratio(rr_entry, rr_sl, rr_tp, rr_position)
                    
                    if rr_ratio >= 2:
                        st.success(f'✅ نسبت R/R: **1:{rr_ratio:.2f}** - عالی!')
                    elif rr_ratio >= 1:
                        st.info(f'📊 نسبت R/R: **1:{rr_ratio:.2f}** - قابل قبول')
                    else:
                        st.error(f'❌ نسبت R/R: **1:{rr_ratio:.2f}** - ضعیف!')

            risk_inputs_str = st.text_input(
                "سطوح ریسک (٪):",
                value=st.session_state.saved_settings['risk_levels'],
                key='risk_levels'
            )

            if st.button('🧮 محاسبه کن', type="primary"):
                risk_levels, parse_error = parse_risk_levels(risk_inputs_str)
                
                if parse_error:
                    st.error(f"❌ {parse_error}")
                else:
                    table_df, calc_error = create_risk_management_table(
                        capital, stop_loss_percentage, risk_levels, leverage
                    )

                    if calc_error:
                        st.error(f"❌ {calc_error}")
                    else:
                        st.success("✅ محاسبات با موفقیت انجام شد.")
                        
                        # ذخیره در تاریخچه
                        save_to_history(capital, stop_loss_percentage, leverage, risk_levels, table_df)
                        
                        # متریک‌ها
                        if use_leverage:
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("سرمایه", f"${capital:,.0f}")
                            m2.metric("حد ضرر", f"{stop_loss_percentage:.2f}%")
                            m3.metric("اهرم", f"{leverage:.0f}×")
                            m4.metric("سطوح", len(risk_levels))
                        else:
                            m1, m2, m3 = st.columns(3)
                            m1.metric("سرمایه", f"${capital:,.0f}")
                            m2.metric("حد ضرر", f"{stop_loss_percentage:.2f}%")
                            m3.metric("سطوح", len(risk_levels))

                        st.divider()
                        
                        # جدول و نمودار
                        chart_col, table_col = st.columns([1, 1])
                        
                        with table_col:
                            st.subheader("📊 جدول سایز پوزیشن")
                            st.dataframe(
                                table_df.style.format("${:,.2f}"), 
                                use_container_width=True
                            )
                            
                            # دانلود CSV
                            csv_data = export_to_csv(table_df)
                            st.download_button(
                                label="📥 دانلود جدول (CSV)",
                                data=csv_data,
                                file_name=f"position_sizing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        
                        with chart_col:
                            st.subheader("📈 نمودار بصری")
                            if PLOTLY_AVAILABLE:
                                fig = create_visualization(table_df, leverage)
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning('📊 برای نمایش نمودار، Plotly را نصب کنید: `pip install plotly`')
                        
                        # راهنما
                        st.info("💡 **میزان ریسک:** حداکثر ضرر در صورت فعال شدن SL")
                        st.info("📊 **سایز پوزیشن:** ارزش کل معامله")
                        if use_leverage:
                            st.info(f"💳 **مارجین لازم:** با اهرم {leverage:.0f}×، فقط این مقدار نیاز است!")
    
    # تب 2: محاسبه معکوس
    with tab2:
        st.subheader('🔄 محاسبه معکوس - از مارجین به سایز')
        st.markdown('وقتی میزان مارجین موجود خود را می‌دانید و می‌خواهید ببینید چه سایز پوزیشنی می‌توانید باز کنید.')
        
        rev_col1, rev_col2, rev_col3 = st.columns(3)
        
        with rev_col1:
            available_margin = st.number_input('مارجین موجود (USD)', min_value=0.01, value=100.0, step=10.0)
        
        with rev_col2:
            rev_sl = st.number_input('حد ضرر (٪)', min_value=0.01, value=2.0, step=0.1, key='rev_sl')
        
        with rev_col3:
            rev_leverage = st.number_input('اهرم (×)', min_value=1.0, value=10.0, step=1.0, key='rev_lev')
        
        rev_risk = st.number_input('درصد ریسک از کل سرمایه (٪)', min_value=0.01, value=1.0, step=0.1)
        
        if st.button('🔄 محاسبه معکوس'):
            total_capital_needed = (available_margin * 100) / rev_risk
            position_size = available_margin * rev_leverage
            dollar_risk = (position_size * rev_sl) / 100
            
            st.success('✅ نتایج محاسبه معکوس:')
            
            res1, res2, res3, res4 = st.columns(4)
            res1.metric('سرمایه کل لازم', f'${total_capital_needed:,.2f}')
            res2.metric('سایز پوزیشن', f'${position_size:,.2f}')
            res3.metric('میزان ریسک', f'${dollar_risk:,.2f}')
            res4.metric('درصد از سرمایه', f'{rev_risk}%')
    
    # تب 3: چند معامله همزمان
    with tab3:
        st.subheader('📈 مدیریت چند معامله همزمان')
        
        num_trades = st.number_input('تعداد معاملات همزمان', min_value=1, max_value=10, value=3, step=1)
        
        mt_capital = st.number_input('سرمایه کل (USD)', min_value=0.01, value=1000.0, step=100.0, key='mt_cap')
        
        trades_data = []
        
        for i in range(num_trades):
            with st.expander(f'معامله #{i+1}'):
                t_col1, t_col2, t_col3 = st.columns(3)
                
                with t_col1:
                    t_risk = st.number_input(f'ریسک (٪)', min_value=0.01, value=0.5, step=0.1, key=f't_risk_{i}')
                
                with t_col2:
                    t_sl = st.number_input(f'حد ضرر (٪)', min_value=0.01, value=2.0, step=0.1, key=f't_sl_{i}')
                
                with t_col3:
                    t_lev = st.number_input(f'اهرم (×)', min_value=1.0, value=1.0, step=1.0, key=f't_lev_{i}')
                
                dollar_risk = (mt_capital * t_risk) / 100
                position_size = dollar_risk / (t_sl / 100)
                margin_needed = position_size / t_lev
                
                trades_data.append({
                    'معامله': f'#{i+1}',
                    'ریسک (٪)': t_risk,
                    'ریسک ($)': dollar_risk,
                    'سایز': position_size,
                    'مارجین': margin_needed
                })
        
        if st.button('💼 محاسبه کل پورتفولیو'):
            trades_df = pd.DataFrame(trades_data)
            
            total_risk = trades_df['ریسک ($)'].sum()
            total_margin = trades_df['مارجین'].sum()
            total_risk_percent = (total_risk / mt_capital) * 100
            
            st.success('✅ خلاصه پورتفولیو:')
            
            p1, p2, p3, p4 = st.columns(4)
            p1.metric('مجموع ریسک', f'${total_risk:,.2f}')
            p2.metric('درصد ریسک کل', f'{total_risk_percent:.2f}%')
            p3.metric('مجموع مارجین', f'${total_margin:,.2f}')
            p4.metric('مارجین آزاد', f'${mt_capital - total_margin:,.2f}')
            
            st.dataframe(trades_df.style.format({
                'ریسک ($)': '${:,.2f}',
                'سایز': '${:,.2f}',
                'مارجین': '${:,.2f}'
            }), use_container_width=True)
            
            if total_risk_percent > 5:
                st.error('⚠️ هشدار: ریسک کل بیش از ۵٪ است!')
            elif total_risk_percent > 3:
                st.warning('⚠️ توجه: ریسک کل بالاتر از حد توصیه شده (۳٪) است.')
    
    # تب 4: تاریخچه
    with tab4:
        st.subheader('📜 تاریخچه محاسبات')
        
        if len(st.session_state.history) == 0:
            st.info('هنوز محاسبه‌ای ثبت نشده است.')
        else:
            for idx, entry in enumerate(st.session_state.history):
                with st.expander(f"🕐 {entry['timestamp']} - سرمایه: ${entry['capital']:,.0f}"):
                    h_col1, h_col2, h_col3 = st.columns(3)
                    h_col1.metric('سرمایه', f"${entry['capital']:,.0f}")
                    h_col2.metric('حد ضرر', f"{entry['stop_loss']:.2f}%")
                    h_col3.metric('اهرم', f"{entry['leverage']:.0f}×")
                    
                    hist_df = pd.DataFrame(entry['table'])
                    st.dataframe(hist_df.style.format("${:,.2f}"), use_container_width=True)
            
            if st.button('🗑️ پاک کردن تاریخچه'):
                st.session_state.history = []
                st.success('تاریخچه پاک شد!')
                st.rerun()

if __name__ == "__main__":
    main()
