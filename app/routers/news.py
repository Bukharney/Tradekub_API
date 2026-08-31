from datetime import datetime
from fastapi import Depends, status, HTTPException, APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session
from newsdataapi import NewsDataApiClient

from app import oauth2, utils
from app.config import settings
from .. import models
from ..database import get_db

router = APIRouter(tags=["news"], prefix="/news")


def get_news_api_client():
    return NewsDataApiClient(apikey=settings.news_data_api_key)


@router.get("/", status_code=status.HTTP_200_OK)
def get_news(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    news = db.query(models.News).order_by(models.News.news_time.desc()).all()
    if not news:
        return []
    return news


@router.get("/update", status_code=status.HTTP_200_OK)
def update_news(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can update news"
        )
    sql = text("DELETE FROM news;")
    db.execute(sql)
    db.commit()

    api = get_news_api_client()
    categories = ["business", "politics"]
    all_results = []
    seen_titles = set()

    for cat in categories:
        try:
            response = api.latest_api(country="th", category=cat)
            results = response.get("results", [])
            for news_item in results:
                title = news_item.get("title", "").strip()
                if title and title not in seen_titles and news_item.get("description") is not None:
                    seen_titles.add(title)
                    all_results.append(news_item)
        except Exception:
            continue

    for news_item in all_results:
        pub_date_str = news_item.get("pubDate")
        pub_date = None
        if pub_date_str:
            try:
                pub_date = datetime.fromisoformat(pub_date_str)
            except Exception:
                pub_date = utils.get_current_time()
        else:
            pub_date = utils.get_current_time()

        new_news = models.News(
            topic=news_item.get("title", ""),
            content=news_item.get("description", ""),
            file=news_item.get("image_url", "") or "",
            news_time=pub_date,
        )
        db.add(new_news)

    db.commit()

    return {"message": "News created"}

