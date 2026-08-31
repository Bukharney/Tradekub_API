from fastapi import Depends, status, HTTPException, APIRouter
from app import oauth2, utils
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session


router = APIRouter(prefix="/turnover", tags=["Turnover"])


@router.get(
    "/",
)
def get_turnover(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    turnover = (
        db.query(models.Turnover)
        .order_by(models.Turnover.timestamp.desc())
        .first()
    )
    if not turnover:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Turnover not found"
        )

    return turnover


@router.get(
    "/all",
)
def get_all_turnovers(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    turnovers = db.query(models.Turnover).all()
    if not turnovers:
        return []

    return turnovers


@router.get("/api")
def get_quote(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to access this resource",
        )
    return utils.get_quote(db)


@router.get(
    "/{symbol}",
)
def get_turnover_symbol(
    symbol: str,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    turnover = (
        db.query(models.Turnover)
        .filter(models.Turnover.symbol == symbol.upper())
        .first()
    )
    if not turnover:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Turnover not found"
        )

    return turnover
