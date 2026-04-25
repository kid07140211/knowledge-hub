import streamlit as st
import pandas as pd
import datetime
import re
from streamlit_option_menu import option_menu
from supabase import create_client, Client

# --- 1. Supabase 接続設定 ---
# Streamlit CloudのSecretsに設定した値を使用
URL: str = st.secrets["https://cnlrkrubzynxltgxxhfq.supabase.co/rest/v1/"]
KEY: str = st.secrets["sb_publishable_lNAGKaeQst8n2XLX4jJEfw_P23c4dAH"]
supabase: Client = create_client(URL, KEY)

# --- 2. データベース操作関数 ---

@st.cache_data(ttl=600)
def load_data():
    """Supabaseから全データを読み込む"""
    try:
        response = supabase.table("knowledge_hub").select("*").execute()
        if not response.data:
            return pd.DataFrame(columns=["date", "type", "title", "detail", "author", "tags", "status", "start_date", "deadline", "related_books"])
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame()

def save_data_to_db(new_row_df):
    """DataFrameをSupabaseに保存する"""
    # 辞書形式に変換（空の値はNoneにする）
    data_dict = new_row_df.replace({pd.NA: None, float('nan'): None}).to_dict(orient='records')
    try:
        supabase.table("knowledge_hub").insert(data_dict).execute()
        st.cache_data.clear() # キャッシュを消して最新状態にする
    except Exception as e:
        st.error(f"保存エラー: {e}")

def delete_item(title, item_type):
    """特定のアイテムを削除する"""
    try:
        supabase.table("knowledge_hub").delete().eq("title", title).eq("type", item_type).execute()
        st.cache_data.clear() 
        st.rerun()
    except Exception as e:
        st.error(f"削除エラー: {e}")

# --- 3. アプリ初期化 & ページ設定 ---
st.set_page_config(page_title="Knowledge Hub", layout="centered")

# CSSの注入
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stInfo, .stWarning, .stSuccess {
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        background-color: white !important;
        color: #333 !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem;
    }
    .author-label { color: #6c757d; font-size: 0.9rem; }
    .tag-label { 
        display: inline-block; background: #e9ecef; border-radius: 5px;
        padding: 2px 8px; font-size: 0.8rem; margin-right: 5px; color: #495057;
    }
    .stButton>button { border-radius: 10px; width: 100%; background-color: #343a40; color: white; border: none; }
    </style>
    """, unsafe_allow_html=True)

# タイトル表示
st.markdown("""
    <div style="text-align: center; padding: 20px 0px;">
        <h1 style="color: #1d3557; font-family: 'Helvetica Neue', Arial, sans-serif; letter-spacing: 2px; margin-bottom: 0;">
            📚 Knowledge Hub
        </h1>
        <p style="color: #457b9d; font-size: 0.9rem; margin-top: 5px; font-weight: bold;">
            Personal Intelligence & Learning Management
        </p>
    </div>
    <hr style="margin-top: 0; margin-bottom: 20px; border: 0; border-top: 1px solid #eee;">
""", unsafe_allow_html=True)

# --- 4. メニュー制御 (バグ修正版) ---
tabs = ["本棚", "メモ", "計画", "著者"]

if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "本棚"

# クエリパラメータによる強制ジャンプ（著者ページからの遷移用）
query_params = st.query_params
if "jump_to" in query_params:
    st.session_state.selected_tab = query_params["jump_to"]
    st.query_params.clear()
    st.rerun()

# メニュー描画
selected = option_menu(
    menu_title=None,
    options=tabs,
    icons=["journal-bookmark", "chat-right-text", "clock-history", "person-badge"],
    default_index=tabs.index(st.session_state.selected_tab),
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#ffffff"},
        "nav-link-selected": {"background-color": "#343a40", "color": "white"},
    }
)

# ユーザーがクリックした際の同期
st.session_state.selected_tab = selected

# 最新データの読み込み
df = load_data()

# --- 5. メインコンテンツ ---

# --- 【本棚】 ---
if selected == "本棚":
    st.markdown("### 📚 My Bookshelf")
    default_search = st.session_state.get('book_search', "")
    
    with st.expander("＋ 本を登録する"):
        with st.form("add_book_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            title = c1.text_input("タイトル")
            author = c2.text_input("著者")
            tags = st.text_input("タグ (#数学 #物理)")
            status = st.radio("ステータス", ["読了", "これから読む"], horizontal=True)
            
            if st.form_submit_button("本棚に保存"):
                if title:
                    new_book = pd.DataFrame([{
                        "date": str(datetime.date.today()), "type": "book", 
                        "title": title, "author": author, "tags": tags, "status": status
                    }])
                    save_data_to_db(new_book)
                    
                    # 著者が未登録なら自動登録
                    if author:
                        existing_authors = df[df["type"] == "author"]["title"].tolist()
                        if author not in existing_authors:
                            new_author = pd.DataFrame([{
                                "date": str(datetime.date.today()), "type": "author",
                                "title": author, "detail": f"『{title}』の著者", "related_books": title
                            }])
                            save_data_to_db(new_author)
                    
                    st.toast(f"『{title}』を登録しました", icon='✅')
                    st.rerun()

    col_v, col_s = st.columns([0.4, 0.6])
    view = col_v.segmented_control("表示対象", ["読了", "これから読む"], default="読了")
    search = col_s.text_input("🔍 検索", value=default_search)

    if 'book_search' in st.session_state:
        del st.session_state.book_search
    
    res = df[(df["type"]=="book") & (df["status"]==view)]
    if search:
        res = res[res["title"].str.contains(search, na=False) | res["tags"].str.contains(search, na=False)]
    
    if not res.empty:
        for i, row in res.iloc[::-1].iterrows():
            st.markdown(f"""
            <div style="background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 10px; border-left: 5px solid #343a40;">
                <div style="font-weight: bold; font-size: 1.1rem; color: #212529;">📖 {row['title']}</div>
                <div style="color: #6c757d; font-size: 0.9rem;">👤 {row['author'] if pd.notna(row['author']) else '不明'}</div>
                <div style="margin-top: 8px;"><span class="tag-label">{row['tags'] if pd.notna(row['tags']) else ''}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.popover("⚙️ 操作"):
                if st.button("🗑️ この本を削除", key=f"del_book_{i}"):
                    delete_item(row['title'], "book")
            
            with st.expander(f"「{row['title']}」のメモ"):
                memos = df[(df["type"]=="memo") & (df["title"]==row['title'])]
                for _, m in memos.iloc[::-1].iterrows():
                    st.info(f"{m['detail']}\n\n---\n📅 {m['date']}")

# --- 【メモ】 ---
elif selected == "メモ":
    st.markdown("### 📝 Deep Notes")
    book_titles = df[df["type"]=="book"]["title"].unique()
    
    if len(book_titles) > 0:
        with st.expander("＋ 新しい思考を記録する", expanded=True):
            target = st.selectbox("対象の本を選択", book_titles)
            with st.form("add_memo_form", clear_on_submit=True):
                m_body = st.text_area("思考ログ", height=150)
                m_tag = st.text_input("トピックタグ")
                if st.form_submit_button("記録する"):
                    if m_body:
                        new_memo = pd.DataFrame([{"date": str(datetime.date.today()), "type": "memo", "title": target, "detail": m_body, "tags": m_tag}])
                        save_data_to_db(new_memo)
                        st.rerun()
    
    st.divider()
    all_memos = df[df["type"]=="memo"]
    if not all_memos.empty:
        for i, m_row in all_memos.iloc[::-1].iterrows():
            st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 12px; border-left: 4px solid #dee2e6;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="font-weight: bold; color: #495057;">📖 {m_row['title']}</span>
                        <span style="color: #adb5bd; font-size: 0.75rem;">📅 {m_row['date']}</span>
                    </div>
                    <div style="font-size: 0.95rem; margin-bottom: 8px;">{m_row['detail']}</div>
                </div>
            """, unsafe_allow_html=True)
            with st.popover("🗑️"):
                if st.button("このメモを削除", key=f"del_memo_{i}"):
                    delete_item(m_row['title'], "memo")

# --- 【計画】 ---
elif selected == "計画":
    st.markdown("### 📅 Mission Control")
    with st.expander("＋ 新しいミッションを追加"):
        with st.form("plan_f", clear_on_submit=True):
            p_t = st.text_input("題名")
            p_detail = st.text_area("詳細")
            c1, c2 = st.columns(2)
            p_start = c1.date_input("開始日", datetime.date.today())
            p_end = c2.date_input("期限", datetime.date.today() + datetime.timedelta(days=7))
            if st.form_submit_button("登録"):
                new_plan = pd.DataFrame([{"date": str(datetime.date.today()), "type": "plan", "title": p_t, "detail": p_detail, "start_date": str(p_start), "deadline": str(p_end)}])
                save_data_to_db(new_plan)
                st.rerun()

    plans = df[df["type"]=="plan"].copy()
    if not plans.empty:
        st.markdown("#### 🚀 進行中のミッション")
        for i, row in plans.iterrows():
            ed = datetime.datetime.strptime(str(row['deadline']), '%Y-%m-%d').date()
            days_left = (ed - datetime.date.today()).days
            st.warning(f"🎯 {row['title']} (あと {days_left} 日)\n\n{row['detail']}")
            if st.button("🗑️ 削除", key=f"del_plan_{i}"):
                delete_item(row['title'], "plan")

# --- 【著者】 ---
elif selected == "著者":
    st.markdown("### 👥 Thinkers")
    with st.expander("＋ 新しい著者を登録"):
        with st.form("add_author", clear_on_submit=True):
            a_name = st.text_input("著者名")
            a_desc = st.text_area("著者の思想など")
            a_books = st.text_input("関連本 (カンマ区切り)")
            if st.form_submit_button("登録"):
                new_a = pd.DataFrame([{"date": str(datetime.date.today()), "type": "author", "title": a_name, "detail": a_desc, "related_books": a_books}])
                save_data_to_db(new_a)
                st.rerun()

    authors = df[df["type"]=="author"]
    for i, row in authors.iterrows():
        st.markdown(f"""<div style="background: #f1f3f5; padding: 15px; border-radius: 10px; border-left: 5px solid #1d3557; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #1d3557;">{row['title']}</h4>
                        <p style="font-size: 0.9rem;">{row['detail'] if pd.notna(row['detail']) else ''}</p>
                    </div>""", unsafe_allow_html=True)
        
        related = row.get('related_books', "")
        if pd.notna(related) and related:
            books = [b.strip() for b in re.split('[、,]', str(related))]
            cols = st.columns(min(len(books), 5))
            for idx, b_name in enumerate(books):
                if cols[idx % 5].button(f"📖 {b_name}", key=f"j_{row['title']}_{idx}"):
                    st.session_state.selected_tab = "本棚"
                    st.session_state.book_search = b_name
                    st.rerun()
        
        if st.button("🗑️ 著者削除", key=f"del_auth_{i}"):
            delete_item(row['title'], "author")