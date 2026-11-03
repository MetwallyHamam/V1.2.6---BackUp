import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.news.models import (
    NewsComment,
    NewsLike,
    NewsMention,
    NewsPollOption,
    NewsPollVote,
    NewsPost,
    NewsUserAction,
)
from app.modules.notifications.models import Notification

router = APIRouter(prefix="/news", tags=["news"])
TEMPLATES = {"NEWCOMER", "ANNOUNCEMENT", "UPDATE", "EVENT", "MAINTENANCE", "GENERAL"}


class NewsWrite(BaseModel):
    template: str = Field(default="GENERAL", max_length=40)
    title: str = Field(min_length=3, max_length=300)
    summary: str = Field(min_length=3, max_length=1000)
    body: str = Field(min_length=3, max_length=50000)
    video_url: str | None = Field(default=None, max_length=1000)
    audience: Literal["ALL", "INTERNAL", "PORTAL"] = "ALL"
    is_featured: bool = False
    requires_confirmation: bool = False
    is_template: bool = False
    publish_from: datetime | None = None
    publish_until: datetime | None = None
    mention_user_ids: list[int] = Field(default_factory=list, max_length=100)
    poll_options: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_values(self) -> "NewsWrite":
        self.template = self.template.upper()
        if self.template not in TEMPLATES:
            raise ValueError("Unsupported news template.")
        if self.publish_from and self.publish_until and self.publish_until <= self.publish_from:
            raise ValueError("Publish until must be after publish from.")
        if self.video_url:
            parsed = urlparse(self.video_url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or not (
                host.endswith("youtube.com") or host == "youtu.be" or host.endswith("vimeo.com")
            ):
                raise ValueError("Only HTTPS YouTube or Vimeo video links are allowed.")
        self.mention_user_ids = list(dict.fromkeys(self.mention_user_ids))
        self.poll_options = [value.strip() for value in self.poll_options if value.strip()]
        if self.poll_options and len(self.poll_options) < 2:
            raise ValueError("A poll requires at least two choices.")
        return self


class NewsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template: str
    title: str
    summary: str
    body: str
    video_url: str | None
    audience: str
    status: str
    effective_status: str
    is_featured: bool
    requires_confirmation: bool
    is_template: bool
    publish_from: datetime | None
    publish_until: datetime | None
    author_user_id: int
    author_name: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    image_url: str | None
    confirmed: bool
    dismissed: bool
    confirmation_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    liked: bool = False
    mentions: list[dict[str, object]] = []
    poll_options: list[dict[str, object]] = []
    poll_vote_option_id: int | None = None


class NewsCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    mention_user_ids: list[int] = Field(default_factory=list, max_length=20)


class NewsMentionCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    is_active: bool


class NewsCommentRead(BaseModel):
    id: int
    author_user_id: int
    author_name: str
    body: str
    created_at: datetime


def effective_status(row: NewsPost, now: datetime) -> str:
    if row.status != "PUBLISHED":
        return row.status
    if row.publish_from and row.publish_from > now:
        return "SCHEDULED"
    if row.publish_until and row.publish_until <= now:
        return "EXPIRED"
    return "PUBLISHED"


def visible_to(row: NewsPost, actor: User, now: datetime) -> bool:
    portal = actor.user_type == "CLIENT_PORTAL"
    return effective_status(row, now) == "PUBLISHED" and row.audience in (
        {"ALL", "PORTAL"} if portal else {"ALL", "INTERNAL"}
    )


def serialize(db: Session, row: NewsPost, actor: User, *, analytics: bool = False) -> NewsRead:
    action = db.scalar(
        select(NewsUserAction).where(
            NewsUserAction.news_post_id == row.id, NewsUserAction.user_id == actor.id
        )
    )
    author = db.get(User, row.author_user_id)
    count = (
        db.scalar(
            select(func.count())
            .select_from(NewsUserAction)
            .where(NewsUserAction.news_post_id == row.id, NewsUserAction.confirmed_at.is_not(None))
        )
        if analytics
        else 0
    )
    mention_ids = list(db.scalars(select(NewsMention.user_id).where(NewsMention.news_post_id == row.id)))
    mentioned_users = list(db.scalars(select(User).where(User.id.in_(mention_ids)))) if mention_ids else []
    options = list(db.scalars(select(NewsPollOption).where(NewsPollOption.news_post_id == row.id).order_by(NewsPollOption.position)))
    vote_counts: dict[int, int] = {
        option_id: int(total)
        for option_id, total in db.execute(
            select(NewsPollVote.option_id, func.count())
            .where(NewsPollVote.news_post_id == row.id)
            .group_by(NewsPollVote.option_id)
        ).all()
    }
    own_vote = db.scalar(select(NewsPollVote.option_id).where(NewsPollVote.news_post_id == row.id, NewsPollVote.user_id == actor.id))
    return NewsRead(
        **{
            key: getattr(row, key)
            for key in (
                "id",
                "template",
                "title",
                "summary",
                "body",
                "video_url",
                "audience",
                "status",
                "is_featured",
                "requires_confirmation",
                "is_template",
                "publish_from",
                "publish_until",
                "author_user_id",
                "published_at",
                "created_at",
                "updated_at",
            )
        },
        effective_status=effective_status(row, server_now()),
        author_name=author.full_name if author else "Unknown",
        image_url=f"/news/{row.id}/image" if row.image_filename else None,
        confirmed=bool(action and action.confirmed_at),
        dismissed=bool(action and action.dismissed_at),
        confirmation_count=int(count or 0),
        like_count=int(db.scalar(select(func.count()).select_from(NewsLike).where(NewsLike.news_post_id == row.id)) or 0),
        comment_count=int(db.scalar(select(func.count()).select_from(NewsComment).where(NewsComment.news_post_id == row.id)) or 0),
        liked=db.scalar(select(NewsLike.id).where(NewsLike.news_post_id == row.id, NewsLike.user_id == actor.id)) is not None,
        mentions=[{"id": user.id, "name": user.full_name} for user in mentioned_users],
        poll_options=[{"id": option.id, "label": option.label, "votes": int(vote_counts.get(option.id, 0))} for option in options],
        poll_vote_option_id=own_vote,
    )


def replace_composer_extras(db: Session, row: NewsPost, data: NewsWrite) -> None:
    db.query(NewsMention).filter(NewsMention.news_post_id == row.id).delete(synchronize_session=False)
    for user_id in data.mention_user_ids:
        if db.get(User, user_id):
            db.add(NewsMention(news_post_id=row.id, user_id=user_id))
    if not db.scalar(select(NewsPollVote.id).where(NewsPollVote.news_post_id == row.id)):
        db.query(NewsPollOption).filter(NewsPollOption.news_post_id == row.id).delete(synchronize_session=False)
        for position, label in enumerate(data.poll_options):
            db.add(NewsPollOption(news_post_id=row.id, label=label, position=position))


def require_visible_news(db: Session, post_id: int, actor: User) -> NewsPost:
    row = db.get(NewsPost, post_id)
    grants = effective_permissions(db, actor).permissions
    if not row or (not visible_to(row, actor, server_now()) and not ({"news.manage", "news.publish"} & set(grants))):
        raise NotFoundError("News post not found.")
    return row


@router.get("", response_model=list[NewsRead])
def list_news(
    include_all: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("news.view")),
) -> list[NewsRead]:
    now = server_now()
    rows = list(
        db.scalars(
            select(NewsPost).order_by(
                NewsPost.is_featured.desc(),
                NewsPost.publish_from.desc(),
                NewsPost.created_at.desc(),
            )
        )
    )
    grants = effective_permissions(db, actor).permissions
    can_manage = bool({"news.manage", "news.publish"} & set(grants))
    if not include_all or not can_manage:
        actions = {
            item.news_post_id: item
            for item in db.scalars(select(NewsUserAction).where(NewsUserAction.user_id == actor.id))
        }
        rows = [
            row
            for row in rows
            if not row.is_template and visible_to(row, actor, now)
            and not (actions.get(row.id) and actions[row.id].dismissed_at)
        ]
    return [serialize(db, row, actor, analytics=can_manage) for row in rows]


@router.get("/mention-candidates", response_model=list[NewsMentionCandidateRead])
def list_news_mention_candidates(
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("news.view", "news.create")),
) -> list[User]:
    return list(
        db.scalars(
            select(User).where(User.is_active.in_([True])).order_by(User.full_name)
        )
    )


@router.post("", response_model=NewsRead)
def create_news(
    data: NewsWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("news.create")),
) -> NewsRead:
    base = data.model_dump(exclude={"mention_user_ids", "poll_options"})
    row = NewsPost(**base, author_user_id=actor.id)
    db.add(row)
    db.flush()
    replace_composer_extras(db, row, data)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="NewsPost",
            entity_id=str(row.id),
            action="CREATED",
            new_values_json=json.dumps({"title": row.title, "audience": row.audience}),
        )
    )
    db.commit()
    db.refresh(row)
    return serialize(db, row, actor)


@router.put("/{post_id}", response_model=NewsRead)
def update_news(
    post_id: int,
    data: NewsWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("news.create", "news.manage")),
) -> NewsRead:
    row = db.get(NewsPost, post_id)
    if not row:
        raise NotFoundError("News post not found.")
    grants = effective_permissions(db, actor).permissions
    if row.author_user_id != actor.id and "news.manage" not in grants:
        raise AuthorizationError("Only the author or a news manager can edit this post.")
    for key, value in data.model_dump(exclude={"mention_user_ids", "poll_options"}).items():
        setattr(row, key, value)
    replace_composer_extras(db, row, data)
    db.add(
        AuditLog(
            actor_user_id=actor.id, entity_type="NewsPost", entity_id=str(row.id), action="UPDATED"
        )
    )
    db.commit()
    db.refresh(row)
    return serialize(db, row, actor, analytics=True)


@router.post("/{post_id}/publish", response_model=NewsRead)
def publish_news(
    post_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("news.publish")),
) -> NewsRead:
    row = db.get(NewsPost, post_id)
    if not row:
        raise NotFoundError("News post not found.")
    if row.is_template:
        raise ConflictError(
            "NEWS_TEMPLATE_CANNOT_PUBLISH",
            "Use this template to create a new post before publishing.",
        )
    row.status = "PUBLISHED"
    row.published_by_user_id = actor.id
    row.published_at = server_now()
    mention_ids = list(db.scalars(select(NewsMention.user_id).where(NewsMention.news_post_id == row.id)))
    for user_id in mention_ids:
        if user_id != actor.id:
            db.add(Notification(recipient_user_id=user_id, notification_type="NEWS_MENTION", severity="INFO", title=f"Mentioned in news: {row.title}"[:200], message=f"{actor.full_name} mentioned you in a news post.", deep_link="/news", deduplication_key=f"news-mention:{row.id}:user:{user_id}"))
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="NewsPost",
            entity_id=str(row.id),
            action="PUBLISHED",
        )
    )
    db.commit()
    db.refresh(row)
    return serialize(db, row, actor, analytics=True)


@router.post("/{post_id}/unpublish", response_model=NewsRead)
def unpublish_news(
    post_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("news.publish")),
) -> NewsRead:
    row = db.get(NewsPost, post_id)
    if not row:
        raise NotFoundError("News post not found.")
    row.status = "UNPUBLISHED"
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="NewsPost",
            entity_id=str(row.id),
            action="UNPUBLISHED",
        )
    )
    db.commit()
    db.refresh(row)
    return serialize(db, row, actor, analytics=True)


@router.delete("/{post_id}", status_code=204)
def delete_news(
    post_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("news.manage")),
    settings: Settings = Depends(get_settings),
) -> None:
    row = db.get(NewsPost, post_id)
    if not row:
        raise NotFoundError("News post not found.")
    image_filename = row.image_filename
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="NewsPost",
            entity_id=str(row.id),
            action="DELETED",
            old_values_json=json.dumps({"title": row.title, "status": row.status}),
        )
    )
    db.delete(row)
    db.commit()
    if image_filename:
        path = Path(settings.attachment_storage_path).expanduser().resolve() / "news" / image_filename
        path.unlink(missing_ok=True)


@router.post("/{post_id}/action", response_model=NewsRead)
def news_action(
    post_id: int,
    action: Literal["VIEW", "CONFIRM", "DISMISS"],
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("news.view")),
) -> NewsRead:
    row = db.get(NewsPost, post_id)
    if not row or not visible_to(row, actor, server_now()):
        raise NotFoundError("News post not found.")
    state = db.scalar(
        select(NewsUserAction).where(
            NewsUserAction.news_post_id == row.id, NewsUserAction.user_id == actor.id
        )
    )
    if not state:
        state = NewsUserAction(news_post_id=row.id, user_id=actor.id)
        db.add(state)
    now = server_now()
    if action == "VIEW":
        state.viewed_at = now
    elif action == "CONFIRM":
        state.confirmed_at = now
        state.dismissed_at = None
    else:
        state.dismissed_at = now
    db.commit()
    return serialize(db, row, actor)


@router.post("/{post_id}/like", response_model=NewsRead)
def toggle_like(post_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("news.view"))) -> NewsRead:
    row = require_visible_news(db, post_id, actor)
    existing = db.scalar(select(NewsLike).where(NewsLike.news_post_id == post_id, NewsLike.user_id == actor.id))
    if existing:
        db.delete(existing)
    else:
        db.add(NewsLike(news_post_id=post_id, user_id=actor.id))
    db.commit()
    return serialize(db, row, actor)


@router.get("/{post_id}/comments", response_model=list[NewsCommentRead])
def list_comments(post_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("news.view"))) -> list[NewsCommentRead]:
    require_visible_news(db, post_id, actor)
    rows = list(db.scalars(select(NewsComment).where(NewsComment.news_post_id == post_id).order_by(NewsComment.created_at)))
    users = {user.id: user.full_name for user in db.scalars(select(User).where(User.id.in_({row.author_user_id for row in rows})))} if rows else {}
    return [NewsCommentRead(id=row.id, author_user_id=row.author_user_id, author_name=users.get(row.author_user_id, "Unknown"), body=row.body, created_at=row.created_at) for row in rows]


@router.post("/{post_id}/comments", response_model=NewsCommentRead, status_code=201)
def add_comment(post_id: int, data: NewsCommentCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("news.view"))) -> NewsCommentRead:
    post = require_visible_news(db, post_id, actor)
    row = NewsComment(news_post_id=post_id, author_user_id=actor.id, body=data.body.strip())
    db.add(row)
    db.flush()
    recipient_ids = set(data.mention_user_ids) - {actor.id}
    active_recipient_ids = set(
        db.scalars(
            select(User.id).where(
                User.id.in_(recipient_ids), User.is_active.in_([True])
            )
        )
    ) if recipient_ids else set()
    for user_id in active_recipient_ids:
        db.add(Notification(
            recipient_user_id=user_id,
            notification_type="NEWS_COMMENT_MENTION",
            severity="INFO",
            title=f"Mentioned in a comment: {post.title}"[:200],
            message=f"{actor.full_name} mentioned you in a news comment.",
            deep_link="/news",
            deduplication_key=f"news-comment-mention:{row.id}:user:{user_id}",
        ))
    db.commit()
    db.refresh(row)
    return NewsCommentRead(id=row.id, author_user_id=actor.id, author_name=actor.full_name, body=row.body, created_at=row.created_at)


@router.post("/{post_id}/poll/{option_id}", response_model=NewsRead)
def vote_poll(post_id: int, option_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("news.view"))) -> NewsRead:
    row = require_visible_news(db, post_id, actor)
    option = db.scalar(select(NewsPollOption).where(NewsPollOption.id == option_id, NewsPollOption.news_post_id == post_id))
    if not option:
        raise NotFoundError("Poll option not found.")
    vote = db.scalar(select(NewsPollVote).where(NewsPollVote.news_post_id == post_id, NewsPollVote.user_id == actor.id))
    if vote:
        vote.option_id = option_id
    else:
        db.add(NewsPollVote(news_post_id=post_id, option_id=option_id, user_id=actor.id))
    db.commit()
    return serialize(db, row, actor)


@router.post("/{post_id}/image", response_model=NewsRead)
async def upload_image(
    post_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("news.create", "news.manage")),
    settings: Settings = Depends(get_settings),
) -> NewsRead:
    row = db.get(NewsPost, post_id)
    if not row:
        raise NotFoundError("News post not found.")
    grants = effective_permissions(db, actor).permissions
    if row.author_user_id != actor.id and "news.manage" not in grants:
        raise AuthorizationError("Only the author or a news manager can update this image.")
    allowed = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    if upload.content_type not in allowed:
        raise AppError("NEWS_IMAGE_TYPE_INVALID", "Use JPG, PNG, WebP or GIF images.", 415)
    content = await upload.read(settings.attachment_max_bytes + 1)
    if len(content) > settings.attachment_max_bytes:
        raise AppError("NEWS_IMAGE_TOO_LARGE", "The image exceeds the upload limit.", 413)
    directory = (Path(settings.attachment_storage_path).expanduser().resolve() / "news").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{row.id}-{uuid.uuid4().hex}{allowed[upload.content_type]}"
    (directory / filename).write_bytes(content)
    row.image_filename = filename
    row.image_content_type = upload.content_type
    db.commit()
    db.refresh(row)
    return serialize(db, row, actor, analytics=True)


@router.get("/{post_id}/image")
def get_image(
    post_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("news.view")),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    row = db.get(NewsPost, post_id)
    if not row or not row.image_filename:
        raise NotFoundError("News image not found.")
    grants = effective_permissions(db, actor).permissions
    if not visible_to(row, actor, server_now()) and not (
        {"news.manage", "news.publish"} & set(grants)
    ):
        raise NotFoundError("News image not found.")
    path = (
        Path(settings.attachment_storage_path).expanduser().resolve() / "news" / row.image_filename
    ).resolve()
    if not path.is_file():
        raise NotFoundError("News image not found.")
    return FileResponse(path, media_type=row.image_content_type or "application/octet-stream")
