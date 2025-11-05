import streamlit as st
import pandas as pd
import plotly.express as px
from personal_progress import (
    add_todo, list_todos, mark_todo_done, delete_todo,
    add_task, list_tasks, delete_task, total_points,
    add_predefined, add_investment, points_per_day, streak_days, PREDEFINED
)
from supabase_handler import supabase
import uuid


# Konfiguracija stranice
st.set_page_config(page_title="Osobni napredak", page_icon="💪", layout="wide")

# Tabovi
tabs = st.tabs(["📈 Napredak", "📝 To-Do lista", "📊 Statistika"])

# =====================
# 📈 TAB 1: Napredak
# =====================
with tabs[0]:
    st.title("💪 Osobni napredak")

    total = total_points()
    st.progress(min(total / 1000, 1.0), f"Ukupno: {total:.1f} / 1000 bodova")

    # ---------- Tablica zadataka ----------
    def show_tasks():
        # Učitaj iz Supabase
        if "progress_df_orig" not in st.session_state:
            res = supabase.table("progress").select("*").order("id", desc=False).execute()
            st.session_state.progress_df_orig = (
                pd.DataFrame(res.data) if res.data else
                pd.DataFrame(columns=["id", "date", "task", "points", "note"])
            ).sort_values("id", ascending=True).reset_index(drop=True)

        # Editor tablice
        edited_df = st.data_editor(
            st.session_state.progress_df_orig,
            num_rows="dynamic",
            use_container_width=True,
            key="progress_editor"
        )

        # Gumb spremi
        if st.button("💾 Spremi promjene"):
            edited_records = [
                r for r in edited_df.to_dict("records")
                if any(v not in (None, "", []) for v in r.values())
            ]

            def ids_from(records):
                out = set()
                for r in records:
                    if r.get("id"):
                        out.add(int(r["id"]))
                return out

            orig_ids = ids_from(st.session_state.progress_df_orig.to_dict("records"))
            curr_ids = ids_from(edited_records)

            # INSERT / UPDATE
            for row in edited_records:
                rid = row.get("id")
                payload = {
                    "date": row.get("date"),
                    "task": row.get("task"),
                    "points": row.get("points"),
                    "note": row.get("note"),
                }
                if rid in orig_ids:
                    supabase.table("progress").update(payload).eq("id", int(rid)).execute()
                else:
                    supabase.table("progress").insert(payload).execute()

            # DELETE
            deleted_ids = orig_ids - curr_ids
            for tid in deleted_ids:
                supabase.table("progress").delete().eq("id", int(tid)).execute()

            # Refresh
            res = supabase.table("progress").select("*").order("id", desc=False).execute()
            st.session_state.progress_df_orig = (
                pd.DataFrame(res.data) if res.data else
                pd.DataFrame(columns=["id", "date", "task", "points", "note"])
            ).sort_values("id", ascending=True).reset_index(drop=True)

            st.success("✅ Promjene spremljene!")
            st.rerun()

    show_tasks()

    # ---------- Dodavanje zadataka ----------
    st.subheader("Dodaj zadatak")

    # Dnevni zadatak
    with st.expander("✅ Dnevni zadatak (0.2 boda)", expanded=True):
        desc = st.text_input("Opis (opcionalno)", key="daily_desc")
        if st.button("Dodaj dnevni zadatak"):
            add_task("Dnevni zadatak", 0.2, desc)
            st.success("Dodano: Dnevni zadatak (+0.2 b)")
            res = supabase.table("progress").select("*").order("id", desc=False).execute()
            st.session_state.progress_df_orig = pd.DataFrame(res.data)
            st.rerun()

    # Predefinirani
    with st.expander("⭐ Predefinirani zadaci"):
        sel = st.selectbox("Odaberi zadatak", [n for n, _ in PREDEFINED])
        pdesc = st.text_input("Opis (opcionalno)", key="pred_desc")
        if st.button("Dodaj predefinirani"):
            add_predefined(sel, pdesc)
            st.success(f"Dodan zadatak: {sel}")
            res = supabase.table("progress").select("*").order("id", desc=False).execute()
            st.session_state.progress_df_orig = pd.DataFrame(res.data)
            st.rerun()

    # Ulaganje
    with st.expander("📈 Uloženo u dionice"):
        amt = st.number_input("Iznos ulaganja (€)", min_value=0.0, step=1000.0, value=10000.0)
        idesc = st.text_input("Opis (opcionalno)", key="inv_desc")
        if st.button("Dodaj ulaganje"):
            add_investment(amt, idesc)
            st.success("Ulaganje dodano.")
            res = supabase.table("progress").select("*").order("id", desc=False).execute()
            st.session_state.progress_df_orig = pd.DataFrame(res.data)
            st.rerun()

    # Vlastiti
    with st.expander("🛠️ Vlastiti zadatak"):
        cname = st.text_input("Naziv", key="custom_name")
        cpoints = st.number_input("Bodovi", min_value=0.0, step=0.1, value=1.0)
        cdesc = st.text_area("Opis (opcionalno)", key="custom_desc")
        if st.button("Dodaj vlastiti zadatak", disabled=not bool(cname.strip())):
            add_task(cname.strip(), cpoints, cdesc)
            st.success(f"Dodan: {cname} (+{cpoints} b)")
            res = supabase.table("progress").select("*").order("id", desc=False).execute()
            st.session_state.progress_df_orig = pd.DataFrame(res.data)
            st.rerun()


# =====================
# 📝 TAB 2: TO-DO LISTA
# =====================
with tabs[1]:
    st.title("📝 Dnevna To-Do lista")

    # Funkcija za reload liste
    def refresh_todos():
        st.session_state.todos = list_todos()

    if "todos" not in st.session_state:
        refresh_todos()

    # Dodavanje
    with st.form("add_todo", clear_on_submit=True):
        title = st.text_input("Dodaj novi zadatak", placeholder="npr. Pročitati 10 stranica knjige")
        submitted = st.form_submit_button("Dodaj")
        if submitted and title.strip():
            add_todo(title.strip())
            st.success("Zadatak dodan!")
            refresh_todos()
            st.rerun()

    # Prikaz
    if st.session_state.todos:
        for todo in st.session_state.todos:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write("✅" if todo["done"] else "⬜️", todo["title"])
            with col2:
                if not todo["done"]:
                    if st.button("✔️", key=f"done_{todo['id']}"):
                        mark_todo_done(todo["id"])
                        refresh_todos()
                        st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{todo['id']}"):
                    delete_todo(todo["id"])
                    refresh_todos()
                    st.rerun()
    else:
        st.info("Nema zadataka trenutno.")


# =====================
# 📊 TAB 3: STATISTIKA
# =====================
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