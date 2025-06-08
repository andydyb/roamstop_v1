from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.crud import crud_reseller
from app.core.config import SECRET_KEY, ALGORITHM
from app.schemas.token import TokenData
from app.models.reseller import ResellerProfile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False) # Set auto_error=False

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db) # token can be None
) -> Optional[ResellerProfile]: # Return type can be None
    if token is None: # If no token provided (due to auto_error=False), user is not authenticated
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            # This case should ideally not be reached if token is valid and contains "sub"
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError: # Catches any error during decoding (expired, invalid signature, etc.)
        raise credentials_exception

    user = crud_reseller.get_reseller_by_email(db, email=token_data.email)
    if user is None:
        # This means the user ID in a valid token does not exist in DB.
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Optional[ResellerProfile] = Depends(get_current_user),
) -> ResellerProfile: # This should still return ResellerProfile or raise
    if not current_user: # If get_current_user returned None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, # Or 403 if preferred for "not active" vs "not authenticated"
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: ResellerProfile = Depends(get_current_active_user), # Changed dependency
) -> ResellerProfile:
    # get_current_active_user already ensures current_user is not None and is active.
    # So, we just need to check for superuser status.
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
