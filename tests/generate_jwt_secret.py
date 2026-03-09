"""Generate secure JWT secret for production use."""

import secrets


def generate_jwt_secret():
    """Generate a cryptographically secure JWT secret."""
    return secrets.token_urlsafe(32)


if __name__ == "__main__":
    print("=" * 70)
    print("JWT SECRET GENERATOR")
    print("=" * 70)
    print()
    print("Copy this secret to your .env file:")
    print()
    print(f"JWT_SECRET={generate_jwt_secret()}")
    print()
    print("=" * 70)
    print("IMPORTANT: Keep this secret secure! Never commit it to git.")
    print("=" * 70)
