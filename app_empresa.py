import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Duarte Gestão ERP",
    page_icon="🏢",
    layout="wide"
)

# =========================
# BANCO
# =========================
conn = sqlite3.connect("duarte.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    username TEXT PRIMARY KEY,
    senha TEXT,
    perfil TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    data TEXT,
    tipo TEXT,
    descricao TEXT,
    valor REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    acao TEXT,
    data_hora TEXT
)
""")

conn.commit()

# =========================
# CRIPTOGRAFIA
# =========================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def criar_usuarios():
    usuarios = [
        ("admin", hash_senha("1234"), "admin"),
        ("financeiro", hash_senha("1234"), "financeiro"),
        ("auditor", hash_senha("1234"), "auditor"),
    ]

    for u in usuarios:
        cursor.execute("INSERT OR IGNORE INTO usuarios VALUES (?, ?, ?)", u)
    conn.commit()

criar_usuarios()

# =========================
# LOGIN
# =========================
if "logado" not in st.session_state:
    st.session_state.logado = False

def login():
    st.title("🔐 Duarte Gestão ERP")

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        cursor.execute("SELECT * FROM usuarios WHERE username=?", (user,))
        result = cursor.fetchone()

        if result and result[1] == hash_senha(senha):
            st.session_state.logado = True
            st.session_state.user = user
            st.session_state.perfil = result[2]
            st.rerun()
        else:
            st.error("Login inválido")

if not st.session_state.logado:
    login()
    st.stop()

# =========================
# LOG
# =========================
def log(acao):
    cursor.execute(
        "INSERT INTO logs (usuario, acao, data_hora) VALUES (?, ?, ?)",
        (st.session_state.user, acao, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

# =========================
# CARREGAR DADOS
# =========================
df = pd.read_sql("SELECT * FROM gastos", conn)

# =========================
# UI
# =========================
st.image("https://www.duartegestao.com.br/images/logo-duartegestao.png", width=180)
st.title(f"💼 ERP Duarte Gestão - {st.session_state.perfil.upper()}")

menu = st.sidebar.radio(
    "Menu",
    ["📊 Dashboard", "➕ Lançar", "✏️ Editar/Excluir", "📅 Análise", "📜 Logs"]
)

# =========================
# DASHBOARD
# =========================
if menu == "📊 Dashboard":

    total = df["valor"].sum() if not df.empty else 0

    col1, col2 = st.columns(2)
    col1.metric("💰 Total", f"R$ {total:,.2f}")
    col2.metric("📦 Registros", len(df))

    if not df.empty:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["mes"] = df["data"].dt.to_period("M").astype(str)

        grafico = df.groupby("mes")["valor"].sum()
        st.line_chart(grafico)

# =========================
# LANÇAR
# =========================
elif menu == "➕ Lançar":

    if st.session_state.perfil == "auditor":
        st.warning("Sem permissão")
        st.stop()

    data = st.date_input("Data")
    tipo = st.selectbox("Categoria", ["Alimentação", "Transporte", "Material", "Outros"])
    valor = st.number_input("Valor", min_value=0.0)
    descricao = st.text_input("Descrição")

    if st.button("Salvar"):
        cursor.execute("""
            INSERT INTO gastos (usuario, data, tipo, descricao, valor)
            VALUES (?, ?, ?, ?, ?)
        """, (st.session_state.user, str(data), tipo, descricao, valor))
        conn.commit()

        log("NOVO GASTO")
        st.success("Salvo!")
        st.rerun()

# =========================
# EDITAR / EXCLUIR
# =========================
elif menu == "✏️ Editar/Excluir":

    if df.empty:
        st.warning("Sem dados")
        st.stop()

    st.dataframe(df, use_container_width=True)

    if st.session_state.perfil == "auditor":
        st.warning("Sem permissão")
        st.stop()

    rid = st.number_input("ID do registro", min_value=1)

    registro = df[df["id"] == rid]

    if not registro.empty:
        registro = registro.iloc[0]

        data = st.text_input("Data", registro["data"])
        tipo = st.selectbox(
            "Categoria",
            ["Alimentação", "Transporte", "Material", "Outros"],
            index=["Alimentação","Transporte","Material","Outros"].index(registro["tipo"])
            if registro["tipo"] in ["Alimentação","Transporte","Material","Outros"] else 0
        )
        descricao = st.text_input("Descrição", registro["descricao"])
        valor = st.number_input("Valor", value=float(registro["valor"]))

        col1, col2 = st.columns(2)

        if col1.button("Salvar alteração"):
            cursor.execute("""
                UPDATE gastos
                SET data=?, tipo=?, descricao=?, valor=?
                WHERE id=?
            """, (data, tipo, descricao, valor, rid))
            conn.commit()

            log(f"EDITOU ID {rid}")
            st.success("Atualizado!")
            st.rerun()

        if col2.button("Excluir"):
            cursor.execute("DELETE FROM gastos WHERE id=?", (rid,))
            conn.commit()

            log(f"EXCLUIU ID {rid}")
            st.warning("Removido!")
            st.rerun()

# =========================
# ANÁLISE
# =========================
elif menu == "📅 Análise":

    if not df.empty:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")

        meses = df["data"].dt.to_period("M").astype(str).unique()

        mes = st.selectbox("Mês", sorted(meses))

        filtrado = df[df["data"].dt.to_period("M").astype(str) == mes]

        st.dataframe(filtrado, use_container_width=True)
        st.bar_chart(filtrado.groupby("tipo")["valor"].sum())

# =========================
# LOGS
# =========================
elif menu == "📜 Logs":

    logs = pd.read_sql("SELECT * FROM logs ORDER BY id DESC", conn)
    st.dataframe(logs, use_container_width=True)