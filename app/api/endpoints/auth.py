from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm # No longer need to import if using the one from dependencies
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm # Keep this for form_data

from app.core.dependencies import oauth2_scheme # Import centralized scheme
from app.db.session import get_db
from app.crud import crud_reseller
from app.core.security import verify_password, create_access_token
from app.schemas.token import Token
# from app.models.reseller import ResellerProfile # For type hinting if needed

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), # form_data still uses this
    db: Session = Depends(get_db)
    # token: str = Depends(oauth2_scheme) # Not needed for login itself, but for protected endpoints
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    print(f"[AUTH ENDPOINT] Login attempt for username: {form_data.username}") # Debug print
    user = crud_reseller.get_reseller_by_email(db, email=form_data.username)

    if not user:
        print(f"[AUTH ENDPOINT] User not found: {form_data.username}") # Debug print
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.hashed_password:
        print(f"[AUTH ENDPOINT] User {form_data.username} has no hashed password.") # Debug print
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password", # Keep generic for security
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_password_correct = verify_password(form_data.password, user.hashed_password)
    print(f"[AUTH ENDPOINT] Verification for {form_data.username} (DB hash: {user.hashed_password}): {is_password_correct}") # Debug print

    if not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email} # "sub" is a standard claim for the subject (user identifier)
    )
    return {"access_token": access_token, "token_type": "bearer"}
