from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario

bp = Blueprint("auth", __name__)


@bp.route("/", methods=["GET", "POST"])
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        u = Usuario.query.filter_by(username=request.form.get("username", "").strip()).first()
        if u and u.check_password(request.form.get("password", "")):
            login_user(u)
            return redirect(url_for("dashboard.index"))
        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))
