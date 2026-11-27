from app import db
from app.models import Sucursal, Usuario


def _crear_sucursal(nombre="Sucursal Temporal"):
    existente = Sucursal.query.filter_by(nombre=nombre).first()
    if existente:
        return existente
    sucursal = Sucursal(nombre=nombre)
    db.session.add(sucursal)
    db.session.commit()
    return sucursal


def _crear_usuario(username="operador", password="operador123", rol="cajero", sucursal_id=1):
    usuario = Usuario(username=username, rol=rol, sucursal_id=sucursal_id)
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_panel_administrativo_para_admin(admin_client):
    html = admin_client.get("/admin/").get_data(as_text=True)
    assert "Panel administrativo" in html
    assert "Usuarios registrados" in html


def test_cajero_no_puede_entrar_al_panel(cajero_client):
    respuesta = cajero_client.get("/admin/", follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    assert "Acción permitida solo para administradores." in html
    assert "Panel administrativo" not in html


def test_panel_muestra_resumen_de_sucursales(admin_client):
    html = admin_client.get("/admin/").get_data(as_text=True)
    assert "Sucursales" in html
    assert "Principal" in html
    assert "Productos activos" in html


def test_registrar_usuario_y_poder_iniciar_sesion(admin_client):
    respuesta = admin_client.post(
        "/admin/usuarios/nuevo",
        data={
            "username": "sofia",
            "rol": "cajero",
            "sucursal_id": "1",
            "password": "sofia123",
            "confirmacion": "sofia123",
        },
        follow_redirects=True,
    )
    html = respuesta.get_data(as_text=True)
    assert "Usuario «sofia» registrado correctamente." in html
    assert "sofia" in html
    assert Usuario.query.filter_by(username="sofia").one().sucursal_id == 1

    admin_client.get("/logout")
    respuesta = admin_client.post(
        "/login",
        data={"username": "sofia", "password": "sofia123"},
        follow_redirects=True,
    )
    assert "Dashboard" in respuesta.get_data(as_text=True)


def test_no_permite_usuarios_duplicados(admin_client):
    _crear_usuario(username="Maria")

    respuesta = admin_client.post(
        "/admin/usuarios/nuevo",
        data={
            "username": "maria",
            "rol": "cajero",
            "sucursal_id": "1",
            "password": "maria123",
            "confirmacion": "maria123",
        },
        follow_redirects=True,
    )
    assert "El nombre de usuario ya está en uso." in respuesta.get_data(as_text=True)
    assert Usuario.query.filter(db.func.lower(Usuario.username) == "maria").count() == 1


def test_validacion_de_contrasena_y_sucursal(admin_client):
    respuesta = admin_client.post(
        "/admin/usuarios/nuevo",
        data={
            "username": "carlos",
            "rol": "cajero",
            "sucursal_id": "9999",
            "password": "corta",
            "confirmacion": "otra",
        },
        follow_redirects=True,
    )
    html = respuesta.get_data(as_text=True)
    assert "al menos 6 caracteres" in html
    assert "Las contraseñas no coinciden." in html
    assert "Seleccione una sucursal activa." in html
    assert Usuario.query.filter_by(username="carlos").first() is None


def test_editar_usuario_cambia_rol_sucursal_y_clave(admin_client):
    usuario = _crear_usuario()
    sucursal = _crear_sucursal("Sucursal Centro")

    respuesta = admin_client.post(
        "/admin/usuarios/%d/editar" % usuario.id,
        data={
            "username": "operador",
            "rol": "tendero",
            "sucursal_id": str(sucursal.id),
            "password": "nueva123",
            "confirmacion": "nueva123",
        },
        follow_redirects=True,
    )
    assert "Usuario «operador» actualizado." in respuesta.get_data(as_text=True)

    actualizado = db.session.get(Usuario, usuario.id)
    assert actualizado.rol == "tendero"
    assert actualizado.sucursal_id == sucursal.id
    assert actualizado.check_password("nueva123")


def test_crear_sucursal_y_aparece_en_el_selector(admin_client):
    respuesta = admin_client.post(
        "/admin/sucursales/nueva",
        data={"nombre": "Sucursal Sur", "direccion": "Calle 50 #10-20", "telefono": "3001234567"},
        follow_redirects=True,
    )
    html = respuesta.get_data(as_text=True)
    assert "Sucursal «Sucursal Sur» creada correctamente." in html
    assert Sucursal.query.filter_by(nombre="Sucursal Sur").one().direccion == "Calle 50 #10-20"

    html = admin_client.get("/dashboard").get_data(as_text=True)
    assert "Sucursal Sur" in html


def test_no_permite_nombres_de_sucursal_duplicados(admin_client):
    respuesta = admin_client.post(
        "/admin/sucursales/nueva",
        data={"nombre": "principal"},
        follow_redirects=True,
    )
    assert "Ya existe una sucursal con ese nombre." in respuesta.get_data(as_text=True)
    assert Sucursal.query.filter(db.func.lower(Sucursal.nombre) == "principal").count() == 1


def test_no_desactiva_sucursal_con_datos(admin_client):
    respuesta = admin_client.post("/admin/sucursales/1/estado", follow_redirects=True)
    assert "la sucursal tiene usuarios asignados" in respuesta.get_data(as_text=True)
    assert db.session.get(Sucursal, 1).activa is True


def test_desactiva_sucursal_vacia_y_desaparece_del_selector(admin_client):
    sucursal = _crear_sucursal("Sucursal Vacía")

    respuesta = admin_client.post(
        "/admin/sucursales/%d/estado" % sucursal.id, follow_redirects=True
    )
    assert "Sucursal «Sucursal Vacía» desactivada." in respuesta.get_data(as_text=True)
    assert db.session.get(Sucursal, sucursal.id).activa is False

    html = admin_client.get("/dashboard").get_data(as_text=True)
    assert "Sucursal Vacía" not in html


def test_login_muestra_cuenta_y_sucursal(client):
    html = client.get("/login").get_data(as_text=True)
    assert "norte · norte123" in html
    assert "Cajero · Sucursal Norte" in html
    assert "admin · admin123" in html
