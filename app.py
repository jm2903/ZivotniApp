import streamlit as st
import pandas as pd
import plotly.express as px
from personal_progress import (
    init_db, init_todo_db, add_todo, list_todos, mark_todo_done, delete_todo,
    add_task, list_tasks, delete_task, total_points,
    reset_all_data, reset_completed_todos,
    points_per_day, streak_days
)

st.set_page_config(page_title="Osobni napredak", page_icon="💪", layout="wide")
init_db()
init_todo_db()
reset_completed_todos()

tabs = st.tabs(["📈 Napredak", "📝 To-Do lista", "📊 Statistika"])

# --- TAB 1: Napredak ---
with tabs[0]:
    st.title("💪 Osobni napredak")
    total = total_points()
    st.progress(min(total / 1000, 1.0), f"Ukupno: {total:.1f} / 1000 bodova")

    rows = list_tasks()
    st.write(f"Prikazano zapisa: {len(rows)} | Bodova ukupno: {total:.1f}")
    if rows:
        df = pd.DataFrame([t.__dict__ for t in rows])
        st.dataframe(df, use_container_width=True, hide_index=True)
        del_id = st.number_input("Obriši zapis (upiši ID)", min_value=0, step=1, value=0)
        if st.button("Obriši zapis"):
            if del_id > 0:
                delete_task(int(del_id))
                st.rerun()
    else:
        st.info("Još nema zapisa.")

    # --- Dodavanje zadataka ---
    st.subheader("Dodaj zadatak")

    with st.expander("✅ Dnevni zadatak (0.2 boda)", expanded=True):
        desc = st.text_input("Opis (opcionalno)", key="daily_desc")
        if st.button("Dodaj dnevni zadatak"):
            add_task("Dnevni zadatak", 0.2, desc)
            st.success("Dodano: Dnevni zadatak (+0.2 b)")
            st.rerun()

    with st.expander("⭐ Predefinirani zadaci"):
        from personal_progress import PREDEFINED, add_predefined
        sel = st.selectbox("Odaberi zadatak", [n for n, _ in PREDEFINED])
        pdesc = st.text_input("Opis (opcionalno)", key="pred_desc")
        if st.button("Dodaj predefinirani"):
            add_predefined(sel, pdesc)
            st.success(f"Dodan zadatak: {sel}")
            st.rerun()

    with st.expander("📈 Uloženo u dionice"):
        from personal_progress import add_investment
        amt = st.number_input("Iznos ulaganja (€)", min_value=0.0, step=1000.0, value=10000.0)
        idesc = st.text_input("Opis (opcionalno)", key="inv_desc")
        if st.button("Dodaj ulaganje"):
            add_investment(amt, idesc)
            st.success("Ulaganje dodano.")
            st.rerun()

    with st.expander("🛠️ Vlastiti zadatak"):
        cname = st.text_input("Naziv", key="custom_name")
        cpoints = st.number_input("Bodovi", min_value=0.0, step=0.1, value=1.0)
        cdesc = st.text_area("Opis (opcionalno)", key="custom_desc")
        if st.button("Dodaj vlastiti zadatak", disabled=not bool(cname.strip())):
            add_task(cname.strip(), cpoints, cdesc)
            st.success(f"Dodan: {cname} (+{cpoints} b)")
            st.rerun()

# --- TAB 2: TO-DO LISTA ---
with tabs[1]:
    st.title("📝 Dnevna To-Do lista")
    todos = list_todos()
    with st.form("add_todo"):
        title = st.text_input("Dodaj novi zadatak", placeholder="npr. Pročitati 10 stranica knjige")
        if st.form_submit_button("Dodaj"):
            if title.strip():
                add_todo(title.strip())
                st.success("Zadatak dodan!")
                st.rerun()

    if todos:
        for todo in todos:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write("✅" if todo["done"] else "⬜️", todo["title"])
            with col2:
                if not todo["done"]:
                    if st.button("✔️", key=f"done_{todo['id']}"):
                        mark_todo_done(todo["id"])
                        st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{todo['id']}"):
                    delete_todo(todo["id"])
                    st.rerun()
    else:
        st.info("Nema zadataka trenutno.")

# --- TAB 3: STATISTIKA ---
with tabs[2]:
    st.title("📊 Statistika napretka")
    data = points_per_day()
    if data:
        df = pd.DataFrame({"Datum": list(data.keys()), "Bodovi": list(data.values())})
        fig = px.line(df, x="Datum", y="Bodovi", title="Ukupno bodova po danu", markers=True)
        st.plotly_chart(fig, use_container_width=True)
        st.metric("🔥 Streak dana zaredom", streak_days())
        # Kalendar aktivnosti
        df["Datum"] = pd.to_datetime(df["Datum"])
        df["Aktivan"] = 1
        cal = px.density_heatmap(
            df, x=df["Datum"].dt.day, y=df["Datum"].dt.month,
            z="Aktivan", nbinsx=31, nbinsy=12,
            color_continuous_scale=["#f0f0f0", "#00cc44"]
        )
        cal.update_layout(title="📆 Aktivnost kroz godinu", xaxis_title="Dan", yaxis_title="Mjesec")
        st.plotly_chart(cal, use_container_width=True)
    else:
        st.info("Još nema dovoljno podataka za statistiku.")

# --- RESET SVEGA ---
st.divider()
st.subheader("⚙️ Postavke / Reset")
if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False
if not st.session_state.confirm_reset:
    if st.button("🧨 Resetiraj sve podatke"):
        st.session_state.confirm_reset = True
else:
    st.warning("Ova akcija će izbrisati SVE podatke i početi ispočetka.")
    if st.button("✅ Da, resetiraj sve"):
        reset_all_data()
        st.session_state.confirm_reset = False
        st.success("Sve obrisano. Aplikacija resetirana.")
        st.rerun()
    if st.button("❌ Odustani"):
        st.session_state.confirm_reset = False
        st.rerun()