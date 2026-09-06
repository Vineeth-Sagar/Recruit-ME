"""Import every model so ``Base.metadata`` is complete for Alembic + create_all."""

from .auth import (
    EmailChangeToken,
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)
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
from .site_credential import (
    CredentialAuthType,
    CredentialSite,
    CredentialStatus,
    SiteCredential,
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
    "EmailChangeToken",
    "PasswordResetToken",
    "JobProfile",
    "Resume",
    "ResumeParse",
    "ResumeStatus",
    "SiteCredential",
    "CredentialSite",
    "CredentialAuthType",
    "CredentialStatus",
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
