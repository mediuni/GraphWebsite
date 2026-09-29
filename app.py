from __future__ import annotations

import pandas as pd
import streamlit as st

from neo4j_service import (
    get_dashboard_metrics,
    find_student,
    get_students,
    graph_neighborhood,
    ping,
    recommend_game_genres,
    game_genres_likes,
    seed_demo_data,
)

st.set_page_config(
    page_title="Game Genre Recommender",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
      .hero {
        padding: 1.4rem 1.6rem; border-radius: 22px;
        background: linear-gradient(120deg, #111827 0%, #1f2937 55%, #0f766e 100%);
        color: white; margin-bottom: 1rem;
      }
      .hero h1 {margin:0; font-size:2.15rem;}
      .hero p {opacity:.88; margin:.35rem 0 0 0;}
      .genre-card {
        padding: 1rem 1.1rem; border: 1px solid rgba(128,128,128,.25);
        border-radius: 16px; margin-bottom: .75rem;
      }
      .score-pill {
        display:inline-block; padding:.2rem .55rem; border-radius:999px;
        background:#0f766e; color:white; font-size:.8rem; font-weight:700;
      }
      .muted {opacity:.72; font-size:.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def require_connection() -> None:
    try:
        if not ping():
            raise RuntimeError("Neo4j did not return a healthy response")
    except Exception as exc:
        st.error("ยังเชื่อมต่อ Neo4j Aura ไม่สำเร็จ")
        st.code(
            '[neo4j]\nuri = "neo4j+s://e737832c.databases.neo4j.io"\n'
            'username = "neo4j"\npassword = "YOUR_PASSWORD"\ndatabase = "neo4j"',
            language="toml",
        )
        st.caption("ให้นำค่าด้านบนไปใส่ใน Streamlit Secrets และห้าม commit password ลง GitHub")
        st.exception(exc)
        st.stop()


def student_selector(key: str = "student") -> str:
    students = get_students()
    if not students:
        st.info("ยังไม่มีข้อมูลนักศึกษา กรุณาไปหน้า Admin / Setup แล้วสร้างข้อมูลตัวอย่าง")
        st.stop()
    labels = {f"{x['student_id']} — {x['name']}": x["student_id"] for x in students}
    chosen = st.selectbox("เลือกผู้ใช้", list(labels), key=key)
    return labels[chosen]


def explain_reason(score: int) -> str:
    if score > 0:
        return f"มีเพื่อน {score} คนชื่นชอบแนวเกมนี้"
    return "แนะนำจากข้อมูลความนิยมทั่วไป"


require_connection()

with st.sidebar:
    st.markdown("## 🎮 Game Genre")
    st.caption("Neo4j Aura + Streamlit")
    page = st.radio(
        "เมนู",
        ["Dashboard", "Recommendations", "Graph Explorer", "Admin / Setup"],
    )
    st.divider()
    st.caption("Bachelor-level Graph Database Project")

st.markdown(
    """
    <div class="hero">
      <h1>🎮 Game Genre Recommendation System</h1>
      <p>ระบบแนะนำแนวเกมด้วย Graph Database ที่ประมวลผลจากความชื่นชอบของเพื่อน</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if page == "Dashboard":
    st.subheader("ภาพรวมระบบ")
    m = get_dashboard_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", m.get("students", 0))
    c2.metric("Game Genres", m.get("game_genres", 0))
    c3.metric("Likes (GENRES_LIKES)", m.get("likes", 0))
    c4.metric("Friend relationships", m.get("friendships", 0))

    st.divider()
    student_id = student_selector("dash_student")
    profile = find_student(student_id)
    likes = game_genres_likes(student_id)
    
    if profile:
        left, right = st.columns([1, 2])
        with left:
            st.markdown(f"### ข้อมูลนักเรียน")
            st.write(f"**รหัส:** {profile['id']}")
            st.write(f"**ชื่อ:** {profile['name']}")
        with right:
            st.markdown("### แนวเกมที่ชอบ (GENRES_LIKES)")
            if likes:
                st.dataframe(pd.DataFrame(likes), use_container_width=True, hide_index=True)
            else:
                st.info("ยังไม่มีข้อมูลความชื่นชอบแนวเกม")

elif page == "Recommendations":
    st.subheader("✨ แนวเกมที่แนะนำสำหรับคุณ")
    student_id = student_selector("rec_student")
    rows = recommend_game_genres(student_id)

    st.caption("คะแนนคำนวณจาก: จำนวนเพื่อนในระบบที่ชื่นชอบแนวเกมนี้ (Collaborative Filtering)")
    if not rows:
        st.info("ยังไม่มีคำแนะนำสำหรับผู้ใช้นี้ หรือผู้ใช้อาจจะชอบแนวเกมทั้งหมดไปแล้ว")
    for i, row in enumerate(rows, start=1):
        st.markdown(
            f"""
            <div class="genre-card">
              <span class="score-pill">#{i} · score {row['score']}</span>
              <h3 style="margin:.55rem 0 .2rem 0">{row['recommendation']}</h3>
              <div class="muted">รหัสแนวเกม: {row['game_genre_id']}</div>
              <p><b>เหตุผล:</b> {explain_reason(row['score'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif page == "Graph Explorer":
    st.subheader("🕸️ Graph Explorer")
    student_id = student_selector("graph_student")
    rows = graph_neighborhood(student_id)
    if not rows:
        st.info("ยังไม่มี neighborhood graph")
    else:
        dot = ["digraph G {", 'rankdir="LR";', 'node [shape=box, style="rounded,filled", fillcolor="#f8fafc"];']
        seen_nodes = set()
        for r in rows:
            for nid, label, name in [
                (r["source_id"], r["source_label"], r["source_name"]),
                (r["target_id"], r["target_label"], r["target_name"]),
            ]:
                if nid not in seen_nodes:
                    safe_name = str(name).replace('"', "'")
                    dot.append(f'"{nid}" [label="{safe_name}\\n:{label}"];')
                    seen_nodes.add(nid)
            dot.append(f'"{r["source_id"]}" -> "{r["target_id"]}" [label="{r["relationship"]}"];')
        dot.append("}")
        st.graphviz_chart("\n".join(dot), use_container_width=True)
        with st.expander("ดูข้อมูล edge ที่ใช้วาดกราฟ"):
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif page == "Admin / Setup":
    st.subheader("⚙️ Setup ข้อมูลตัวอย่าง")
    st.warning("ปุ่มนี้ไม่ลบข้อมูลเดิม และใช้ MERGE จึงสามารถกดซ้ำได้โดยไม่ซ้ำซ้อน")
    st.markdown(
        """
        **Graph schema (Game Genre System)**
        - `(:Student)-[:FRIEND_OF]-(:Student)`
        - `(:Student)-[:GENRES_LIKES {genres_like_date}]->(:game_genre)`
        """
    )
    if st.button("สร้าง Constraint + Demo Data", type="primary", use_container_width=True):
        with st.spinner("กำลังสร้างข้อมูล..."):
            seed_demo_data()
        st.success("สร้างข้อมูลตัวอย่างเรียบร้อยแล้ว")
        st.rerun()