import re
from datetime import datetime, timedelta

from app import db
from app.models import Movimiento, Producto, Proveedor
from app.services.rotacion import obtener_rotacion


def _proveedor(app, nombre="Distribuidora Central", lead=5):
    with app.app_context():
        proveedor = Proveedor(
            nombre=nombre,
            lead_time_dias=lead,
            email="compras@central.co",
            telefono="3001234567",
        )
        db.session.add(proveedor)
        db.session.commit()
        return proveedor.id


def _producto(app, nombre, sku, cantidad=10, stock_minimo=5, proveedor_id=None):
    with app.app_context():
        producto = Producto(
            nombre=nombre,
            sku=sku,
            precio=1000,
            precio_compra=600,
            cantidad=cantidad,
            stock_minimo=stock_minimo,
            proveedor_id=proveedor_id,
            activo=True,
        )
        db.session.add(producto)
        db.session.commit()
        return producto.id


def _salida(app, producto_id, cantidad, dias_atras=0):
    with app.app_context():
        movimiento = Movimiento(
            producto_id=producto_id,
            tipo="salida",
            motivo="venta",
            cantidad=cantidad,
            delta=-cantidad,
            fecha=datetime.now() - timedelta(days=dias_atras),
        )
        db.session.add(movimiento)
        db.session.commit()


def _fila(html, nombre):
    """Devuelve el HTML de la fila de la tabla que contiene el producto."""
    for fila in re.findall(r"<tr.*?</tr>", html, re.S):
        if nombre in fila:
            return fila
    return ""


def test_reporte_de_rotacion_disponible_para_tendero(admin_client):
    respuesta = admin_client.get("/reportes/rotacion")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)
    assert "Rotación y sugerencia de pedidos" in html
    assert "Exportar CSV" in html
    assert "Productos con rotación" in html
    assert "Requieren reposición" in html
    assert "Unidades sugeridas" in html


def test_cajero_no_accede_al_reporte_de_rotacion(cajero_client):
    html = cajero_client.get("/reportes/rotacion", follow_redirects=True).get_data(as_text=True)
    assert "Acción permitida solo para administradores" in html


def test_calcula_rotacion_y_pedido_sugerido(app):
    proveedor_id = _proveedor(app, lead=5)
    producto_id = _producto(app, "Arroz premium", "ROT-001", cantidad=10,
                            stock_minimo=5, proveedor_id=proveedor_id)
    _salida(app, producto_id, 30)

    with app.app_context():
        resultado = obtener_rotacion(periodo=30)
        fila = next(f for f in resultado["filas"] if f["producto"].nombre == "Arroz premium")

    assert fila["unidades"] == 30
    assert fila["frecuencia"] == 1
    assert fila["venta_diaria"] == 1.0
    assert fila["dias_inventario"] == 10.0
    assert fila["rotacion"] == "alta"
    assert fila["lead_time"] == 5
    assert fila["stock_seguridad"] == 7
    assert fila["consumo_entrega"] == 5
    assert fila["punto_pedido"] == 12
    assert fila["sugerido"] == 2
    assert fila["reponer"] is True


def test_producto_sin_ventas_se_marca_sin_rotacion(admin_client, app):
    _producto(app, "Linterna", "ROT-002", cantidad=20, stock_minimo=5)

    html = admin_client.get("/reportes/rotacion").get_data(as_text=True)
    fila = _fila(html, "Linterna")
    assert fila
    assert "Sin rotación" in fila
    assert "Sin proveedor" in fila


def test_filtro_solo_reponer(admin_client, app):
    proveedor_id = _proveedor(app, lead=5)
    con_pedido = _producto(app, "Café molido", "ROT-010", cantidad=10,
                           stock_minimo=5, proveedor_id=proveedor_id)
    sin_pedido = _producto(app, "Sal fina", "ROT-011", cantidad=100, stock_minimo=5)
    _salida(app, con_pedido, 30)

    html = admin_client.get("/reportes/rotacion?solo_reponer=1").get_data(as_text=True)
    assert "Café molido" in html
    assert "Sal fina" not in html
    assert sin_pedido  # el producto sin pedido existe en la base


def test_periodo_afecta_el_calculo(app):
    producto_id = _producto(app, "Atún", "ROT-020", cantidad=10, stock_minimo=2)
    _salida(app, producto_id, 5, dias_atras=40)

    with app.app_context():
        corto = obtener_rotacion(periodo=30)
        largo = obtener_rotacion(periodo=90)

    fila_corta = next(f for f in corto["filas"] if f["producto"].nombre == "Atún")
    fila_larga = next(f for f in largo["filas"] if f["producto"].nombre == "Atún")
    assert fila_corta["unidades"] == 0
    assert fila_larga["unidades"] == 5


def test_csv_de_rotacion_incluye_sugerencias(admin_client, app):
    proveedor_id = _proveedor(app, lead=5)
    producto_id = _producto(app, "Aceite girasol", "ROT-030", cantidad=10,
                            stock_minimo=5, proveedor_id=proveedor_id)
    _salida(app, producto_id, 30)

    respuesta = admin_client.get("/reportes/rotacion.csv")
    assert respuesta.status_code == 200
    assert respuesta.mimetype == "text/csv"
    contenido = respuesta.get_data(as_text=True)
    assert contenido.startswith("\ufeff")
    assert "Cantidad sugerida" in contenido
    assert "Aceite girasol" in contenido
    linea = next(l for l in contenido.splitlines() if "Aceite girasol" in l)
    assert "Distribuidora Central" in linea
    assert linea.rstrip("\r").endswith(",2")


def test_orden_menor_rotacion_prioriza_productos_sin_ventas(app):
    proveedor_id = _proveedor(app, lead=3)
    con_ventas = _producto(app, "Pan tajado", "ROT-040", cantidad=10,
                           stock_minimo=3, proveedor_id=proveedor_id)
    sin_ventas = _producto(app, "Avena", "ROT-041", cantidad=10, stock_minimo=3)
    _salida(app, con_ventas, 12)

    with app.app_context():
        mayor = obtener_rotacion(periodo=30, orden="mayor")
        menor = obtener_rotacion(periodo=30, orden="menor")

    assert mayor["filas"][0]["producto"].nombre == "Pan tajado"
    assert menor["filas"][0]["producto"].nombre == "Avena"
    assert menor["resumen"]["mostrados"] == 2
    assert sin_ventas
