"""Firebase Admin SDK initialization shared by authentication and storage."""

from __future__ import annotations

from threading import Lock

import firebase_admin
from firebase_admin import credentials

from app.core.config import Settings

_initialization_lock = Lock()


def initialize_firebase(settings: Settings) -> firebase_admin.App:
    """Return the configured Firebase app, initializing it at most once per process."""

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    with _initialization_lock:
        try:
            return firebase_admin.get_app()
        except ValueError:
            options: dict[str, str] = {}
            if settings.firebase_project_id:
                options["projectId"] = settings.firebase_project_id
            if settings.firebase_storage_bucket:
                options["storageBucket"] = settings.firebase_storage_bucket

            if settings.firebase_credentials_path:
                app_credential = credentials.Certificate(settings.firebase_credentials_path)
                return firebase_admin.initialize_app(app_credential, options or None)
            return firebase_admin.initialize_app(options=options or None)


__all__ = ["initialize_firebase"]
