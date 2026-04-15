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
# 🎨 ESTILO TOP
# =========================
st.markdown("""
<style>

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #0f172a);
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* MENU */
div[role="radiogroup"] label {
    display: flex;
    align-items: center;
    padding: 14px;
    margin-bottom: 8px;
    border-radius: 12px;
    color: #cbd5e1;
    cursor: pointer;
    transition: all 0.3s ease;
}

div[role="radiogroup"] label:hover {
    background: rgba(59,130,246,0.15);
    transform: translateX(8px);
}

div[role="radiogroup"] input:checked + div {
    background: linear-gradient(90deg,#2563eb,#1d4ed8);
    color: #fff;
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(37,99,235,0.5);
}

/* CARD PADRÃO (REEMBOLSO + DESPESA) */
.card {
    background: #0f172a;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    transition: all 0.3s ease;
    animation: fadeIn 0.4s ease-in-out;
}

.card:hover {
    transform: translateY(-5px) scale(1.02);
    box-shadow: 0 10px 25px rgba(0,0,0,0.4);
}

/* ANIMAÇÃO ENTRADA */
@keyframes fadeIn {
    from {opacity: 0; transform: translateY(15px);}
    to {opacity: 1; transform: translateY(0);}
}

/* BOTÕES */
.stButton>button {
    border-radius: 10px;
    transition: 0.2s;
}

.stButton>button:hover {
    transform: scale(1.05);
}

/* SUCESSO ANIMADO */
.success-check {
    background: linear-gradient(90deg,#22c55e,#16a34a);
    padding: 12px;
    border-radius: 10px;
    color: white;
    text-align: center;
    font-weight: bold;
    animation: pop 0.3s ease;
}

@keyframes pop {
    from {transform: scale(0.8); opacity: 0;}
    to {transform: scale(1); opacity: 1;}
}

</style>
""", unsafe_allow_html=True)

# =========================
# 🔥 LOGO
# =========================
st.markdown("""
<div style="text-align:center;">
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
<img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
</a>
</div>
""", unsafe_allow_html=True)

# =========================
# 📧 EMAIL
# =========================
EMAIL_REMETENTE = "financeiro.duartegestao@gmail.com"
SENHA_EMAIL = "adre gnlu xrmg eheu"

def enviar_email(destinatario, nome, descricao, valor, categoria):
    try:
        corpo = f"""
Olá {nome},

Seu reembolso foi aprovado e pago com sucesso!

Descrição: {descricao}
Categoria: {categoria}
Valor: R$ {valor}

⚠️ NÃO RESPONDER ESTE EMAIL

Duarte Gestão
"""
        msg = MIMEText(corpo)
        msg["Subject"] = "💰 Reembolso Pago"
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = destinatario

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_EMAIL)
            server.send_message(msg)

    except Exception as e:
        st.error(f"Erro email: {e}")

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

def criar_admins():
    conn = connect()
    c = conn.cursor()

    usuarios = [
        ("Admin","admin","admin@email.com","123456","admin"),
        ("Financeiro","financeiro","financeiro@email.com","123456","financeiro"),
        ("Operacional","operacional","operacional@email.com","123456","operacional")
    ]

    for nome, user, email, senha, tipo in usuarios:
        hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        try:
            c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                      (nome, user, email, hash, tipo))
        except:
            pass

    conn.commit()
    conn.close()

criar_tabelas()
criar_admins()

# =========================
# LOGIN
# =========================
def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode(), hash.encode())

def login(user, senha):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=?", (user,))
    r = c.fetchone()
    conn.close()
    if r and verificar_senha(senha, r[4]):
        return r
    return None

if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# LOGIN / CADASTRO
# =========================
if not st.session_state["logado"]:

    abas = st.tabs(["Login", "Criar Conta"])

    with abas[0]:
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[2]
                st.session_state["tipo"] = r[5]
                st.session_state["nome"] = r[1]
                st.session_state["email"] = r[3]
                st.rerun()

    with abas[1]:
        nome = st.text_input("Nome")
        user = st.text_input("Usuário")
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")

        if st.button("Criar Conta"):
            conn = connect()
            try:
                hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                conn.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                             (nome, user, email, hash, "usuario"))
                conn.commit()
                st.success("Conta criada!")
            except:
                st.error("Erro ao criar")
            conn.close()

    st.stop()

# =========================
# MENU
# =========================
menu = st.sidebar.radio(
    "",
    ["dashboard", "despesas", "reembolsos"],
    format_func=lambda x: {
        "dashboard": "📊 Dashboard",
        "despesas": "💸 Despesas",
        "reembolsos": "💰 Reembolsos"
    }[x]
)

# =========================
# DASHBOARD
# =========================
if menu == "dashboard":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.title("📊 Dashboard")

    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"), use_container_width=True)
        st.plotly_chart(px.bar(df, x="centro_custo", y="valor"), use_container_width=True)

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "despesas":

    tab1, tab2 = st.tabs(["Nova", "Minhas"])

    categorias = [
    "Limpeza",
    "Remuneração Sócios",
    "Alimentação",
    "Telefonia e Internet",
    "Software E Licenças - Informática",
    "Transportes / Logística",
    "Material de Escritório",
    "Equipamentos de Informática",
    "Estacionamento",
    "Móveis e Utensílios",
    "Despesas de Viagens",
    "Máquinas e Equipamentos"
]
    centros = [
    "CREDENCIAMENTO",
    "REDE",
    "DIRETORIA",
    "DUARTE GESTÃO",
    "MARKETING",
    "FINANCEIRO"
]

    with tab1:
        desc = st.text_input("Descrição")
        valor = st.number_input("Valor")
        categoria = st.selectbox("Categoria", categorias)
        centro = st.selectbox("Centro de Custo", centros)
        arquivos = st.file_uploader("Anexos", accept_multiple_files=True)

        if st.button("Enviar"):

            lista= []

    if arquivos:
        for arq in arquivos:
            nome = f"{datetime.now().timestamp()}_{arq.name}"
            caminho = os.path.join("uploads", nome)

            with open(caminho, "wb") as f:
                f.write(arq.read())

            lista.append(caminho)

    if arquivos:
        for arq in arquivos:
            nome = f"{datetime.now().timestamp()}_{arq.name}"
            caminho = os.path.join("uploads", nome)

            with open(caminho, "wb") as f:
                f.write(arq.read())

            lista.append(caminho)

    conn = connect()
    conn.execute("""
        INSERT INTO despesas (usuario, descricao, categoria, centro_custo, valor, arquivos)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (st.session_state["usuario"], desc, categoria, centro, valor, ",".join(lista)))

    conn.commit()
    conn.close()

    st.markdown('<div class="success-check">✔ Enviado com sucesso!</div>', unsafe_allow_html=True)
    st.balloons()
    st.rerun()
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
            INSERT INTO despesas (usuario, descricao, categoria, centro_custo, valor, arquivos)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (st.session_state["usuario"], desc, categoria, centro, valor, ",".join(lista)))
    conn.commit()
    conn.close()

    st.success("Enviado!")

    with tab2:
        conn = connect()
        df = pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'", conn)

        for _, row in df.iterrows():
            st.write(f"{row['descricao']} - R$ {row['valor']}")

        conn.close()

# =========================
# REEMBOLSOS
# =========================
elif menu == "reembolsos":

    if st.session_state["tipo"] not in ["admin", "financeiro", "operacional"]:
        st.warning("Sem permissão")
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas ORDER BY id DESC", conn)

    for _, row in df.iterrows():

       st.markdown('<div class="card">', unsafe_allow_html=True)

    st.write(f"👤 {row['usuario']} | 💰 R$ {row['valor']} | 📌 {row['status']}")
    st.write(f"📅 {row['data_criacao']}")

    col1, col2, col3 = st.columns(3)

    if col1.button("✅ Aprovar", key=f"ap_{row['id']}"):
        conn.execute("UPDATE despesas SET status='APROVADO' WHERE id=?", (row["id"],))
        conn.commit()
        st.rerun()

    if col2.button("❌ Rejeitar", key=f"rej_{row['id']}"):
        conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?", (row["id"],))
        conn.commit()
        st.rerun()

    if col3.button("💰 Pagar", key=f"pg_{row['id']}"):
        conn.execute("UPDATE despesas SET status='PAGO' WHERE id=?", (row["id"],))
        conn.commit()
        st.success("Pago!")
        st.balloons()
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    conn.close()