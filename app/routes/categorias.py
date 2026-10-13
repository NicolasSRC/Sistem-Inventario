from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import db
from ..models import Categoria
from ..utils import admin_required

bp = Blueprint("categorias", __name__, url_prefix="/categorias")


@bp.route("/", methods=["GET", "POST"])
@admin_required
def lista():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
        elif Categoria.query.filter(db.func.lower(Categoria.nombre) == nombre.lower()).first():
            flash("La categoría ya existe.", "danger")
        else:
            db.session.add(Categoria(nombre=nombre[:50]))
            db.session.commit()
            flash("Categoría creada.", "success")
        return redirect(url_for("categorias.lista"))
    return render_template("categorias/lista.html", categorias=Categoria.query.order_by(Categoria.nombre).all())


@bp.route("/<int:id>/editar", methods=["POST"])
@admin_required
def editar(id):
    c = db.get_or_404(Categoria, id)
    nombre = request.form.get("nombre", "").strip()
    dup = Categoria.query.filter(Categoria.nombre == nombre, Categoria.id != id).first()
    if not nombre or dup:
        flash("Nombre vacío o repetido.", "danger")
    else:
        c.nombre = nombre[:50]
        db.session.commit()
        flash("Categoría actualizada.", "success")
    return redirect(url_for("categorias.lista"))


@bp.route("/<int:id>/eliminar", methods=["POST"])
@admin_required
def eliminar(id):
    c = db.get_or_404(Categoria, id)
    if c.productos:
        flash("No se puede eliminar: la categoría tiene productos asociados.", "danger")
    else:
        db.session.delete(c)
        db.session.commit()
        flash("Categoría eliminada.", "success")
    return redirect(url_for("categorias.lista"))
