import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# 🎨 ESTILO MENU NÍVEL 3
# =========================
st.markdown("""
<style>

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #0f172a);
    border-right: 1px solid rgba(255,255,255,0.08);
}

/* MENU */
div[role="radiogroup"] label {
    display: flex;
    align-items: center;
    padding: 14px;
    margin-bottom: 8px;
    border-radius: 12px;
    cursor: pointer;
    color: #cbd5e1;
    transition: all 0.25s ease;
    font-size: 15px;
}

/* HOVER */
div[role="radiogroup"] label:hover {
    background: rgba(59,130,246,0.15);
    transform: translateX(6px);
}

/* ATIVO */
div[role="radiogroup"] input:checked + div {
    background: linear-gradient(90deg,#2563eb,#1d4ed8);
    color: white;
    font-weight: 600;
    transform: scale(1.03);
    box-shadow: 0 0 15px rgba(37,99,235,0.6);
}

/* ANIMAÇÃO LATERAL */
div[role="radiogroup"] input:checked + div::before {
    content: "";
    position: absolute;
    left: 0;
    width: 5px;
    height: 100%;
    background: #60a5fa;
    border-radius: 0 4px 4px 0;
}

/* CLICK */
div[role="radiogroup"] label:active {
    transform: scale(0.96);
}

</style>
""", unsafe_allow_html=True)

# =========================
# 🔥 LOGO
# =========================
st.sidebar.markdown("""
<div style="text-align:center;">
<img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="180">
</div>
""", unsafe_allow_html=True)

# =========================
# DB
# =========================
def connect():
    os.makedirs("uploads", exist_ok=True)
    return sqlite3.connect("banco.db", check_same_thread=False)

def criar_tabelas():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        usuario TEXT UNIQUE,
        email TEXT,
        senha TEXT,
        tipo TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        centro_custo TEXT,
        valor REAL,
        arquivos TEXT,
        status TEXT DEFAULT 'PENDENTE',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_pagamento TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

criar_tabelas()

# =========================
# LOGIN MOCK
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = True
    st.session_state["usuario"] = "admin"
    st.session_state["tipo"] = "admin"

# =========================
# 🚀 MENU CORRIGIDO (AQUI TAVA O ERRO)
# =========================
menu = st.sidebar.radio(
    "",
    ["dashboard", "despesas", "reembolsos"]
)

# =========================
# DASHBOARD
# =========================
if menu == "dashboard":

    st.title("📊 Dashboard")

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"), use_container_width=True)
        st.plotly_chart(px.bar(df, x="centro_custo", y="valor"), use_container_width=True)

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "despesas":

    st.title("💸 Despesas")

    desc = st.text_input("Descrição")
    valor = st.number_input("Valor")

    arquivos = st.file_uploader("Anexar", accept_multiple_files=True)

    if st.button("Enviar"):

        lista = []

        if arquivos:
            for arq in arquivos:
                nome = f"{datetime.now().timestamp()}_{arq.name}"
                caminho = os.path.join("uploads", nome)

                with open(caminho, "wb") as f:
                    f.write(arq.read())

                lista.append(caminho)

        conn = connect()
        conn.execute("""
        INSERT INTO despesas (usuario, descricao, valor, arquivos)
        VALUES (?, ?, ?, ?)
        """, (st.session_state["usuario"], desc, valor, ",".join(lista)))
        conn.commit()
        conn.close()

        st.success("Enviado!")

# =========================
# REEMBOLSOS
# =========================
elif menu == "reembolsos":

    st.title("💰 Reembolsos")

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _, row in df.iterrows():

        st.write(f"{row['descricao']} - R$ {row['valor']}")

        if row["arquivos"]:
            arquivos = row["arquivos"].split(",")

            for arq in arquivos:
                if os.path.exists(arq):

                    if arq.endswith(".pdf"):
                        with open(arq, "rb") as f:
                            st.download_button("PDF", f, file_name=os.path.basename(arq))

                    elif arq.endswith((".png",".jpg",".jpeg")):
                        st.image(arq, width=200)

    conn.close()