from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, Query # Query might be needed if error_message was a Query param, but it's a path param here. No, it's a query param.
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse # Import HTMLResponse
from typing import Optional # Import Optional

from app.api.endpoints import resellers as resellers_api
from app.api.endpoints import auth as auth_api
from app.api.endpoints import products as products_api
from app.api.endpoints import orders as orders_api
import datetime # For current_year in base.html context example

app = FastAPI(title="RoamStop API", version="0.1.0")

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="frontend/templates")

# Include API routers
app.include_router(auth_api.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(resellers_api.router, prefix="/api/v1/resellers", tags=["Resellers"])
app.include_router(products_api.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(orders_api.router, prefix="/api/v1/orders", tags=["Orders"])

@app.get("/ping", tags=["Health Check"])
async def ping():
    return {"message": "pong"}

# Simple test endpoint for rendering index.html
@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def read_root(request: Request):
    # Example of adding current_year to context for base.html
    # In a real app, this might be part of a global context processor
    return templates.TemplateResponse("index.html", {
        "request": request,
        "message": "Welcome to Roamstop!",
        "current_year": datetime.datetime.utcnow().year
    })

@app.get("/checkout", response_class=HTMLResponse, tags=["Frontend"])
async def route_checkout(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request, "current_year": datetime.datetime.utcnow().year})

@app.get("/order-success", response_class=HTMLResponse, tags=["Frontend"])
async def route_order_success(request: Request):
    return templates.TemplateResponse("order_success.html", {"request": request, "current_year": datetime.datetime.utcnow().year})

@app.get("/order-error", response_class=HTMLResponse, tags=["Frontend"])
async def route_order_error(request: Request, error_message: Optional[str] = None): # Added Optional import
    return templates.TemplateResponse("order_error.html", {"request": request, "error_message": error_message, "current_year": datetime.datetime.utcnow().year})

# Test route for products_display.html - can be removed later
@app.get("/products-display-test", response_class=HTMLResponse, tags=["Frontend"])
async def route_products_display_test(request: Request):
    sample_products = [
        {"id": 1, "name": "Test Product 1", "description": "Desc 1", "duration_days": 7, "price": 10.00},
        {"id": 2, "name": "Test Product 2", "description": "Desc 2", "duration_days": 30, "price": 30.00},
    ]
    return templates.TemplateResponse("products_display.html", {"request": request, "products": sample_products, "country_code_display": "Test Country", "current_year": datetime.datetime.utcnow().year})

@app.get("/reseller/login", response_class=HTMLResponse, tags=["Frontend"])
async def route_reseller_login(request: Request):
    return templates.TemplateResponse("reseller_login.html", {"request": request, "current_year": datetime.datetime.utcnow().year})

@app.get("/reseller/dashboard", response_class=HTMLResponse, tags=["Frontend"])
async def route_reseller_dashboard(request: Request):
    return templates.TemplateResponse("reseller_dashboard.html", {"request": request, "current_year": datetime.datetime.utcnow().year})
