from fastapi import Depends, status, HTTPException, APIRouter
from app import oauth2
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/broker", tags=["Broker"])


@router.post(
    "/",
    response_model=schemas.BrokerOut,
    status_code=status.HTTP_201_CREATED,
)
def create_broker(
    broker: schemas.BrokerCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can create brokers"
        )
    new_broker = models.Broker(**broker.model_dump())
    db.add(new_broker)
    db.commit()
    db.refresh(new_broker)
    return new_broker


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
)
def get_all_brokers(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    brokers = db.query(models.Broker).all()
    return brokers


@router.get(
    "/{id}",
    response_model=schemas.BrokerOut,
)
def get_broker(
    id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    broker = db.query(models.Broker).filter(models.Broker.id == id).first()
    if not broker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Broker not found"
        )

    return broker
