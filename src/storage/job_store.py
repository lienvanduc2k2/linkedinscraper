"""
SQLite storage for tracking sent jobs to avoid duplicates.
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from src.utils.logger import log


class Base(DeclarativeBase):
    pass


class SentJob(Base):
    __tablename__ = "sent_jobs"

    job_id = Column(String(255), primary_key=True)
    title = Column(String(500))
    company = Column(String(255))
    location = Column(String(255))
    url = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    keyword = Column(String(255))


class JobStore:
    def __init__(self, db_path: str = "data/jobs.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        log.info(f"JobStore initialized at {db_path}")

    def is_sent(self, job_id: str) -> bool:
        """Check if a job was already sent."""
        with self.Session() as session:
            return session.get(SentJob, job_id) is not None

    def mark_sent(self, job: dict, keyword: str = ""):
        """Mark a job as sent."""
        with self.Session() as session:
            entry = SentJob(
                job_id=job["job_id"],
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                url=job.get("url", ""),
                keyword=keyword,
                sent_at=datetime.utcnow(),
            )
            session.merge(entry)
            session.commit()

    def get_new_jobs(self, jobs: list[dict], keyword: str = "") -> list[dict]:
        """Filter out already-sent jobs, return only new ones."""
        new_jobs = []
        for job in jobs:
            if not self.is_sent(job["job_id"]):
                new_jobs.append(job)
        log.info(f"[{keyword}] {len(new_jobs)}/{len(jobs)} jobs are new")
        return new_jobs
