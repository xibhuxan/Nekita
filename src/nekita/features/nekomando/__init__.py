"""Feature `nekomando`: respuestas fijas a frases de texto libre."""

from nekita.core.context import AppContext
from nekita.core.feature import Feature
from nekita.features.nekomando import service
from nekita.features.nekomando.router import build_router


def build() -> Feature:
    """Carga los datos por defecto; los overrides se aplican en `on_startup` (necesita la BD)."""
    nekomandos = service.Nekomandos(service.load_defaults())

    async def on_startup(ctx: AppContext) -> None:
        await service.import_legacy_file(ctx.db, ctx.settings.data_path)
        rechazados = nekomandos.apply_overrides(await service.load_db_overrides(ctx.db))
        if rechazados:
            service.log.warning("Overrides de nekomandos rechazados: %s", ", ".join(rechazados))

    return Feature(
        name="nekomando",
        router=build_router(nekomandos),
        help_lines=nekomandos.help_lines(),
        on_startup=on_startup,
    )
