from datetime import timedelta
from fastapi import APIRouter, Depends, status, HTTPException, Response, Request
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import database, schemas, models, utils, oauth2

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=schemas.Token)
def login(
    request: Request,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.email == user_credentials.username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not utils.verify(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials"
        )

    access_token = oauth2.create_access_token(data={"user_id": user.id})

    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("user-agent", "unknown")

    login_record = models.Login_Logout(
        user_id=user.id,
        logout=utils.get_current_time()
        + timedelta(minutes=oauth2.ACCESS_TOKEN_EXPIRE_MINUTES),
        device=user_agent,
        ip=client_ip,
    )

    db.add(login_record)
    db.commit()
    db.refresh(login_record)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    logout_record = (
        db.query(models.Login_Logout)
        .filter(models.Login_Logout.user_id == current_user.id)
        .order_by(models.Login_Logout.id.desc())
        .first()
    )

    if logout_record and logout_record.logout:
        now_naive = utils.get_current_time().replace(tzinfo=None)
        rec_logout_naive = (
            logout_record.logout.replace(tzinfo=None)
            if logout_record.logout.tzinfo
            else logout_record.logout
        )

        if now_naive < rec_logout_naive:
            logout_record.logout = utils.get_current_time()
            db.add(logout_record)
            db.commit()
            db.refresh(logout_record)
            response.status_code = status.HTTP_200_OK
            return {"message": "User logged out successfully"}

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User already logged out",
    )


@router.get("/reset", status_code=status.HTTP_200_OK)
def reset_db(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can reset database",
        )

    admin_info = {
        "id": current_user.id,
        "name": current_user.name,
        "phone": current_user.phone,
        "email": current_user.email,
        "password": current_user.password,
        "role": current_user.role,
    }

    tables = [
        "login_logout",
        "transactions",
        "orders",
        "bank_tsc",
        "dividend",
        "portfolio",
        "notification",
        "turnover",
        "accounts",
        "stocks",
        "brokers",
        "users",
        "news",
        "alembic_version",
    ]
    for table in tables:
        try:
            db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        except Exception:
            db.execute(text(f"DROP TABLE IF EXISTS {table};"))

    db.commit()

    # Re-create schema
    models.Base.metadata.create_all(bind=db.get_bind())

    # Re-insert admin user so active admin session remains valid
    recreated_admin = models.User(**admin_info)
    db.add(recreated_admin)
    db.commit()

    return {"message": "Database reset executed successfully"}
