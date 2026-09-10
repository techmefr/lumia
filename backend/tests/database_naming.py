from sqlalchemy.engine import make_url


def run_database_url(base_url: str, *, worker: str | None, pid: int) -> str:
    """Gives this pytest run a database of its own, derived from the one configured.

    Two runs sharing a database wipe each other's schema mid-test: `create_all` and `drop_all`
    race, and the loser fails on `pg_type_typname_nsp_index` with errors that look like a
    regression of the branch under test. The xdist worker id comes first so `-n auto` workers get
    one database each; the pid separates two runs started side by side.
    """
    url = make_url(base_url)
    suffix = worker if worker else f"p{pid}"
    return url.set(database=f"{url.database}_{suffix}").render_as_string(hide_password=False)


def maintenance_url(base_url: str) -> str:
    """A database has to be created from outside itself, so point at the always-present one."""
    return make_url(base_url).set(database="postgres").render_as_string(hide_password=False)
