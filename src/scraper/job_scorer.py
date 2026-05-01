"""
Job Relevance Scorer — phân tích title + description để tính điểm phù hợp.
"""
from src.utils.logger import log


def title_pre_filter(job: dict, scoring_cfg: dict) -> bool:
    """
    Quick title-only pre-filter: loại bỏ job rõ ràng không liên quan
    mà không cần fetch description (tiết kiệm request).
    """
    title = job.get("title", "").lower()
    for kw in scoring_cfg.get("title_exclude_keywords", []):
        if kw.lower() in title:
            log.debug(f"  [pre-filter] excluded by title keyword '{kw}': {job.get('title')}")
            return False
    return True


def score_job(job: dict, scoring_cfg: dict) -> tuple[int, list[str]]:
    """
    Chấm điểm job từ 0–100 dựa trên title + description.
    Trả về (score, danh sách keyword khớp).
    """
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    full_text = title + " " + description

    score = 0
    matched: list[str] = []

    # Title include keywords: +20 pts mỗi keyword khớp trong title
    for kw in scoring_cfg.get("title_include_keywords", []):
        if kw.lower() in title:
            score += 20
            matched.append(kw)

    # Title exclude keywords: -40 pts (đã được pre-filter nhưng double-check)
    for kw in scoring_cfg.get("title_exclude_keywords", []):
        if kw.lower() in title:
            score -= 40

    # Must-have keywords trong full text: +15 pts mỗi keyword
    for kw in scoring_cfg.get("must_have_keywords", []):
        if kw.lower() in full_text:
            score += 15
            if kw not in matched:
                matched.append(kw)

    # Nice-to-have keywords: +5 pts mỗi keyword
    for kw in scoring_cfg.get("nice_to_have_keywords", []):
        if kw.lower() in full_text:
            score += 5
            if kw not in matched:
                matched.append(kw)

    # Exclude keywords (hard penalty: -50 pts) — tín hiệu không phù hợp
    for kw in scoring_cfg.get("exclude_keywords", []):
        if kw.lower() in full_text:
            score -= 50
            log.debug(f"  [-50] exclude keyword: '{kw}' in '{job.get('title')}'")

    # Clamp về [0, 100]
    final_score = max(0, min(100, score))

    # Deduplicate matched list (case-insensitive)
    seen: set[str] = set()
    unique_matched: list[str] = []
    for m in matched:
        ml = m.lower()
        if ml not in seen:
            seen.add(ml)
            unique_matched.append(m)

    return final_score, unique_matched
