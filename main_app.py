import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
import datetime
import sqlite3

# --- DB設定 (SQLite版) ---
def get_connection():
    # knowledge_hub.db というファイルが自動で作られます
    return sqlite3.connect("knowledge_hub.db", check_same_thread=False)

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    # テーブルがなければ作成（カラム名は今のdfに合わせて調整してください）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS data (
            date TEXT, type TEXT, title TEXT, detail TEXT, 
            related_books TEXT, author TEXT, tags TEXT, status TEXT
        )
    """)
    conn.commit()
    conn.close()

def load_data():
    create_table()
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM data", conn)
    conn.close()
    return df

def save_data_to_db(new_row_df):
    conn = get_connection()
    # DataFrameをそのままDBに追加保存
    new_row_df.to_sql("data", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

# --- 1. 冒頭に削除関数を定義 (SQLite対応版) ---
def delete_item(item_id, item_type):
    """
    dfのインデックスではなく、DB上の行を直接特定して削除します。
    ※load_dataで読み込む際、SQLiteの行番号(rowid)をIDとして使うと確実です。
    """
    conn = sqlite3.connect("knowledge_hub.db")
    cur = conn.cursor()
    # シンプルに「同じタイトルかつ同じタイプ」のものを消す命令
    cur.execute("DELETE FROM data WHERE title = ? AND type = ?", (item_id, item_type))
    conn.commit()
    conn.close()
    st.cache_data.clear() 
    st.rerun()
    
# --- 2. データの読み込み ---
# アプリの冒頭で1回だけ実行
df = load_data()

# --- ページ設定 & スタイル注入 (CSS) ---
st.set_page_config(page_title="Knowledge Hub", layout="centered")

st.markdown("""
    <style>
    /* 全体の背景とフォント */
    .main { background-color: #f8f9fa; }
    
    /* カード風のデザイン */
    .stInfo, .stWarning, .stSuccess {
        border-radius: 15px;
        border: none;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        background-color: white !important;
        color: #333 !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem;
    }
    /* 著者名やタグの装飾 */
    .author-label { color: #6c757d; font-size: 0.9rem; }
    .tag-label { 
        display: inline-block;
        background: #e9ecef;
        border-radius: 5px;
        padding: 2px 8px;
        font-size: 0.8rem;
        margin-right: 5px;
        color: #495057;
    }
    /* ボタンのカスタマイズ */
    .stButton>button {
        border-radius: 10px;
        width: 100%;
        background-color: #343a40;
        color: white;
        border: none;
        padding: 0.5rem;
    }
    
    /* 入力フォームの角丸 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- アプリケーションの最上部にタイトルを表示 ---
st.markdown("""
    <div style="text-align: center; padding: 20px 0px;">
        <h1 style="color: #1d3557; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; letter-spacing: 2px; margin-bottom: 0;">
            📚 Knowledge Hub
        </h1>
        <p style="color: #457b9d; font-size: 0.9rem; margin-top: 5px; font-weight: bold;">
            Personal Intelligence & Learning Management
        </p>
    </div>
    <hr style="margin-top: 0; margin-bottom: 20px; border: 0; border-top: 1px solid #eee;">
""", unsafe_allow_html=True)

# --- ボトムナビゲーション (HTML/JS的な役割) ---
# --- サイドバーまたはメインのメニュー部分 ---
tabs = ["本棚", "メモ", "計画", "著者"]

# 現在のタブが何番目かを探すロジックを追加
if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "本棚"

# --- 3. 【重要】ジャンプ用の処理をメニュー描画前に実行 ---
# 著者ページのボタンが押されたとき、クエリパラメータや特定のキーを監視して
# メニューが描画される前に session_state を上書きします。
query_params = st.query_params
if "jump_to" in query_params:
    st.session_state.selected_tab = query_params["jump_to"]
    # 処理が終わったらパラメータを消して再実行
    st.query_params.clear()
    st.rerun()
    
current_index = tabs.index(st.session_state.selected_tab)

selected = option_menu(
    menu_title=None,
    options=tabs,
    icons=["journal-bookmark", "chat-right-text", "clock-history", "person-badge"],
    menu_icon="cast",
    default_index=current_index,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#ffffff"},
        "icon": {"color": "#6c757d", "font-size": "18px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#343a40", "color": "white"},
    }
)
# メニューを手動でクリックした時もセッションを更新
# st.session_state.selected_tab = selected
# ユーザーが直接タブをクリックした場合の更新
if selected != st.session_state.selected_tab:
    st.session_state.selected_tab = selected


# --- メインコンテンツ ---

# 1. 本棚
if selected == "本棚":
    # --- 便利機能：著者ページからのジャンプ受け口 ---
    default_search = st.session_state.get('book_search', "")

    st.markdown("### 📚 My Bookshelf")
    
    with st.expander("＋ 本を登録する"):
        with st.form("add_book_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            title = c1.text_input("タイトル")
            author = c2.text_input("著者")
            tags = st.text_input("タグ (#数学 #物理)")
            status = st.radio("ステータス", ["読了", "これから読む"], horizontal=True)
            if st.form_submit_button("本棚に保存"):
                if title:
                    # 1. 本のデータを準備
                    new_book = pd.DataFrame([{
                        "date": datetime.date.today(), 
                        "type": "book", 
                        "title": title, 
                        "author": author, 
                        "tags": tags, 
                        "status": status
                    }])
                    
                    # 2. 【ここが重要】著者が未登録なら自動で追加する
                    # 既存の著者リストを取得
                    existing_authors = df[df["type"] == "author"]["title"].tolist()
                    
                    # 著者名が入力されており、かつ未登録の場合
                    if author and (author not in existing_authors):
                        new_author = pd.DataFrame([{
                            "date": datetime.date.today(),
                            "type": "author",
                            "title": author,
                            "detail": f"『{title}』の著者",
                            "related_books": title
                        }])
                        # 本と著者の両方を今のデータに追加
                        df = pd.concat([df, new_book, new_author])
                    else:
                        # 著者が既にいる場合は、その著者の「関連本」に今の本を追記する
                        if author:
                            idx_list = df[(df["type"] == "author") & (df["title"] == author)].index
                            if not idx_list.empty:
                                idx = idx_list[0]
                                current_rel = str(df.at[idx, 'related_books'])
                                if title not in current_rel:
                                    # 「nan」対策をしてから追記
                                    new_rel = f"{current_rel}, {title}" if current_rel != "nan" else title
                                    df.at[idx, 'related_books'] = new_rel
                        
                        # 本のデータだけ追加
                        df = pd.concat([df, new_book])

                    # 3. 保存してリロード
                    save_data_to_db(new_book)
                    st.toast(f"『{title}』と著者『{author}』を登録しました！", icon='✅')
                    st.rerun()
                else:
                    st.error("タイトルを入力してください")
    # 検索・絞り込みエリア
    col_v, col_s = st.columns([0.4, 0.6])
    view = col_v.segmented_control("表示対象", ["読了", "これから読む"], default="読了")
    
    # 著者ページからのジャンプ時はここに自動でタイトルが入る
    search = col_s.text_input("🔍 タイトル・タグ検索", value=default_search)

    # 検索が終わったらセッションをクリア（次回普通に開くときは空にするため）
    if 'book_search' in st.session_state:
        del st.session_state.book_search
    
    # フィルタリング
    res = df[(df["type"]=="book") & (df["status"]==view)]
    if search:
        # タイトルまたはタグに検索ワードが含まれるものを抽出
        res = res[res["title"].str.contains(search, na=False) | res["tags"].str.contains(search, na=False)]
    
    # --- 表示ロジック ---
    if not res.empty:
        for i, row in res.iloc[::-1].iterrows():
            card_html = f"""
            <div style="background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 10px; border-left: 5px solid #343a40;">
                <div style="font-weight: bold; font-size: 1.1rem; color: #212529;">📖 {row['title']}</div>
                <div style="color: #6c757d; font-size: 0.9rem;">👤 {row['author'] if pd.notna(row['author']) else '不明'}</div>
                <div style="margin-top: 8px;">
                    <span style="background: #e9ecef; border-radius: 5px; padding: 2px 8px; font-size: 0.75rem; color: #495057;">
                        {row['tags'] if pd.notna(row['tags']) else ''}
                    </span>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            with st.popover("⚙️ 操作"):
                if st.button("🗑️ この本を削除", key=f"del_book_{i}"):
                    delete_item(row['title'], "book")
            
            with st.expander(f"「{row['title']}」のメモを確認"):
                book_memos = df[(df["type"]=="memo") & (df["title"]==row['title'])]
                if not book_memos.empty:
                    for _, m_row in book_memos.iloc[::-1].iterrows():
                        st.markdown(f"""
                            <div style="background-color: #f1f3f5; padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 0.9rem; border-left: 3px solid #dee2e6;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: #adb5bd; font-size: 0.75rem;">📅 {m_row['date']}</span>
                                    <span style="color: #6c757d; font-size: 0.7rem;">{m_row['tags'] if pd.notna(m_row['tags']) else ''}</span>
                                </div>
                                <div style="color: #343a40; line-height: 1.4;">{m_row['memo']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.write("まだメモがありません。")
    else:
        st.info("該当する本が見つかりません。")

# 2. メモ
# --- 2. メモページ (ブラッシュアップ版) ---
elif selected == "メモ":
    st.markdown("### 📝 Deep Notes")
    book_titles = df[df["type"]=="book"]["title"].unique()
    
    # --- 入力エリア ---
    if len(book_titles) > 0:
        with st.expander("＋ 新しい思考を記録する", expanded=True):
            target = st.selectbox("対象の本を選択", book_titles)
            with st.form("add_memo_form", clear_on_submit=True):
                m_body = st.text_area("今日の思考ログ", height=150, placeholder="ここに学んだことや考えたことを自由に書き殴ってください...")
                m_tag = st.text_input("トピックタグ (任意)")
                
                if st.form_submit_button("思考を記録する"):
                    if m_body:
                        new_memo = pd.DataFrame([{"date": str(datetime.date.today()), "type": "memo", "title": target, "detail": m_body, "tags": m_tag}])
                        save_data_to_db(new_memo)
                        st.toast(f'「{target}」にメモを保存しました', icon='📝')
                        st.rerun()
    
    st.divider()
    st.subheader("最新のメモ一覧")

    # --- 一覧表示エリア (新しい順) ---
    all_memos = df[df["type"]=="memo"]
    
    if not all_memos.empty:
        # iloc[::-1] で新しい順（降順）に並び替え
        for i, m_row in all_memos.iloc[::-1].iterrows():
            st.markdown(f"""
                <div style="
                    background-color: white;
                    padding: 15px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    margin-bottom: 12px;
                    border-left: 4px solid #dee2e6;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: bold; color: #495057; font-size: 0.85rem;">📖 {m_row['title']}</span>
                        <span style="color: #adb5bd; font-size: 0.75rem;">📅 {m_row['date']}</span>
                    </div>
                    <div style="color: #212529; line-height: 1.5; font-size: 0.95rem; margin-bottom: 8px;">
                        {m_row['memo']}
                    </div>
                    {f'<div style="text-align: right;"><span style="background: #f8f9fa; border-radius: 5px; padding: 2px 8px; font-size: 0.7rem; color: #6c757d; border: 1px solid #e9ecef;">#{m_row["tags"]}</span></div>' if pd.notna(m_row['tags']) and m_row['tags'] != '' else ''}
                </div>
                """, unsafe_allow_html=True)
            # 【ここに削除機能を追加】
            with st.popover("🗑️"):
                if st.button("このメモを完全に削除", key=f"del_memo_{i}"):
                    delete_item(m_row['title'], "memo")
    else:
        st.info("まだメモがありません。上のフォームから最初の思考を記録しましょう！")

# 3. 計画
# --- 3. 計画ページ (ブラッシュアップ版) ---
elif selected == "計画":
    st.markdown("### 📅 Mission Control")
    
    # 1. ミッション追加フォーム
    with st.expander("＋ 新しいミッションを追加"):
        with st.form("plan_f", clear_on_submit=True):
            p_t = st.text_input("題名")
            p_detail = st.text_area("詳細")
            p_tag = st.text_input("タグ")
            c1, c2 = st.columns(2)
            p_start = c1.date_input("開始日", datetime.date.today())
            p_end = c2.date_input("期限", datetime.date.today() + datetime.timedelta(days=7))
            if st.form_submit_button("ミッションを登録"):
                if p_t:
                    new_plan = pd.DataFrame([{"date": str(datetime.date.today()), "type": "plan", "title": p_t, "detail": p_detail, "tags": p_tag, "start_date": str(p_start), "deadline": str(p_end)}])
                    save_data_to_db(new_plan)
                    st.toast(f"ミッション『{p_t}』を予約しました", icon='🚀')
                    st.rerun()

    # データの準備
    plans = df[df["type"]=="plan"].copy()
    today = datetime.date.today()

    if not plans.empty:
        def to_date(d):
            return datetime.datetime.strptime(str(d), '%Y-%m-%d').date()

        plans['is_finished'] = plans['deadline'].apply(lambda x: to_date(x) < today)
        active_plans = plans[~plans['is_finished']]
        history_plans = plans[plans['is_finished']]

        # --- 2. 進行中のミッション ---
        st.markdown("#### 🚀 進行中のミッション")
        for i, row in active_plans.iterrows():
            sd = to_date(row['start_date'])
            ed = to_date(row['deadline'])
            days_left = (ed - today).days
            color = "#e63946" if days_left <= 3 else "#457b9d"
            
            # カード部分（HTML）
            html = f"""
            <div style="background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-top: 5px solid {color}; margin-bottom: 0px;">
                <div style="display: flex; justify-content: space-between; font-weight: bold;">
                    <span style="color: #1d3557;">🎯 {row['title']}</span>
                    <span style="color: #6c757d; font-size: 0.7rem;">{row.get('tags', '')}</span>
                </div>
                <div style="height: 18px; background: #eee; border-radius: 9px; position: relative; overflow: hidden; margin-top: 10px;">
                    <div style="position: absolute; left: 0; top: 0; height: 100%; width: 100%; background: {color}; color: white; display: flex; align-items: center; padding-left: 15px; font-size: 0.65rem;">
                        {sd} ━━ {ed} (あと {max(0, days_left)} 日)
                    </div>
                </div>
            </div>"""
            st.components.v1.html(html, height=100)
            
            # --- ここを修正：横並びにボタンを配置 ---
            col_ex, col_del = st.columns([0.85, 0.15])
            with col_ex.expander("詳細を確認"):
                st.write(row['detail'] if row['detail'] else "詳細なし")
            
            with col_del:
                with st.popover("🗑️"):
                    if st.button("削除", key=f"del_plan_{i}"):
                        delete_item(row['title'], "plan") # 事前に定義した削除関数

        # --- 3. 終了したミッション（履歴） ---
        if not history_plans.empty:
            st.markdown("---")
            st.markdown("#### ✅ 完了・終了したミッション")
            for _, row in history_plans.iterrows():
                ed = to_date(row['deadline'])
                
                # 履歴用のコンパクトな表示
                with st.expander(f"✔️ {row['title']} （{ed} 終了）"):
                    st.caption(f"期間: {row['start_date']} 〜 {row['deadline']}")
                    st.info(row['detail'] if row['detail'] else "詳細なし")
                    if row.get('tags'):
                        st.write(f"🏷️ {row['tags']}")
                    # 履歴の削除ボタン
                    if st.button("🗑️ 履歴から削除", key=f"del_hist_{i}"):
                        delete_item(row['title'], "plan")
    else:
        st.info("登録されたミッションはありません。")
# 4. 著者
elif selected == "著者":
    st.markdown("### 👥 Thinkers")
    
    # --- 便利機能：著者をクイック追加 ---
    with st.expander("＋ 新しい著者を登録"):
        with st.form("add_author", clear_on_submit=True):
            a_name = st.text_input("著者名")
            a_desc = st.text_area("著者の特徴・思想など")
            a_books = st.text_input("関連本 (カンマ区切り)", placeholder="例: サピエンス全史, ホモ・デウス")
            if st.form_submit_button("登録"):
                if a_name:
                    new_a = pd.DataFrame([{"date": datetime.date.today(), "type": "author", "title": a_name, "detail": a_desc, "related_books": a_books}])
                    save_data_to_db(new_a)
                    st.rerun()

    st.markdown("---")
    
    # 著者データの取得
    authors = df[df["type"]=="author"]
    
    if not authors.empty:
        for i, row in authors.iterrows():
            with st.container():
                # デザインを整えた著者カード
                st.markdown(f"""
                <div style="background: #f1f3f5; padding: 15px; border-radius: 10px; border-left: 5px solid #1d3557; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #1d3557;">{row['title']}</h4>
                    <p style="font-size: 0.9rem; color: #495057; margin-top: 8px;">{row['detail'] if pd.notna(row['detail']) else ''}</p>
                </div>
                """, unsafe_allow_html=True)
                # 【ここに削除機能を追加】
                with st.popover("⚙️"):
                    if st.button("🗑️ この著者を削除", key=f"del_auth_{i}"):
                        delete_item(row['title'], "author")
                # 関連本ボタンの表示
                related = row.get('related_books', "")
                if pd.notna(related) and related:
                    st.caption("📚 本棚の関連ページへジャンプ:")
                    # カンマまたは全角読点で分割
                    import re
                    books = [b.strip() for b in re.split('[、,]', str(related))]
                    
                    cols = st.columns(len(books) if len(books) < 5 else 5)
                    for i, b_name in enumerate(books):
                        # ボタンを押したら本棚へワープ
                        if cols[i % 5].button(f"📖 {b_name}", key=f"jump_{row['title']}_{b_name}_{i}"):
                            st.session_state.selected_tab = "本棚"
                            st.session_state.book_search = b_name
                            st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("著者がまだ登録されていないか、データの形式が古いようです。上のフォームから登録してみてください。")