import uvicorn

from app.main import app


def main() -> None:
    from app.config import get_settings

    s = get_settings()
    uvicorn.run(
        app,
        host=s.server_host,
        port=int(s.server_port),
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()