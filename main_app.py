import streamlit as st
import pandas as pd
import datetime
import re
from streamlit_option_menu import option_menu
from supabase import create_client, Client

# --- 1. Supabase 接続設定 ---
# Streamlit CloudのSecretsに設定した値を使用
# --- 修正後 ---
URL: str = st.secrets["SUPABASE_URL"]
KEY: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. データベース操作関数 ---

@st.cache_data(ttl=600)
def load_data():
    """Supabaseから全データを読み込む"""
    # 期待するカラムのリスト
    columns = ["date", "type", "title", "detail", "author", "tags", "status", "start_date", "deadline", "related_books"]
    try:
        response = supabase.table("knowledge_hub").select("*").execute()
        if not response.data:
            # データが1件もない場合、空の枠組み（カラム名だけある状態）を返す
            return pd.DataFrame(columns=columns)
        
        df_raw = pd.DataFrame(response.data)
        
        # 足りないカラムがあれば補完する（これがKeyErrorを防ぐお守りになります）
        for col in columns:
            if col not in df_raw.columns:
                df_raw[col] = None
                
        return df_raw
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame(columns=columns)
    
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
                        # キャッシュを介さず、DBから直接現在の著者一覧を確認
                        check_auth = supabase.table("knowledge_hub").select("title").eq("type", "author").eq("title", author).execute()
                        if not check_auth.data: # 著者がまだ存在しない場合のみ登録
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


# --- 【メモ】セクション ---
elif selected == "メモ":
    st.markdown("### 📝 Knowledge & Thought Log")
    
    # 1. ページ内タブで「本のメモ」と「日常メモ」を分ける
    memo_tab1, memo_tab2 = st.tabs(["📖 本の抜き書き・感想", "💡 日常の思考・アイデア"])
    
    df = load_data()

    # --- タブ1: 本のメモ（既存の機能をこちらに集約） ---
    with memo_tab1:
        st.markdown("#### 📚 Book Notes")
        # 本に関連するデータ（type=="book"）から、詳細(detail)が空でないものを抽出
        book_memos = df[(df["type"]=="book") & (df["detail"].notna()) & (df["detail"] != "")]
        
        b_search = st.text_input("🔍 本のメモを検索", key="book_memo_search")
        if b_search:
            book_memos = book_memos[book_memos['title'].str.contains(b_search, case=False) | 
                                    book_memos['detail'].str.contains(b_search, case=False)]
        
        if book_memos.empty:
            st.info("本のメモはまだありません。「本棚」から登録・編集できます。")
        else:
            for i, row in book_memos.iterrows():
                with st.expander(f"📖 {row['title']}"):
                    st.write(row['detail'])
                    st.caption(f"著者: {row['author']} / タグ: {row['tags']}")

    # --- タブ2: 日常メモ（新機能） ---
    with memo_tab2:
        st.markdown("#### ⚡ Quick Thoughts")
        
        # 検索機能
        c1, c2 = st.columns([2, 1])
        q_search = c1.text_input("🔍 キーワード検索", key="daily_memo_search")
        t_search = c2.text_input("🏷️ タグ検索", key="daily_tag_search")
        
        with st.expander("＋ 新しい日常メモを追加"):
            with st.form("add_daily_memo", clear_on_submit=True):
                m_t = st.text_input("タイトル")
                m_c = st.text_area("内容")
                m_tag = st.text_input("タグ（カンマ区切り）")
                if st.form_submit_button("保存"):
                    if m_t and m_c:
                        new_m = pd.DataFrame([{
                            "date": str(datetime.date.today()), "type": "memo", 
                            "title": m_t, "detail": m_c, "tags": m_tag
                        }])
                        save_data_to_db(new_m)
                        st.cache_data.clear()
                        st.rerun()

        # 日常メモの表示（type=="memo"）
        daily_memos = df[df["type"]=="memo"].copy()
        if q_search:
            daily_memos = daily_memos[daily_memos['title'].str.contains(q_search, case=False) | 
                                      daily_memos['detail'].str.contains(q_search, case=False)]
        if t_search:
            daily_memos = daily_memos[daily_memos['tags'].str.contains(t_search, case=False, na=False)]
            
        for i, row in daily_memos.sort_index(ascending=False).iterrows():
            st.markdown(f"""
            <div style="background: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between;">
                    <strong style="color: #1d3557;">{row['title']}</strong>
                    <span style="color: #adb5bd; font-size: 0.7rem;">{row['date']}</span>
                </div>
                <div style="font-size: 0.9rem; margin-top: 5px; white-space: pre-wrap;">{row['detail']}</div>
                <div style="margin-top: 8px; color: #3498db; font-size: 0.75rem;">#{row['tags']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🗑️ 削除", key=f"del_daily_{i}"):
                delete_item(row['title'], "memo")
                st.cache_data.clear()
                st.rerun()
# --- 【計画】 ---
# --- 【計画】 ---
elif selected == "計画":
    st.markdown("### 📅 Mission Control")
    
    # 1. データの最新化
    df = load_data()
    
    with st.expander("＋ 新しいミッションを追加"):
        with st.form("plan_f", clear_on_submit=True):
            p_t = st.text_input("題名")
            p_detail = st.text_area("詳細")
            c1, c2 = st.columns(2)
            p_start = c1.date_input("開始日", datetime.date.today())
            p_end = c2.date_input("期限", datetime.date.today() + datetime.timedelta(days=7))
            if st.form_submit_button("登録"):
                if p_t:
                    new_plan = pd.DataFrame([{
                        "date": str(datetime.date.today()), 
                        "type": "plan", 
                        "title": p_t, 
                        "detail": p_detail, 
                        "start_date": str(p_start), 
                        "deadline": str(p_end)
                    }])
                    save_data_to_db(new_plan)
                    st.rerun()

    # データの整理
    plans = df[df["type"]=="plan"].copy()
    today = datetime.date.today()
    
    if not plans.empty:
        # 文字列の日付をdateオブジェクトに変換
        plans['deadline_dt'] = pd.to_datetime(plans['deadline']).dt.date
        
        # 進行中とアーカイブに分ける
        active_plans = plans[plans['deadline_dt'] >= today].sort_values('deadline_dt')
        past_plans = plans[plans['deadline_dt'] < today].sort_values('deadline_dt', ascending=False)

        # --- 🚀 進行中のミッション ---
        st.markdown("#### 🚀 Active Missions")
        for i, row in active_plans.iterrows():
            days_left = (row['deadline_dt'] - today).days
            
            # おしゃれなカードデザイン
            st.markdown(f"""
            <div style="background: white; padding: 20px; border-radius: 15px; border-left: 8px solid #3498db; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 1.2rem; color: #2c3e50;">🎯 {row['title']}</span>
                    <span style="background: #ebf5fb; color: #3498db; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold;">
                        あと {days_left} 日
                    </span>
                </div>
                <p style="color: #7f8c8d; font-size: 0.9rem; margin-top: 10px;">{row['detail'] if row['detail'] else '詳細なし'}</p>
                <div style="font-size: 0.75rem; color: #bdc3c7; margin-top: 10px;">期限: {row['deadline']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🗑️ 完了・削除", key=f"del_plan_{i}"):
                delete_item(row['title'], "plan")
                st.cache_data.clear()
                st.rerun()

        # --- 📁 ミッション履歴 (Archive) ---
        if not past_plans.empty:
            st.markdown("---")
            with st.expander("📁 Mission Archive（過去の記録）"):
                for i, row in past_plans.iterrows():
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 10px; opacity: 0.8;">
                        <div style="color: #6c757d; text-decoration: line-through; font-weight: bold;">✅ {row['title']}</div>
                        <div style="font-size: 0.8rem; color: #adb5bd;">期限: {row['deadline']}（終了）</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("履歴から削除", key=f"del_hist_{i}"):
                        delete_item(row['title'], "plan")
                        st.cache_data.clear()
                        st.rerun()

# --- 【著者】 ---
elif selected == "著者":
    st.markdown("### 👥 Thinkers")
    
    # 最新データの読み込み
    df = load_data()
    
    # 1. 検索バーの設置
    search_query = st.text_input("🔍 著者を検索（名前やキーワード）", placeholder="例: 資本論, 現代思想, 氏名など")
    
    with st.expander("＋ 新しい著者を登録"):
        with st.form("add_author", clear_on_submit=True):
            a_name = st.text_input("著者名")
            a_desc = st.text_area("著者の思想など")
            a_books = st.text_input("関連本 (カンマ区切り)")
            if st.form_submit_button("登録"):
                if a_name:
                    new_a = pd.DataFrame([{
                        "date": str(datetime.date.today()), 
                        "type": "author", 
                        "title": str(a_name), 
                        "detail": str(a_desc) if a_desc else "", 
                        "related_books": str(a_books) if a_books else ""
                    }])
                    save_data_to_db(new_a)
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("---")
    
    # 2. フィルタリング処理
    authors = df[df["type"]=="author"].copy()
    
    if search_query:
        # 名前(title)か詳細(detail)にキーワードが含まれているものを抽出（大文字小文字を区別しない）
        authors = authors[
            authors['title'].str.contains(search_query, case=False, na=False) | 
            authors['detail'].str.contains(search_query, case=False, na=False)
        ]
        st.caption(f"検索結果: {len(authors)} 件")

    if authors.empty:
        if search_query:
            st.warning(f"「{search_query}」に一致する著者は見つかりませんでした。")
        else:
            st.info("著者がまだ登録されていません。")
    else:
        # 3. 表示ループ
        for i, row in authors.iterrows():
            with st.container():
                st.markdown(f"""
                <div style="background: #f1f3f5; padding: 15px; border-radius: 10px; border-left: 5px solid #1d3557; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #1d3557;">{row['title']}</h4>
                    <p style="font-size: 0.9rem; margin-top: 8px;">{row['detail'] if pd.notna(row['detail']) else ''}</p>
                </div>
                """, unsafe_allow_html=True)
                
                related = row.get('related_books', "")
                if pd.notna(related) and str(related).strip():
                    books = [b.strip() for b in re.split('[、,]', str(related)) if b.strip()]
                    if books:
                        st.caption("📖 本棚へジャンプ:")
                        cols = st.columns(min(len(books), 5))
                        for idx, b_name in enumerate(books):
                            if cols[idx % 5].button(f"{b_name}", key=f"btn_{i}_{idx}_{b_name}"):
                                st.session_state.selected_tab = "本棚"
                                st.session_state.book_search = b_name
                                st.rerun()
                
                if st.button("🗑️ 著者削除", key=f"del_auth_btn_{i}"):
                    delete_item(row['title'], "author")
                    st.cache_data.clear()
                    st.rerun()
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)