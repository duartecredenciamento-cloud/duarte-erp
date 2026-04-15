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

/* LOADING BAR */
.loading-bar {
    width: 100%;
    height: 6px;
    background: #1e293b;
    border-radius: 10px;
    overflow: hidden;
    margin-top: 10px;
}

.loading-bar::after {
    content: "";
    display: block;
    width: 40%;
    height: 100%;
    background: linear-gradient(90deg,#3b82f6,#60a5fa);
    animation: loading 1s infinite;
}

@keyframes loading {
    0% { margin-left: -40%; }
    100% { margin-left: 100%; }
}

/* SUCCESS CHECK */
.success-check {
    font-size: 22px;
    color: #22c55e;
    animation: pop 0.4s ease;
}

@keyframes pop {
    0% { transform: scale(0.5); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
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

    for i, row in df.iterrows():

        status = row["status"]

        classe = {
            "PENDENTE": "status-pendente",
            "APROVADO": "status-aprovado",
            "PAGO": "status-pago",
            "REJEITADO": "status-rejeitado"
        }.get(status, "status")

        cor_valor = "valor-positivo" if status == "PAGO" else "valor-negativo"

        st.markdown('<div class="card">', unsafe_allow_html=True)

        # HEADER
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between;">
            <div>👤 <b>{row['usuario']}</b></div>
            <div class="status {classe}">{status}</div>
        </div>
        """, unsafe_allow_html=True)

        # INFO
        st.markdown(f"""
        <div style="margin-top:8px;">
            📄 {row['descricao']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="valor {cor_valor}">
            💰 R$ {row['valor']}
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"📅 Criado: {row['data_criacao']}")
        st.caption(f"💸 Pago: {row['data_pagamento']}")

        # 📎 ARQUIVOS
        if row["arquivos"]:
            arquivos = row["arquivos"].split(",")

            for arq in arquivos:
                if os.path.exists(arq):

                    if arq.endswith(".pdf"):
                        with open(arq, "rb") as f:
                            st.download_button(
                                "📄 PDF",
                                f,
                                file_name=os.path.basename(arq),
                                key=f"pdf_{row['id']}_{i}"
                            )

                    elif arq.endswith((".png",".jpg",".jpeg")):
                        st.image(arq, width=200)

                    else:
                        with open(arq, "rb") as f:
                            st.download_button(
                                "📎 Arquivo",
                                f,
                                file_name=os.path.basename(arq),
                                key=f"file_{row['id']}_{i}"
                            )

        col1, col2, col3 = st.columns(3)

        # ✅ APROVAR
        if col1.button("Aprovar", key=f"ap_{row['id']}_{i}"):
            conn.execute("UPDATE despesas SET status='APROVADO' WHERE id=?", (row["id"],))
            conn.commit()
            st.rerun()

        # ❌ REJEITAR
        if col2.button("Rejeitar", key=f"rej_{row['id']}_{i}"):
            conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?", (row["id"],))
            conn.commit()
            st.rerun()

        # 💰 PAGAR
        if col3.button("Pagar", key=f"pg_{row['id']}_{i}"):

            c = conn.cursor()
            c.execute("SELECT nome, email FROM usuarios WHERE usuario=?", (row["usuario"],))
            user_data = c.fetchone()

            if user_data:
                nome, email = user_data
                enviar_email(email, nome, row["descricao"], row["valor"], row["categoria"])

            conn.execute("""
                UPDATE despesas 
                SET status='PAGO', data_pagamento=? 
                WHERE id=?
            """, (datetime.now(), row["id"]))

            conn.commit()

            st.success("💸 Pago com sucesso + Email enviado!")
            st.balloons()

            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    conn.close()