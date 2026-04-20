from fastapi import FastAPI


app = FastAPI(title="nl2sql")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}
