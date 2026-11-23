from app import db
from app.models import Categoria, Producto, Proveedor

DATOS_PROVEEDOR = {
    "nombre": "Distribuidora Norte",
    "nit": "900999888-1",
    "contacto": "Camila Rojas",
    "telefono": "3009998877",
    "email": "compras@distrinorte.co",
    "direccion": "Bogotá",
    "lead_time_dias": "4",
}


def _crear_proveedor(client, **cambios):
    datos = dict(DATOS_PROVEEDOR)
    datos.update(cambios)
    return client.post("/proveedores/nuevo", data=datos, follow_redirects=True)


def test_lista_proveedores_vacia(admin_client):
    respuesta = admin_client.get("/proveedores/")
    assert respuesta.status_code == 200
    assert "No se encontraron proveedores" in respuesta.get_data(as_text=True)


def test_crear_editar_y_cambiar_estado(admin_client):
    respuesta = _crear_proveedor(admin_client)
    assert "Proveedor registrado correctamente" in respuesta.get_data(as_text=True)

    proveedor = Proveedor.query.filter_by(nombre="Distribuidora Norte").first()
    assert proveedor is not None
    assert proveedor.lead_time_dias == 4
    assert proveedor.activo is True

    respuesta = admin_client.post(
        f"/proveedores/{proveedor.id}/editar",
        data={**DATOS_PROVEEDOR, "nombre": "Distribuidora Norte SAS", "lead_time_dias": "7"},
        follow_redirects=True,
    )
    assert "Proveedor actualizado" in respuesta.get_data(as_text=True)
    assert proveedor.nombre == "Distribuidora Norte SAS"
    assert proveedor.lead_time_dias == 7

    respuesta = admin_client.post(
        f"/proveedores/{proveedor.id}/estado", follow_redirects=True
    )
    assert "desactivado" in respuesta.get_data(as_text=True)
    assert proveedor.activo is False

    respuesta = admin_client.post(
        f"/proveedores/{proveedor.id}/estado", follow_redirects=True
    )
    assert "activado" in respuesta.get_data(as_text=True)
    assert proveedor.activo is True


def test_nombre_duplicado_y_correo_invalido(admin_client):
    _crear_proveedor(admin_client)

    respuesta = _crear_proveedor(admin_client, nombre="distribuidora norte")
    assert "Ya existe un proveedor con ese nombre" in respuesta.get_data(as_text=True)

    respuesta = _crear_proveedor(admin_client, nombre="Otro proveedor", email="correo-sin-dominio")
    assert "correo electrónico no es válido" in respuesta.get_data(as_text=True)
    assert Proveedor.query.filter_by(nombre="Otro proveedor").first() is None


def test_cajero_no_accede_a_proveedores(cajero_client):
    respuesta = cajero_client.get("/proveedores/", follow_redirects=True)
    assert respuesta.status_code == 200
    assert "Acción permitida solo para administradores" in respuesta.get_data(as_text=True)


def test_producto_asociado_a_proveedor_y_filtro(admin_client):
    _crear_proveedor(admin_client)
    proveedor = Proveedor.query.filter_by(nombre="Distribuidora Norte").first()
    categoria = Categoria.query.first()

    respuesta = admin_client.post(
        "/productos/nuevo",
        data={
            "nombre": "Producto Con Proveedor",
            "sku": "PROV-001",
            "precio": "15000",
            "cantidad": "5",
            "stock_minimo": "2",
            "categoria_id": str(categoria.id),
            "proveedor_id": str(proveedor.id),
        },
        follow_redirects=True,
    )
    assert "Producto registrado correctamente" in respuesta.get_data(as_text=True)

    producto = Producto.query.filter_by(sku="PROV-001").first()
    assert producto is not None
    assert producto.proveedor_id == proveedor.id

    admin_client.post(
        "/productos/nuevo",
        data={
            "nombre": "Producto Sin Proveedor",
            "sku": "PROV-002",
            "precio": "9000",
            "cantidad": "2",
            "stock_minimo": "1",
            "categoria_id": str(categoria.id),
        },
        follow_redirects=True,
    )

    respuesta = admin_client.get(f"/productos/?proveedor={proveedor.id}")
    assert "Producto Con Proveedor" in respuesta.get_data(as_text=True)
    assert "Producto Sin Proveedor" not in respuesta.get_data(as_text=True)


def test_reporte_productos_incluye_proveedor(admin_client):
    _crear_proveedor(admin_client)
    proveedor = Proveedor.query.filter_by(nombre="Distribuidora Norte").first()
    producto = Producto(
        nombre="Producto Reporte",
        sku="REP-001",
        precio=10000,
        precio_compra=7000,
        cantidad=3,
        proveedor=proveedor,
    )
    db.session.add(producto)
    db.session.commit()

    respuesta = admin_client.get("/reportes/productos.csv")
    assert respuesta.status_code == 200
    assert "Distribuidora Norte" in respuesta.get_data(as_text=True)
