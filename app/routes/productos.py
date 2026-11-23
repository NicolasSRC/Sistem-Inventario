from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required

from .. import db
from ..models import Producto, Categoria, Proveedor
from ..services.inventario import InventarioError, registrar_entrada
from ..utils import admin_required

bp = Blueprint("productos", __name__, url_prefix="/productos")


def _proveedores_form():
    return Proveedor.query.order_by(Proveedor.activo.desc(), Proveedor.nombre).all()


def _filtrar():
    q = request.args.get("q", "").strip()
    cat = request.args.get("categoria", type=int)
    prov = request.args.get("proveedor", type=int)
    estado = request.args.get("estado", "activos")
    if not current_user.es_admin:
        estado = "activos"

    query = Producto.query
    if estado == "activos":
        query = query.filter(Producto.activo.is_(True))
    elif estado == "inactivos":
        query = query.filter(Producto.activo.is_(False))
    if q:
        like = "%" + q + "%"
        query = query.filter(db.or_(
            Producto.nombre.ilike(like),
            Producto.sku.ilike(like),
            Producto.codigo_barras.ilike(like),
        ))
    if cat:
        query = query.filter_by(categoria_id=cat)
    if prov:
        query = query.filter_by(proveedor_id=prov)
    return query.order_by(Producto.nombre).all(), q, cat, prov, estado


@bp.route("/")
@login_required
def lista():
    items, q, cat, prov, estado = _filtrar()
    return render_template(
        "productos/lista.html",
        productos=items,
        q=q,
        cat=cat,
        prov=prov,
        estado=estado,
        categorias=Categoria.query.order_by(Categoria.nombre).all(),
        proveedores=Proveedor.query.filter_by(activo=True).order_by(Proveedor.nombre).all(),
    )


@bp.route("/alertas")
@admin_required
def alertas():
    items = Producto.query.filter(
        Producto.activo.is_(True),
        Producto.cantidad <= Producto.stock_minimo,
    ).order_by(Producto.cantidad).all()
    return render_template("productos/alertas.html", productos=items)


def _guardar(p):
    es_nuevo = p.id is None
    f = request.form
    try:
        nombre = f["nombre"].strip()
        precio = float(f["precio"])
        stock_inicial = int(f.get("cantidad") or 0)
        minimo = int(f.get("stock_minimo") or 5)
        precio_compra = float(f.get("precio_compra") or 0)
        dias_alerta = int(f.get("dias_alerta_vencimiento") or 15)
        if (not nombre or precio < 0 or stock_inicial < 0 or minimo < 0
                or precio_compra < 0 or dias_alerta < 0):
            raise ValueError
    except (ValueError, KeyError):
        flash("Datos inválidos: revise nombre, precios y cantidades.", "danger")
        return False

    proveedor = None
    proveedor_id = f.get("proveedor_id")
    if proveedor_id:
        try:
            proveedor = db.session.get(Proveedor, int(proveedor_id))
        except (TypeError, ValueError):
            proveedor = None
        if not proveedor:
            flash("El proveedor seleccionado no existe.", "danger")
            return False

    sku = f.get("sku", "").strip() or None
    if sku:
        otro = Producto.query.filter_by(sku=sku).first()
        if otro and otro.id != p.id:
            flash("Ya existe un producto con ese SKU.", "danger")
            return False

    codigo_barras = f.get("codigo_barras", "").strip() or None
    if codigo_barras:
        otro = Producto.query.filter_by(codigo_barras=codigo_barras).first()
        if otro and otro.id != p.id:
            flash("Ya existe un producto con ese código de barras.", "danger")
            return False

    p.nombre, p.descripcion, p.sku = nombre, f.get("descripcion", "").strip(), sku
    p.codigo_barras = codigo_barras
    p.precio = precio
    p.stock_minimo = minimo
    p.dias_alerta_vencimiento = dias_alerta
    p.proveedor_id = proveedor.id if proveedor else None
    p.categoria_id = int(f["categoria_id"]) if f.get("categoria_id") else None

    if es_nuevo:
        p.precio_compra = precio_compra
        p.cantidad = 0
        p.activo = True

    db.session.add(p)
    try:
        db.session.flush()
        if es_nuevo and stock_inicial > 0:
            registrar_entrada(
                p,
                stock_inicial,
                costo_unitario=precio_compra,
                proveedor=proveedor,
                actualizar_costo=False,
                motivo="inventario_inicial",
                observacion="Stock inicial",
                usuario=current_user,
            )
        else:
            db.session.commit()
    except InventarioError as e:
        db.session.rollback()
        flash(str(e), "danger")
        return False
    return True


@bp.route("/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo():
    if request.method == "POST" and _guardar(Producto()):
        flash("Producto registrado correctamente.", "success")
        return redirect(url_for("productos.lista"))
    return render_template("productos/form.html", p=None,
                           categorias=Categoria.query.all(), proveedores=_proveedores_form())


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar(id):
    p = db.get_or_404(Producto, id)
    if request.method == "POST" and _guardar(p):
        flash("Producto actualizado.", "success")
        return redirect(url_for("productos.lista"))
    return render_template("productos/form.html", p=p,
                           categorias=Categoria.query.all(), proveedores=_proveedores_form())


@bp.route("/<int:id>/estado", methods=["POST"])
@admin_required
def cambiar_estado(id):
    p = db.get_or_404(Producto, id)
    p.activo = not p.activo
    db.session.commit()
    if p.activo:
        flash("Producto «%s» activado." % p.nombre, "success")
    else:
        flash("Producto «%s» desactivado. Su historial se conserva." % p.nombre, "warning")
    return redirect(url_for("productos.lista"))
