"""Sender IDs are hashed before storage (PRD 7, Privacy)."""
import hashlib
import hmac
import os
import re

from dotenv import load_dotenv

load_dotenv()

SALT = os.getenv("SENDER_HASH_SALT", "change-me").encode()


def normalize_phone(sender: str) -> str:
    digits = re.sub(r"\D", "", sender)
    # "+91 98765-43210" and "09876543210" are the same person.
    return digits[-10:] if digits else sender.strip().lower()


def hash_sender(sender: str) -> str:
    # Keyed hash, not plain sha256: there are only ~10^10 phone numbers,
    # so an unsalted hash could be reversed by trying them all.
    return hmac.new(SALT, normalize_phone(sender).encode(), hashlib.sha256).hexdigest()[:16]
