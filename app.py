import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional
from decimal import Decimal, InvalidOperation

st.set_page_config(
    page_title="ماشین حساب مدیریت سرمایه",
    page_icon="🤖",
    layout="centered"
)

# Initialize session state for settings
if 'saved_settings' not in st.session_state:
    st.session_state.saved_settings = None
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# Theme colors
THEMES = {
    "بنفش": {"primary": "#667eea", "secondary": "#764ba2"},
    "آبی": {"primary": "#4facfe", "secondary": "#00f2fe"},
    "سبز": {"primary": "#11998e", "secondary": "#38ef7d"},
    "نارنجی": {"primary": "#f46b45", "secondary": "#eea849"},
    "صورتی": {"primary": "#ee9ca7", "secondary": "#ffdde1"}
}

if 'theme' not in st.session_state:
    st.session_state.theme = "بنفش"

@st.cache_data
def inject_custom_css(dark_mode: bool, theme_name: str):
    theme = THEMES[theme_name]
    
    if dark_mode:
        bg_color = "#1a1a1a"
        text_color = "#e0e0e0"
        card_bg = "#2d2d2d"
        table_header_bg = "#3a3a3a"
        input_bg = "#2d2d2d"
    else:
        bg_color = "#ffffff"
        text_color = "#333333"
        card_bg = "#f8f9fa"
        table_header_bg = "#f0f2f6"
        input_bg = "#ffffff"
    
    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');

        html, body, [class*="st-"], .stApp {{
            font-family: "Vazirmatn", sans-serif !important;
            direction: rtl !important;
            text-align: right;
            background-color: {bg_color} !important;
            color: {text_color} !important;
        }}

        h1, h2, h3, h4 {{
            font-family: "Vazirmatn", sans-serif !important;
            text-align: right !important;
            color: {text_color} !important;
        }}

        .stMarkdown, .stText, div[data-testid="stAlert"] {{
            text-align: right !important;
            direction: rtl !important;
        }}

        div[data-testid="stDataFrame"] table thead tr th, 
        div[data-testid="stDataFrame"] table tbody tr th,
        div[data-testid="stDataFrame"] table tbody tr td {{
            font-family: "Vazirmatn", sans-serif !important;
            text-align: center !important;
            font-size: 15px !important;
        }}
        
        div[data-testid="stDataFrame"] table tbody tr th {{
            text-align: right !important;
            font-weight: 600 !important;
        }}
        
        div[data-testid="stDataFrame"] table {{
            border-collapse: collapse !important;
        }}
        
        div[data-testid="stDataFrame"] table thead tr th {{
            background-color: {table_header_bg} !important;
            font-weight: 600 !important;
            padding: 12px 8px !important;
        }}
        
        div[data-testid="stDataFrame"] table tbody tr td {{
            padding: 10px 8px !important;
        }}
        
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextInput"] input {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
        }}
        
        div[data-testid="stNumberInput"] input {{
            direction: ltr !important; 
            text-align: center !important;
        }}
        
        div[data-testid="stTextInput"] input {{
            direction: ltr !important;
            text-align: left !important;
        }}

        div[data-testid="stButton"] {{ 
            text-align: right !important; 
            width: 100%; 
        }}
        
        .stButton button {{
            direction: rtl; 
            margin-left: auto;
            margin-right: 0;
            width: auto;
            border-radius: 8px;
            font-weight: bold;
        }}
        
        div[data-testid="stMetric"] {{
            direction: rtl !important;
            text-align: right !important;
            font-family: "Vazirmatn", sans-serif !important;
            background-color: {card_bg} !important;
            padding: 10px;
            border-radius: 8px;
        }}
        
        div[data-testid="stCheckbox"] {{
            direction: rtl !important;
            text-align: right !important;
        }}
        
        .stAlert {{
            background-color: {card_bg} !important;
        }}
        
        /* Mobile Responsive */
        @media (max-width: 768px) {{
            div[data-testid="column"] {{
                width: 100% !important;
                flex: 100% !important;
                margin-bottom: 1rem;
            }}
            
            .stButton button {{
                width: 100% !important;
                margin-bottom: 0.5rem;
            }}
        }}
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

def suggest_risk_level(capital: float) -> str:
    """پیشنهاد بهترین سطح ریسک بر اساس سرمایه"""
    if capital < 500:
        return "💡 **پیشنهاد هوشمند:** با سرمایه کمتر از ۵۰۰ دلار، ریسک ۰.۵٪ تا ۱٪ مناسب است."
    elif capital < 2000:
        return "💡 **پیشنهاد هوشمند:** با سرمایه ۵۰۰ تا ۲۰۰۰ دلار، ریسک ۱٪ تا ۱.۵٪ توصیه می‌شود."
    elif capital < 10000:
        return "💡 **پیشنهاد هوشمند:** با سرمایه ۲۰۰۰ تا ۱۰۰۰۰ دلار، می‌توانید ریسک ۱٪ تا ۲٪ بگیرید."
    else:
        return "💡 **پیشنهاد هوشمند:** با سرمایه بالای ۱۰۰۰۰ دلار، ریسک ۰.۵٪ تا ۱٪ برای حفظ سرمایه بهینه است."

def create_risk_management_table(
    capital: float, 
    stop_loss_percentage: float, 
    risk_levels: List[float],
    leverage: float = 1.0,
    take_profit_percentage: Optional[float] = None
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
            
            # With Take Profit
            if take_profit_percentage and take_profit_percentage > 0:
                tp_factor = Decimal(str(take_profit_percentage)) / Decimal('100')
                potential_profit = float(position_size_dec * tp_factor)
                risk_reward = float(tp_factor / sl_factor)
                
                if leverage > 1:
                    data[col_name] = [
                        dollar_risk,
                        position_size,
                        margin_required,
                        potential_profit,
                        risk_reward
                    ]
                else:
                    data[col_name] = [
                        dollar_risk,
                        position_size,
                        potential_profit,
                        risk_reward
                    ]
            else:
                if leverage > 1:
                    data[col_name] = [
                        dollar_risk,
                        position_size,
                        margin_required
                    ]
                else:
                    data[col_name] = [dollar_risk, position_size]
        
        # Create index labels
        if take_profit_percentage and take_profit_percentage > 0:
            if leverage > 1:
                index_labels = [
                    '💰 میزان ریسک',
                    '📊 سایز پوزیشن',
                    '💳 مارجین لازم (با اهرم)',
                    '💵 سود احتمالی (TP)',
                    '⚖️ نسبت R:R'
                ]
            else:
                index_labels = [
                    '💰 میزان ریسک',
                    '📊 سایز پوزیشن',
                    '💵 سود احتمالی (TP)',
                    '⚖️ نسبت R:R'
                ]
        else:
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

def save_settings(capital, stop_loss, leverage, risk_input, use_leverage):
    """ذخیره تنظیمات"""
    st.session_state.saved_settings = {
        'capital': capital,
        'stop_loss': stop_loss,
        'leverage': leverage,
        'risk_input': risk_input,
        'use_leverage': use_leverage
    }

def load_settings():
    """بارگذاری تنظیمات"""
    return st.session_state.saved_settings

def main():
    # Sidebar
    with st.sidebar:
        st.header("⚙️ تنظیمات")
        
        # Dark Mode
        dark_mode = st.checkbox(
            "🌙 حالت تاریک" if not st.session_state.dark_mode else "☀️ حالت روشن",
            value=st.session_state.dark_mode
        )
        st.session_state.dark_mode = dark_mode
        
        # Theme
        theme = st.selectbox(
            "🎨 تم رنگی",
            options=list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme)
        )
        st.session_state.theme = theme
        
        st.divider()
        
        # Saved Settings Display
        if st.session_state.saved_settings:
            st.subheader("💾 تنظیمات ذخیره‌شده")
            saved = st.session_state.saved_settings
            st.info(f"💰 سرمایه: ${saved['capital']:,.0f}\n\n"
                   f"📉 حد ضرر: {saved['stop_loss']:.2f}%\n\n"
                   f"⚡ اهرم: {saved['leverage']:.0f}×\n\n"
                   f"📊 ریسک‌ها: {saved['risk_input']}")
            
            if st.button("🗑️ پاک کردن", use_container_width=True):
                st.session_state.saved_settings = None
                st.rerun()
    
    inject_custom_css(st.session_state.dark_mode, st.session_state.theme)

    st.title('🤖 ماشین حساب مدیریت سرمایه')
    st.markdown("محاسبه دقیق **سایز پوزیشن** بر اساس سرمایه کل، درصد ریسک و اهرم.")
    
    st.divider()

    # Load saved settings
    saved = load_settings()
    default_capital = saved['capital'] if saved else 1000.0
    default_sl = saved['stop_loss'] if saved else 1.5
    default_leverage = saved['leverage'] if saved else 10.0
    default_risk = saved['risk_input'] if saved else "0.25, 0.5, 1.0, 2.0"
    default_use_leverage = saved['use_leverage'] if saved else False

    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            capital = st.number_input(
                'سرمایه کل (USD)', 
                min_value=0.01, 
                value=default_capital, 
                step=100.0,
                format="%.0f",
                help="مجموع سرمایه‌ای که برای معامله در اختیار دارید"
            )
        
        with col2:
            stop_loss_percentage = st.number_input(
                'حد ضرر معامله (٪)', 
                min_value=0.01,
                max_value=99.99,
                value=default_sl, 
                step=0.1,
                format="%.2f",
                help="درصد افت قیمت تا حد ضرر (مثلاً ۱.۵٪ یعنی SL در ۱.۵٪ پایین‌تر از قیمت ورود)"
            )

    # Smart Risk Suggestion
    st.info(suggest_risk_level(capital))

    use_leverage = st.checkbox('⚡ استفاده از اهرم (Leverage)', value=default_use_leverage)
    
    leverage = 1.0
    if use_leverage:
        leverage = st.number_input(
            'مقدار اهرم (×)',
            min_value=1.0,
            max_value=125.0,
            value=default_leverage,
            step=1.0,
            format="%.0f",
            help="اهرم معاملاتی (مثلاً 10× یعنی ده برابر قدرت خرید)"
        )
        
        st.warning(f"⚠️ **هشدار:** با اهرم {leverage:.0f}×، ریسک معامله شما {leverage:.0f} برابر می‌شود. با احتیاط استفاده کنید!")

    risk_inputs_str = st.text_input(
        "سطوح ریسک مورد نظر (٪) - با کاما جدا کنید:",
        value=default_risk,
        help="مثال: 0.5, 1, 2 یا 0.25, 0.5, 1, 1.5, 2, 3"
    )
    
    # Take Profit
    use_take_profit = st.checkbox('📈 محاسبه سود احتمالی (Take Profit)', value=False)
    
    take_profit_percentage = None
    if use_take_profit:
        take_profit_percentage = st.number_input(
            'هدف سود (٪)',
            min_value=0.01,
            max_value=1000.0,
            value=3.0,
            step=0.5,
            format="%.2f",
            help="درصد رشد قیمت تا هدف سود (مثلاً ۳٪ یعنی TP در ۳٪ بالاتر از قیمت ورود)"
        )

    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        calculate_btn = st.button('🧮 محاسبه کن', type="primary", use_container_width=True)
    
    with col_btn2:
        if st.button('💾 ذخیره', use_container_width=True):
            save_settings(capital, stop_loss_percentage, leverage, risk_inputs_str, use_leverage)
            st.success("✅ ذخیره شد!")
            st.rerun()

    if calculate_btn:
        risk_levels, parse_error = parse_risk_levels(risk_inputs_str)
        
        if parse_error:
            st.error(f"❌ {parse_error}")
            return
        
        table_df, calc_error = create_risk_management_table(
            capital, 
            stop_loss_percentage, 
            risk_levels,
            leverage,
            take_profit_percentage
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
            
            # Format table
            if use_take_profit and take_profit_percentage:
                formatted_df = table_df.copy()
                for idx in formatted_df.index:
                    if 'R:R' not in idx:
                        formatted_df.loc[idx] = formatted_df.loc[idx].apply(lambda x: f"${x:,.2f}")
                    else:
                        formatted_df.loc[idx] = formatted_df.loc[idx].apply(lambda x: f"{x:.2f}")
                st.dataframe(formatted_df, use_container_width=True)
            else:
                st.dataframe(
                    table_df.style.format("${:,.2f}"), 
                    use_container_width=True
                )
            
            st.info("💡 **ردیف اول (میزان ریسک دلاری):** این مقدار نشان‌دهنده **حداکثر مبلغی** است که شما مجازید در این معامله، در صورت رسیدن به حد ضرر، از دست بدهید.")
            
            if use_leverage:
                st.info("📊 **ردیف دوم (سایز پوزیشن):** ارزش کل معامله‌ای که باید باز کنید.")
                st.info(f"💳 **ردیف سوم (مارجین لازم با اهرم {leverage:.0f}×):** با استفاده از اهرم {leverage:.0f}×، فقط کافیه این مقدار (سایز پوزیشن ÷ {leverage:.0f}) از سرمایه‌ات رو وارد کنی!")
            else:
                st.info("🚀 **ردیف دوم (سایز پوزیشن):** این مقدار نشان‌دهنده **ارزش کل دلاری** است که باید با آن وارد معامله شوید تا در صورت فعال شدن حد ضرر، دقیقا مبلغ ردیف اول را از دست بدهید.")
            
            if use_take_profit and take_profit_percentage:
                st.info("💵 **سود احتمالی:** مقدار سودی که در صورت رسیدن به هدف Take Profit به دست می‌آورید.")
                st.info("⚖️ **نسبت R:R (Risk to Reward):** نسبت پاداش به ریسک. هرچه بالاتر باشد، معامله سودآورتر است!")
            
            st.caption("💡 این محاسبات بر اساس فرمول‌های استاندارد مدیریت ریسک در بازارهای مالی انجام شده‌اند.")
    
    st.divider()
    st.markdown(
        f"""
        <div style="text-align: center; padding: 15px; color: {'#999' if st.session_state.dark_mode else '#666'}; font-size: 13px;">
            <p style="margin: 5px 0;">ساخته شده با ❤️ توسط <strong>KanekiDevPro</strong></p>
            <p style="margin: 5px 0;">
                <a href="https://github.com/KanekiDevPro" target="_blank" style="color: {THEMES[st.session_state.theme]['primary']}; text-decoration: none; margin: 0 8px;">GitHub 🐙</a>
            </p>
            <p style="margin: 5px 0; font-size: 11px; color: {'#666' if st.session_state.dark_mode else '#999'};">نسخه 2.0 | © 2025</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
