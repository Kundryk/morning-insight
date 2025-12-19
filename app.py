import streamlit as st
from supabase import create_client
from openai import OpenAI
from datetime import datetime, timedelta

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="Morning Insight",
    page_icon="☕️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ДИЗАЙН ТА ТИПОГРАФІКА (CSS) ---
st.markdown("""
    <style>
    /* --- ЗАГАЛЬНИЙ ФОН ТА ШРИФТИ --- */
    .stApp {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }

    /* --- ЛИПКИЙ ЧАТ (ПРАВА КОЛОНКА) --- */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
        position: sticky;
        top: 2rem;
        align-self: flex-start;
        max-height: 90vh;
        overflow-y: auto;
        padding-bottom: 50px;
    }

    /* --- КРАСИВИЙ ТЕКСТ СТАТТІ --- */
    .article-content {
        font-size: 17px;           /* Більший шрифт */
        line-height: 1.7;          /* Більше повітря між рядками */
        color: #E0E0E0;            /* М'який білий колір */
        background-color: #262730; /* Темний фон картки */
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Виділення жирним (Інсайти, Контекст) */
    .article-content b {
        color: #FFD700; /* Золотистий колір для акцентів */
        font-weight: 600;
    }

    /* --- ЗАГОЛОВКИ ДАТ --- */
    .date-header {
        font-size: 1.1em;
        font-weight: bold;
        color: #FF4B4B;
        margin-top: 30px;
        margin-bottom: 15px;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* --- АКТИВНА СТАТТЯ --- */
    .active-border {
        border-left: 4px solid #4CAF50;
        padding-left: 15px;
        margin-left: -15px; /* Компенсація відступу */
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. ПІДКЛЮЧЕННЯ СЕРВІСІВ ---
@st.cache_resource
def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None

@st.cache_resource
def init_openai():
    try:
        return OpenAI(api_key=st.secrets["openai"]["api_key"])
    except: return None

supabase = init_supabase()
client = init_openai()

# --- 4. SESSION STATE ---
if "active_article" not in st.session_state:
    st.session_state.active_article = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. ФУНКЦІЯ ДАТИ ---
def get_friendly_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        if dt.date() == now.date(): return "СЬОГОДНІ 🔥"
        elif dt.date() == (now - timedelta(days=1)).date(): return "ВЧОРА"
        else: return dt.strftime("%d.%m.%Y")
    except: return date_str

# --- 6. ГОЛОВНИЙ ІНТЕРФЕЙС ---
st.title("Morning Insight ☕️")

col_feed, col_chat = st.columns([2, 1])

# === ЛІВА КОЛОНКА: СТРІЧКА ===
with col_feed:
    st.subheader("📰 Стрічка")
    
    if supabase:
        response = supabase.table("articles").select("*").order("created_at", desc=True).execute()
        articles = response.data
        
        if not articles:
            st.info("📭 Немає новин.")
        else:
            current_date = None
            for article in articles:
                if article.get('is_hidden'): continue

                # Групування по датах
                d_label = get_friendly_date(article['created_at'])
                if d_label != current_date:
                    st.markdown(f"<div class='date-header'>{d_label}</div>", unsafe_allow_html=True)
                    current_date = d_label

                # Перевірка активності
                is_active = (st.session_state.active_article and st.session_state.active_article['id'] == article['id'])
                
                # Заголовок картки
                status = "⭐️ " if article.get('is_favorite') else ""
                title_text = f"{status}{'🟢 ' if is_active else ''}{article.get('title', 'Без назви')}"
                
                # Контейнер для візуального виділення активної статті
                container = st.container()
                if is_active:
                    container.markdown("<div class='active-border'>", unsafe_allow_html=True)

                with container.expander(title_text, expanded=True):
                    # --- ТУТ МАГІЯ ТЕКСТУ ---
                    raw_summary = article.get('summary', '')
                    # Чистимо сміття, але залишаємо HTML теги
                    clean_summary = raw_summary.replace('**', '').replace('##', '')
                    
                    # Обгортаємо в наш красивий CSS клас
                    st.markdown(f"""
                        <div class="article-content">
                            {clean_summary}
                        </div>
                    """, unsafe_allow_html=True)
                    # ------------------------

                    st.divider()
                    
                    # Кнопки
                    c1, c2, c3, c4 = st.columns([1.5, 0.8, 0.8, 2])
                    with c1:
                        if st.button("💬 Обговорити", key=f"chat_{article['id']}", type="primary" if is_active else "secondary"):
                            st.session_state.active_article = article
                            st.session_state.messages = []
                            st.rerun()
                    with c2:
                        if st.button("❤️" if article.get('is_favorite') else "👍", key=f"fav_{article['id']}"):
                            new_val = not article.get('is_favorite')
                            supabase.table("articles").update({"is_favorite": new_val}).eq("id", article['id']).execute()
                            st.rerun()
                    with c3:
                        if st.button("👎", key=f"hide_{article['id']}"):
                            supabase.table("articles").update({"is_hidden": True}).eq("id", article['id']).execute()
                            st.rerun()
                    with c4:
                        st.markdown(f"<div style='text-align: right; margin-top: 5px;'><a href='{article.get('url')}' target='_blank' style='color: #4CAF50; text-decoration: none;'>Читати оригінал ↗</a></div>", unsafe_allow_html=True)
                
                if is_active:
                    container.markdown("</div>", unsafe_allow_html=True)

# === ПРАВА КОЛОНКА: ЧАТ ===
with col_chat:
    st.subheader("💬 Асистент")
    
    chat_container = st.container()
    
    with chat_container:
        if st.session_state.active_article:
            st.info(f"Тема: **{st.session_state.active_article['title']}**")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        else:
            st.warning("👈 Вибери статтю зліва, щоб почати чат.")

    if prompt := st.chat_input("Твоє питання..."):
        if not st.session_state.active_article:
            st.toast("⚠️ Спочатку вибери статтю!", icon="👈")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    msg_ph = st.empty()
                    full_resp = ""
                    context = st.session_state.active_article.get('summary', '')
                    
                    try:
                        stream = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": f"Відповідай на основі тексту: {context}"},
                                *st.session_state.messages
                            ],
                            stream=True,
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_resp += chunk.choices[0].delta.content
                                msg_ph.markdown(full_resp + "▌")
                        msg_ph.markdown(full_resp)
                        st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    except Exception as e:
                        st.error(f"Error: {e}")