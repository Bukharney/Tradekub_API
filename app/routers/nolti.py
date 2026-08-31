from typing import List, Optional
from fastapi import Depends, status, HTTPException, APIRouter
from app import oauth2
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/noti", tags=["Notification"])


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
)
def get_all_notification(
    current_user: Optional[models.User] = Depends(oauth2.get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return []

    if current_user.role == "admin":
        noti = (
            db.query(models.Notifications)
            .order_by(models.Notifications.created_at.desc())
            .all()
        )
    else:
        user_account_ids = [
            acc.id
            for acc in db
            .query(models.Accounts)
            .filter(models.Accounts.user_id == current_user.id)
            .all()
        ]
        if not user_account_ids:
            return []
        noti = (
            db.query(models.Notifications)
            .filter(models.Notifications.account_id.in_(user_account_ids))
            .order_by(models.Notifications.created_at.desc())
            .all()
        )

    return noti


@router.get(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.NotiOut],
)
def get_notification(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == account_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    if account.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    noti = (
        db.query(models.Notifications)
        .filter(models.Notifications.account_id == account_id)
        .order_by(models.Notifications.created_at.desc())
        .all()
    )

    return noti


@router.delete(
    "/{noti_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@router.get(
    "/delete/{noti_id}",
    status_code=status.HTTP_200_OK,
)
def delete_notification(
    noti_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    noti = (
        db.query(models.Notifications)
        .filter(models.Notifications.id == noti_id)
        .first()
    )
    if not noti:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == noti.account_id)
        .first()
    )
    if account and account.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    db.delete(noti)
    db.commit()
    return None
