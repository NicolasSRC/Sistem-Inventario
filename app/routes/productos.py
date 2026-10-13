from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .. import db
from ..models import Producto, Categoria
from ..utils import admin_required

bp = Blueprint("productos", __name__, url_prefix="/productos")


def _filtrar():
    q = request.args.get("q", "").strip()
    cat = request.args.get("categoria", type=int)
    query = Producto.query
    if q:
        like = "%" + q + "%"
        query = query.filter(db.or_(Producto.nombre.ilike(like), Producto.sku.ilike(like)))
    if cat:
        query = query.filter_by(categoria_id=cat)
    return query.order_by(Producto.nombre).all(), q, cat


@bp.route("/")
@login_required
def lista():
    items, q, cat = _filtrar()
    return render_template("productos/lista.html", productos=items, q=q, cat=cat,
                           categorias=Categoria.query.order_by(Categoria.nombre).all())


@bp.route("/alertas")
@admin_required
def alertas():
    items = Producto.query.filter(Producto.cantidad <= Producto.stock_minimo).order_by(Producto.cantidad).all()
    return render_template("productos/alertas.html", productos=items)


def _guardar(p):
    f = request.form
    try:
        nombre = f["nombre"].strip()
        precio = float(f["precio"])
        cantidad = int(f.get("cantidad") or 0)
        minimo = int(f.get("stock_minimo") or 5)
        if not nombre or precio < 0 or cantidad < 0 or minimo < 0:
            raise ValueError
    except (ValueError, KeyError):
        flash("Datos inválidos: revise nombre, precio y cantidades.", "danger")
        return False
    sku = f.get("sku", "").strip() or None
    if sku:
        otro = Producto.query.filter_by(sku=sku).first()
        if otro and otro.id != p.id:
            flash("Ya existe un producto con ese SKU.", "danger")
            return False
    p.nombre, p.descripcion, p.sku = nombre, f.get("descripcion", "").strip(), sku
    p.precio, p.cantidad, p.stock_minimo = precio, cantidad, minimo
    p.categoria_id = int(f["categoria_id"]) if f.get("categoria_id") else None
    db.session.add(p)
    db.session.commit()
    return True


@bp.route("/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo():
    if request.method == "POST" and _guardar(Producto()):
        flash("Producto registrado correctamente.", "success")
        return redirect(url_for("productos.lista"))
    return render_template("productos/form.html", p=None, categorias=Categoria.query.all())


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar(id):
    p = db.get_or_404(Producto, id)
    if request.method == "POST" and _guardar(p):
        flash("Producto actualizado.", "success")
        return redirect(url_for("productos.lista"))
    return render_template("productos/form.html", p=p, categorias=Categoria.query.all())


@bp.route("/<int:id>/eliminar", methods=["POST"])
@admin_required
def eliminar(id):
    p = db.get_or_404(Producto, id)
    db.session.delete(p)
    db.session.commit()
    flash("Producto eliminado.", "success")
    return redirect(url_for("productos.lista"))
