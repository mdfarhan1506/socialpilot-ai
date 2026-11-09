"""Pre-Publish Quality Validation — Phase 8.

Validates a post before it is submitted to the Instagram publishing pipeline.

Checks performed (in order):
1. Mock-content guard: caption must not contain [MOCK] markers.
2. Caption presence and minimum quality (not empty, not too short, not a placeholder).
3. Caption length and hashtag count (Instagram limits).
4. Image URL: must be a valid public HTTPS URL with a supported image extension or known CDN host.
5. Image URL reachability: HTTP HEAD request to confirm the URL is accessible.
6. No malformed or obviously irrelevant captions (all-whitespace, repetitive chars).

STRICT RULES:
- Never silently pass a post that fails validation.
- Always record the specific failure reason in the ValidationResult.
- Never attempt a real HEAD request in mock mode (unnecessary network call).
- Validation failures cause publishing to be aborted; the reason is logged to the audit trail.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)

# Instagram publishing constraints
CAPTION_MAX_CHARS = 2200
CAPTION_MIN_CHARS = 5
HASHTAG_MAX = 30
VALID_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
KNOWN_CDN_HOSTS = [
    "images.unsplash.com",
    "via.placeholder.com",
    "minio",
    "s3.amazonaws.com",
    "cdn.",
    "cloudinary.com",
    "imgix.net",
    "supabase.co/storage",
]

# Patterns indicating placeholder / mock content
MOCK_PATTERNS = [
    "[MOCK]",
    "[mock]",
    "MOCK_CAPTION",
    "PLACEHOLDER_",
    "lorem ipsum",
    "test caption",
]


@dataclass
class ValidationResult:
    """Result of a pre-publish validation run."""
    passed: bool
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.passed:
            return "Validation passed" + (f" with {len(self.warnings)} warning(s)" if self.warnings else "")
        return f"Validation FAILED: {'; '.join(self.failures)}"


def validate_caption(caption: Optional[str]) -> ValidationResult:
    """Validate the caption for Instagram publishing requirements."""
    failures: List[str] = []
    warnings: List[str] = []

    if not caption or not caption.strip():
        return ValidationResult(passed=False, failures=["Caption is empty or missing"])

    stripped = caption.strip()

    # Mock content guard
    for pat in MOCK_PATTERNS:
        if pat.lower() in stripped.lower():
            failures.append(f"Caption contains mock/placeholder content: '{pat}'")

    # Minimum length
    if len(stripped) < CAPTION_MIN_CHARS:
        failures.append(
            f"Caption too short ({len(stripped)} chars; minimum {CAPTION_MIN_CHARS})"
        )

    # Maximum length
    if len(stripped) > CAPTION_MAX_CHARS:
        failures.append(
            f"Caption too long ({len(stripped)} chars; Instagram limit {CAPTION_MAX_CHARS})"
        )

    # Hashtag limit
    hashtag_count = len(re.findall(r"#\w+", stripped))
    if hashtag_count > HASHTAG_MAX:
        failures.append(
            f"Too many hashtags ({hashtag_count}; Instagram limit {HASHTAG_MAX})"
        )

    # Repetitive / gibberish content check (all same chars repeated)
    unique_chars = len(set(stripped.replace(" ", "").replace("\n", "")))
    if unique_chars < 4 and len(stripped) > 10:
        failures.append("Caption appears to be repetitive/gibberish content")

    # All-whitespace body check
    if stripped == stripped[0] * len(stripped):
        failures.append("Caption is a single repeated character — invalid content")

    return ValidationResult(passed=len(failures) == 0, failures=failures, warnings=warnings)


def validate_image_url(image_url: Optional[str]) -> ValidationResult:
    """Validate image URL structure for Instagram publishing requirements.

    Does NOT make a network request — call validate_image_url_reachable() for that.
    """
    failures: List[str] = []
    warnings: List[str] = []

    if not image_url or not image_url.strip():
        return ValidationResult(passed=False, failures=["Image URL is empty or missing"])

    url = image_url.strip()

    # Must be HTTPS
    if not url.startswith("https://"):
        failures.append(
            "Image URL must begin with https:// (Instagram requires public HTTPS URLs)"
        )
        return ValidationResult(passed=False, failures=failures)

    # Mock URL guard
    if "MOCK" in url.upper() or "PLACEHOLDER" in url.upper() or "via.placeholder.com" in url.lower():
        # via.placeholder.com is a known test host — treat as warning in mock mode,
        # but still structurally valid
        warnings.append(
            "Image URL appears to be a placeholder or mock URL. "
            "In live mode this will likely not satisfy Instagram's media requirements."
        )

    url_lower = url.lower()

    # GIF not supported for feed posts
    if ".gif" in url_lower:
        failures.append(
            "GIF format is not supported for Instagram feed posts. Use JPG, PNG, or WebP."
        )
        return ValidationResult(passed=False, failures=failures)

    # Must have valid extension or be from a known CDN host
    has_valid_ext = any(
        url_lower.endswith(ext) or (ext + "?") in url_lower or (ext + "&") in url_lower
        for ext in VALID_IMAGE_EXTENSIONS
    )
    is_known_cdn = any(host in url_lower for host in KNOWN_CDN_HOSTS)

    if not (has_valid_ext or is_known_cdn):
        failures.append(
            f"Image URL does not appear to be a supported format "
            f"(expected {', '.join(VALID_IMAGE_EXTENSIONS)} or a recognized CDN host). "
            f"URL: {url[:80]}"
        )

    return ValidationResult(passed=len(failures) == 0, failures=failures, warnings=warnings)


async def validate_image_url_reachable(image_url: str, timeout: float = 8.0) -> ValidationResult:
    """Check that the image URL returns a successful HTTP response.

    Makes a lightweight HEAD request to confirm public accessibility.
    Should only be called in live/non-mock mode.
    """
    import httpx

    failures: List[str] = []
    warnings: List[str] = []

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.head(image_url)
            if resp.status_code == 405:
                # Some servers don't support HEAD; try GET with limited content
                resp = await client.get(image_url, headers={"Range": "bytes=0-1023"})

            if resp.status_code in (200, 206):
                content_type = resp.headers.get("content-type", "")
                if content_type and "image" not in content_type and "octet-stream" not in content_type:
                    warnings.append(
                        f"URL returned Content-Type '{content_type}' which may not be a valid image. "
                        "Instagram may reject this URL."
                    )
                return ValidationResult(passed=True, warnings=warnings)

            if resp.status_code in (401, 403):
                failures.append(
                    f"Image URL is not publicly accessible (HTTP {resp.status_code}). "
                    "Instagram requires the image to be publicly downloadable without authentication."
                )
            elif resp.status_code == 404:
                failures.append(
                    f"Image URL returned 404 Not Found. The file may have been deleted or moved."
                )
            else:
                failures.append(
                    f"Image URL returned unexpected status {resp.status_code}. "
                    "Instagram may be unable to fetch this image."
                )

    except httpx.TimeoutException:
        failures.append(
            f"Image URL timed out after {timeout}s. "
            "Instagram requires images to be served quickly from a reliable host."
        )
    except httpx.RequestError as exc:
        failures.append(
            f"Could not reach image URL: {exc}. "
            "Ensure the URL is publicly accessible from the internet."
        )
    except Exception as exc:
        failures.append(f"Unexpected error validating image URL reachability: {exc}")

    return ValidationResult(passed=len(failures) == 0, failures=failures, warnings=warnings)


async def validate_post_for_publishing(
    caption: Optional[str],
    image_url: Optional[str],
    is_mock: bool = True,
    check_reachability: bool = False,
) -> ValidationResult:
    """Run the full pre-publish validation pipeline.

    Args:
        caption: Post caption text.
        image_url: Image URL to validate.
        is_mock: When True, skip network reachability checks (not needed for simulated publishing).
        check_reachability: When True (and not mock), perform HTTP HEAD check on image URL.

    Returns:
        ValidationResult — passed=True means post can proceed to publishing.
    """
    all_failures: List[str] = []
    all_warnings: List[str] = []

    # 1. Validate caption
    cap_result = validate_caption(caption)
    all_failures.extend(cap_result.failures)
    all_warnings.extend(cap_result.warnings)

    # 2. Validate image URL structure
    img_result = validate_image_url(image_url)
    all_failures.extend(img_result.failures)
    all_warnings.extend(img_result.warnings)

    # 3. Network reachability (live mode only, when explicitly requested)
    if not is_mock and check_reachability and image_url and img_result.passed:
        reach_result = await validate_image_url_reachable(image_url)
        all_failures.extend(reach_result.failures)
        all_warnings.extend(reach_result.warnings)

    return ValidationResult(
        passed=len(all_failures) == 0,
        failures=all_failures,
        warnings=all_warnings,
    )
