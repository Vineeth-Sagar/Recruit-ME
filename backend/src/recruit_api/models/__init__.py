"""Import every model so ``Base.metadata`` is complete for Alembic + create_all."""

from .auth import EmailVerificationToken, PasswordResetToken, RefreshToken
from .base import Base
from .job_profile import JobProfile
from .resume import Resume, ResumeParse, ResumeStatus
from .run import (
    TERMINAL_RUN_STATUSES,
    JobMatch,
    MatchStatus,
    Notification,
    Run,
    RunSource,
    RunStatus,
    RunStep,
    RunTrigger,
)
from .user import User, UserPlan, UserRole, UserStatus

__all__ = [
    "Base",
    "User",
    "UserRole",
    "UserPlan",
    "UserStatus",
    "RefreshToken",
    "EmailVerificationToken",
    "PasswordResetToken",
    "JobProfile",
    "Resume",
    "ResumeParse",
    "ResumeStatus",
    "Run",
    "RunStep",
    "RunSource",
    "JobMatch",
    "Notification",
    "RunStatus",
    "RunTrigger",
    "MatchStatus",
    "TERMINAL_RUN_STATUSES",
]
