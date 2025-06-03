from fastapi import FastAPI
from fastapi import FastAPI
from app.api.endpoints import resellers as resellers_api
from app.api.endpoints import auth as auth_api
from app.api.endpoints import products as products_api
from app.api.endpoints import orders as orders_api

app = FastAPI(title="RoamStop API", version="0.1.0")

# Include routers
app.include_router(auth_api.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(resellers_api.router, prefix="/api/v1/resellers", tags=["Resellers"])
app.include_router(products_api.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(orders_api.router, prefix="/api/v1/orders", tags=["Orders"])

@app.get("/ping", tags=["Health Check"])
async def ping():
    return {"message": "pong"}
