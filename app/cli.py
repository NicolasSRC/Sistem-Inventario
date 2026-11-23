"""Comandos de línea de comandos para inicializar y poblar la base de datos."""
import click
from flask.cli import with_appcontext
from flask_migrate import upgrade

from . import db

USUARIOS_BASE = [
    ("admin", "admin123", "tendero"),
    ("cliente", "cliente123", "cajero"),
]
CATEGORIAS_BASE = ("General", "Electrónica", "Papelería", "Hogar")
SUCURSAL_BASE = "Principal"


def sembrar_base():
    """Crea la sucursal, los usuarios y las categorías mínimas (idempotente)."""
    from .models import Categoria, Sucursal, Usuario

    sucursal = Sucursal.query.filter_by(nombre=SUCURSAL_BASE).first()
    if not sucursal:
        sucursal = Sucursal(nombre=SUCURSAL_BASE)
        db.session.add(sucursal)

    for username, password, rol in USUARIOS_BASE:
        if not Usuario.query.filter_by(username=username).first():
            usuario = Usuario(username=username, rol=rol, sucursal=sucursal)
            usuario.set_password(password)
            db.session.add(usuario)

    for usuario in Usuario.query.filter_by(sucursal_id=None).all():
        usuario.sucursal = sucursal

    for nombre in CATEGORIAS_BASE:
        if not Categoria.query.filter_by(nombre=nombre).first():
            db.session.add(Categoria(nombre=nombre))

    db.session.commit()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Aplica las migraciones y carga los datos mínimos."""
    upgrade()
    sembrar_base()
    click.echo("Base de datos inicializada (sucursal, usuarios y categorías base).")


@click.command("seed-base")
@with_appcontext
def seed_base_command():
    """Carga solo los datos mínimos sin ejecutar migraciones."""
    sembrar_base()
    click.echo("Datos base cargados.")
