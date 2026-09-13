import os
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, url_for

from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user
)

from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

login_manager = LoginManager(app)
login_manager.login_view = "login" # type: ignore
login_manager.login_message = "Faça login para acessar o sistema."
login_manager.login_message_category = "warning"


# --------- Usuário (Para o Flask-Login) --------- #

class Usuario(UserMixin):
    def __init__(self, id, nome, usuario, senha_hash, perfil, ativo):
        self.id = id
        self.nome = nome
        self.usuario = usuario
        self.senha_hash = senha_hash
        self.perfil = perfil
        self.ativo = ativo

    @property
    def is_active(self): # type: ignore[override]
        return bool(self.ativo)

    @property
    def is_authenticated(self): # type: ignore[override]
        return bool(self.ativo)

    @property
    def is_admin(self):
        return self.perfil == "admin"


def buscar_usuario_por_id(usuario_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, usario, senha_hash, perfil, ativo "
                "FROM usuarios WHERE id = %s",
                (usuario_id)
            
            )
            return cursor.fetchone()
    finally:
        conn.close()


@login_manager.user_loader
def carregar_usuario(usuario_id):
    linha = buscar_usuario_por_id(usuario_id)
    return Usuario(**linha) if linha else None