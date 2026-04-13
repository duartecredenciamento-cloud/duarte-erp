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
# 🎨 ESTILO PROFISSIONAL
# =========================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg,#020617,#0f172a);
    color: #e2e8f0;
}

/* LOGO */
.logo img {
    transition: 0.3s;
}
.logo img:hover {
    transform: scale(1.08);
}

/* BOTÕES */
.stButton button {
    background: linear-gradient(90deg,#2563eb,#06b6d4);
    border-radius: 10px;
    color: white;
    font-weight: bold;
    border: none;
    padding: 8px;
    transition: 0.3s;
}
.stButton button:hover {
    transform: scale(1.05);
    box-shadow: 0px 0px 15px rgba(37,99,235,0.6);
}

/* CARDS */
.card {
    background: linear-gradient(145deg,#1e293b,#020617);
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    box-shadow: 0px 0px 15px rgba(0,0,0,0.4);
    animation: fadeIn 0.4s ease-in;
}

@keyframes fadeIn {
    from {opacity:0; transform:translateY(10px);}
    to {opacity:1; transform:translateY(0);}
}
</style>
""", unsafe_allow_html=True)

# =========================
# 🔥 LOGO TOPO
# =========================
st.markdown("""
<div class="logo" style="text-align:center;">
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
<img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
</a>
</div>
""", unsafe_allow_html=True)

# =========================
# EMAIL
# =========================
EMAIL_REMETENTE = "financeiro.duartegestao@gmail.com"
SENHA_EMAIL = "bppd twbk bupr pzws"

def enviar_email(destinatario, nome, descricao, valor, categoria):
    corpo = f"""
Olá {nome},

🎉 Seu reembolso foi PAGO!

📌 {descricao}
📂 {categoria}
💰 R$ {valor}

⚠️ Não responda este e-mail.

Duarte Gestão 🚀
"""
    msg = MIMEText(corpo)
    msg["Subject"] = "Reembolso Pago"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = destinatario

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_EMAIL)
            server.send_message(msg)
    except:
        pass

# =========================
# DB
# =========================
def connect():
    os.makedirs("uploads", exist_ok=True)
    return sqlite3.connect("banco.db", check_same_thread=False)

def criar_tabelas():
    conn = connect()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        usuario TEXT,
        email TEXT,
        senha TEXT,
        admin INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        centro TEXT,
        valor REAL,
        status TEXT,
        data_criacao TEXT,
        data_pagamento TEXT
    )
    """)

    conn.commit()
    conn.close()

def criar_admin():
    conn = connect()
    senha_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL,?,?,?,?,?)",
                     ("Admin","admin","admin@email.com",senha_hash,1))
        conn.commit()
    except:
        pass
    conn.close()

criar_tabelas()
criar_admin()

# =========================
# AUTH
# =========================
def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode(), hash.encode())

def login(user, senha):
    conn = connect()
    r = conn.execute("SELECT * FROM usuarios WHERE usuario=?", (user,)).fetchone()
    conn.close()
    if r and verificar_senha(senha, r[4]):
        return r
    return None

# =========================
# SESSION
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# LOGIN
# =========================
if not st.session_state["logado"]:

    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        r = login(u,s)
        if r:
            st.session_state["logado"]=True
            st.session_state["usuario"]=r[2]
            st.session_state["admin"]=r[5]
            st.session_state["nome"]=r[1]
            st.session_state["email"]=r[3]
            st.rerun()

    st.stop()

# =========================
# SIDEBAR LOGO
# =========================
st.sidebar.markdown("""
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
<img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="160">
</a>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("Menu", ["Dashboard","Despesas","Reembolsos"])

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    if not df.empty:
        st.metric("Total", f"R$ {df['valor'].sum():.2f}")
        st.plotly_chart(px.pie(df, names="categoria", values="valor"))
        st.plotly_chart(px.bar(df, x="centro", y="valor"))

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    desc = st.text_input("Descrição")
    valor = st.number_input("Valor")

    if st.button("Enviar"):
        conn = connect()
        conn.execute("""
        INSERT INTO despesas VALUES (NULL,?,?,?,?,?,?,?,?)
        """,(st.session_state["usuario"],desc,"Outros","FINANCEIRO",valor,
             "PENDENTE",datetime.now(),None))
        conn.commit()
        conn.close()
        st.success("Enviado!")

# =========================
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if not st.session_state["admin"]:
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _,row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"👤 {row['usuario']}")
        st.write(f"📌 {row['descricao']}")
        st.write(f"💰 R$ {row['valor']}")
        st.write(f"📊 Status: {row['status']}")
        st.write(f"🕒 Criado em: {row['data_criacao']}")
        st.write(f"💸 Pago em: {row['data_pagamento']}")

        col1,col2 = st.columns(2)

        if col1.button("💰 Pagar", key=f"pg_{row['id']}"):
            user = conn.execute("SELECT nome,email FROM usuarios WHERE usuario=?",
                                (row["usuario"],)).fetchone()

            if user:
                enviar_email(user[1], user[0], row["descricao"], row["valor"], row["categoria"])

            conn.execute("UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?",
                         (datetime.now(), row["id"]))
            conn.commit()

            st.success("Pago + Email enviado!")

        if col2.button("❌ Excluir", key=f"del_{row['id']}"):
            conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
            conn.commit()
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    conn.close()