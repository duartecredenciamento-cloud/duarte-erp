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
body {background: linear-gradient(135deg,#020617,#0f172a); color:#e2e8f0;}

.logo img:hover {transform:scale(1.05); transition:0.3s;}

.card {
    background:#1e293b;
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    animation:fadeIn 0.4s ease-in;
}
@keyframes fadeIn {
    from {opacity:0;}
    to {opacity:1;}
}

.stButton button {
    background:linear-gradient(90deg,#2563eb,#06b6d4);
    border:none;
    border-radius:10px;
    color:white;
    font-weight:bold;
}
</style>
""", unsafe_allow_html=True)

# =========================
# LOGO
# =========================
st.markdown("""
<div class="logo" style="text-align:center;">
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
<img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
</a>
</div>
""", unsafe_allow_html=True)

# =========================
# EMAIL CONFIG
# =========================
EMAIL_REMETENTE = "financeiro.duartegestao@gmail.com"
SENHA_EMAIL = "aywd uklm zpkl mqgr"

def enviar_email(destinatario, nome, descricao, valor, categoria):
    corpo = f"""
Olá {nome},

Seu reembolso foi pago!

Descrição: {descricao}
Categoria: {categoria}
Valor: R$ {valor}

Não responda este e-mail.

Duarte Gestão
"""
    msg = MIMEText(corpo)
    msg["Subject"] = "Reembolso Pago"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = destinatario

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL_REMETENTE, SENHA_EMAIL)
            s.send_message(msg)
    except:
        pass

# =========================
# LISTAS
# =========================
CATEGORIAS = [
"Limpeza","Remuneração Sócios","Alimentação","Telefonia e Internet",
"Software E Licenças - Informática","Transportes / Logística",
"Material de Escritório","Equipamentos de Informática",
"Estacionamento","Móveis e Utensílios",
"Despesas de Viagens","Máquinas e Equipamentos"
]

CENTROS = [
"CREDENCIAMENTO","REDE","DIRETORIA",
"DUARTE GESTÃO","MARKETING","FINANCEIRO"
]

# =========================
# DB
# =========================
def connect():
    os.makedirs("uploads", exist_ok=True)
    return sqlite3.connect("banco.db", check_same_thread=False)

def criar():
    conn = connect()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY,
        nome TEXT,
        usuario TEXT,
        email TEXT,
        senha TEXT,
        admin INTEGER
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        centro TEXT,
        valor REAL,
        arquivos TEXT,
        status TEXT,
        data_criacao TEXT,
        data_pagamento TEXT
    )
    """)
    conn.commit()
    conn.close()

def criar_admin():
    conn = connect()
    senha = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL,?,?,?,?,?)",
                     ("Admin","admin","admin@email.com",senha,1))
        conn.commit()
    except:
        pass
    conn.close()

criar()
criar_admin()

# =========================
# AUTH
# =========================
def login(u,s):
    conn = connect()
    r = conn.execute("SELECT * FROM usuarios WHERE usuario=?", (u,)).fetchone()
    conn.close()
    if r and bcrypt.checkpw(s.encode(), r[4].encode()):
        return r

def criar_user(nome,u,e,s):
    conn = connect()
    senha = bcrypt.hashpw(s.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL,?,?,?,?,?)",
                     (nome,u,e,senha,0))
        conn.commit()
        return True
    except:
        return False

# =========================
# SESSION
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# LOGIN + CADASTRO
# =========================
if not st.session_state["logado"]:

    tab1,tab2 = st.tabs(["Login","Criar Conta"])

    with tab1:
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

    with tab2:
        n = st.text_input("Nome")
        u = st.text_input("Usuário")
        e = st.text_input("Email")
        s = st.text_input("Senha", type="password")
        if st.button("Criar Conta"):
            if criar_user(n,u,e,s):
                st.success("Conta criada!")

    st.stop()

# =========================
# MENU
# =========================
menu = st.sidebar.radio("Menu", ["Dashboard","Despesas","Reembolsos"])

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":
    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)
    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"))
        st.plotly_chart(px.bar(df, x="centro", y="valor"))
    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    tab1,tab2 = st.tabs(["Nova","Minhas"])

    # NOVA
    with tab1:
        desc = st.text_input("Descrição")
        valor = st.number_input("Valor")
        cat = st.selectbox("Categoria", CATEGORIAS)
        centro = st.selectbox("Centro", CENTROS)
        arquivos = st.file_uploader("Arquivos", accept_multiple_files=True)

        if st.button("Enviar"):
            lista=[]
            for arq in arquivos:
                path=f"uploads/{arq.name}"
                with open(path,"wb") as f:
                    f.write(arq.read())
                lista.append(path)

            conn=connect()
            conn.execute("""
            INSERT INTO despesas VALUES (NULL,?,?,?,?,?,?,?,?,?)
            """,(st.session_state["usuario"],desc,cat,centro,valor,
                 ",".join(lista),"PENDENTE",datetime.now(),None))
            conn.commit()
            conn.close()
            st.success("Enviado!")

    # MINHAS
    with tab2:
        conn=connect()
        df=pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'",conn)

        for _,row in df.iterrows():
            st.markdown('<div class="card">',unsafe_allow_html=True)

            st.write(row["descricao"],row["valor"],row["status"])

            # anexos
            if row["arquivos"]:
                for arq in row["arquivos"].split(","):
                    if arq.endswith((".png",".jpg",".jpeg")):
                        st.image(arq,width=200)
                    elif arq.endswith(".pdf"):
                        with open(arq,"rb") as f:
                            st.download_button("PDF",f,file_name=arq,key=f"pdf_{row['id']}")

            col1,col2=st.columns(2)

            if col1.button("Excluir",key=f"del_{row['id']}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
                conn.commit()
                st.rerun()

            if col2.button("Editar",key=f"edit_{row['id']}"):
                st.warning("Edição em breve")

            st.markdown('</div>',unsafe_allow_html=True)

        conn.close()

# =========================
# REEMBOLSOS ADMIN
# =========================
elif menu == "Reembolsos":

    if not st.session_state["admin"]:
        st.stop()

    conn=connect()
    df=pd.read_sql("SELECT * FROM despesas",conn)

    # filtros
    user=st.selectbox("Usuário",["Todos"]+list(df["usuario"].unique()))
    status=st.selectbox("Status",["Todos","PENDENTE","PAGO"])

    if user!="Todos":
        df=df[df["usuario"]==user]
    if status!="Todos":
        df=df[df["status"]==status]

    for _,row in df.iterrows():
        st.markdown('<div class="card">',unsafe_allow_html=True)

        st.write(row["usuario"],row["descricao"],row["valor"])
        st.write("Criado:",row["data_criacao"])
        st.write("Pago:",row["data_pagamento"])

        # anexos preview
        if row["arquivos"]:
            for arq in row["arquivos"].split(","):
                if arq.endswith((".png",".jpg",".jpeg")):
                    st.image(arq,width=200)
                elif arq.endswith(".pdf"):
                    with open(arq,"rb") as f:
                        st.download_button("PDF",f,file_name=arq,key=f"pdf_admin_{row['id']}")

        if st.button("Pagar",key=f"pay_{row['id']}"):

            user_data=conn.execute("SELECT nome,email FROM usuarios WHERE usuario=?",
                                   (row["usuario"],)).fetchone()

            if user_data:
                enviar_email(user_data[1],user_data[0],
                             row["descricao"],row["valor"],row["categoria"])

            conn.execute("UPDATE despesas SET status='PAGO',data_pagamento=? WHERE id=?",
                         (datetime.now(),row["id"]))
            conn.commit()
            st.success("Pago!")

        st.markdown('</div>',unsafe_allow_html=True)

    conn.close()