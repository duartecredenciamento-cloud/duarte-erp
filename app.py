import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# ESTILO
# =========================
st.markdown("""
<style>
body {background-color:#0f172a;color:#e2e8f0;}
.card {
    background: linear-gradient(145deg,#1e293b,#0f172a);
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
}
.title {
    font-size:30px;
    font-weight:bold;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

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
        usuario TEXT UNIQUE,
        senha TEXT,
        admin INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        valor REAL,
        arquivos TEXT,
        status TEXT DEFAULT 'PENDENTE',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_aprovacao TIMESTAMP,
        data_pagamento TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

criar_tabelas()

# =========================
# AUTH
# =========================
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt())

def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode(), hash)

def login(user, senha):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=?", (user,))
    result = c.fetchone()
    conn.close()

    if result and verificar_senha(senha, result[2].encode()):
        
        # 🔥 DEFINE SEU USUÁRIO COMO ADMIN
        if result[1] == "erickteste":  # 👈 TROCA AQUI
            return (result[0], result[1], result[2], 1)

        return result

    return None

def criar_usuario(user, senha, admin):
    conn = connect()
    c = conn.cursor()
    senha_hash = hash_senha(senha)

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", (user, senha_hash.decode(), admin))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# =========================
# LOGIN / CADASTRO
# =========================
if not st.session_state["logado"]:

    st.markdown("""
    <div style="text-align:center;">
        <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
    </div>
    """, unsafe_allow_html=True)

    abas = st.tabs(["Login", "Criar Conta", "Reset Senha"])

    with abas[0]:
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[1]
                st.session_state["admin"] = r[3]
                st.rerun()
            else:
                st.error("Erro no login")

    with abas[1]:
        u = st.text_input("Novo usuário")
        s = st.text_input("Nova senha", type="password")

        if st.button("Criar"):
            if criar_usuario(u, s, 0):
                st.success("Criado!")
            else:
                st.error("Usuário existe")

    with abas[2]:
        u = st.text_input("Usuário reset")
        s = st.text_input("Nova senha", type="password")

        if st.button("Resetar"):
            conn = connect()
            conn.execute("UPDATE usuarios SET senha=? WHERE usuario=?",
                         (hash_senha(s).decode(), u))
            conn.commit()
            conn.close()
            st.success("Senha atualizada")

    st.stop()

# =========================
# MENU
# =========================
menu = st.sidebar.radio("Menu", ["Dashboard", "Despesas", "Reembolsos"])

if st.sidebar.button("Sair"):
    st.session_state["logado"] = False
    st.rerun()

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":
    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.metric("Total", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")

    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"))

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    desc = st.text_input("Descrição")
    valor = st.number_input("Valor", min_value=0.0)
    categoria = st.selectbox("Categoria", ["Alimentação", "Transporte", "Outros"])
    arquivos = st.file_uploader("Nota", accept_multiple_files=True)

    if st.button("Enviar"):
        lista = []
        for arq in arquivos:
            path = f"uploads/{arq.name}"
            with open(path, "wb") as f:
                f.write(arq.read())
            lista.append(path)

        conn = connect()
        conn.execute("""
        INSERT INTO despesas (usuario, descricao, categoria, valor, arquivos)
        VALUES (?, ?, ?, ?, ?)
        """, (st.session_state["usuario"], desc, categoria, valor, ",".join(lista)))

        conn.commit()
        conn.close()

        st.success("Enviado!")

# =========================
# REEMBOLSOS (ADMIN)
# =========================
elif menu == "Reembolsos":

    if not st.session_state.get("admin"):
        st.error("Apenas admin")
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _, row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"👤 {row['usuario']} | 💰 {row['valor']} | {row['status']}")
        st.write(f"📅 Criado: {row['data_criacao']}")
        st.write(f"✔ Aprovado: {row['data_aprovacao']}")
        st.write(f"💸 Pago: {row['data_pagamento']}")

        col1, col2, col3 = st.columns(3)

        if col1.button(f"Aprovar {row['id']}"):
            conn.execute("""
            UPDATE despesas SET status='APROVADO', data_aprovacao=?
            WHERE id=?
            """, (datetime.now(), row['id']))

        if col2.button(f"Pagar {row['id']}"):
            conn.execute("""
            UPDATE despesas SET status='PAGO', data_pagamento=?
            WHERE id=?
            """, (datetime.now(), row['id']))

        if col3.button(f"Rejeitar {row['id']}"):
            conn.execute("""
            UPDATE despesas SET status='REJEITADO'
            WHERE id=?
            """, (row['id'],))

        st.markdown('</div>', unsafe_allow_html=True)

    conn.commit()
    conn.close()