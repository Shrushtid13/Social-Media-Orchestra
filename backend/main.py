# backend/main.py
import os
import uuid
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from langgraph.types import Command

load_dotenv()

from graph import graph

# ── App Setup ─────────────────────────────────────────────────
app = FastAPI(
    title="Social Media Automation API",
    description="LangGraph + Mistral powered social media automation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In Memory Job Store ───────────────────────────────────────
# Replace with Redis when scaling
jobs: dict = {}


# ══════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════

class ImagePlatformSettings(BaseModel):
    mode:          str            # "none" | "generate" | "upload" | "both"
    style:         Optional[str] = "realistic"
    uploaded_path: Optional[str] = None


class GenerateRequest(BaseModel):
    topic:            str
    brand_voice:      str         = "professional"
    target_platforms: list[str]
    posting_mode:     str         = "simultaneous"
    llm_name:         str         = "mistral-large"
    temperature:      float       = 0.7
    image_settings:   dict        = {}
    # Example image_settings:
    # {
    #   "twitter":   {"mode": "generate", "style": "realistic"},
    #   "instagram": {"mode": "both",     "style": "cinematic", "uploaded_path": "uploads/ig.png"},
    #   "linkedin":  {"mode": "none"}
    # }


class ReviewRequest(BaseModel):
    action:        str            # "approve" | "revise" | "reject"
    notes:         Optional[str] = ""
    image_choices: Optional[dict] = {}
    # image_choices example:
    # {"twitter": "generated", "instagram": "uploaded"}


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

# ── Health Check ──────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status":  "running",
        "message": "Social Media Automation API",
        "version": "1.0.0",
        "docs":    "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ── Image Upload ──────────────────────────────────────────────

@app.post("/api/upload")
async def upload_image(
    file:     UploadFile = File(...),
    platform: str        = Form(...)
):
    """
    Upload an image for a specific platform.
    Returns the file path to use in image_settings.
    """

    # Validate file type
    allowed = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Use: {allowed}"
        )

    # Validate platform
    valid_platforms = ["twitter", "instagram", "linkedin"]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Choose from: {valid_platforms}"
        )

    # Save file
    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{platform}_{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = os.path.join(save_dir, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    return {
        "status":   "uploaded",
        "platform": platform,
        "path":     filepath,
        "filename": filename,
        "size_kb":  round(len(contents) / 1024, 2)
    }


# ── Generate Posts ────────────────────────────────────────────

@app.post("/api/generate")
async def generate_posts(request: GenerateRequest):
    """
    Starts the LangGraph automation pipeline.
    Runs until human review interrupt.
    Returns job_id to poll for status.
    """

    # Validate platforms
    valid_platforms = ["twitter", "instagram", "linkedin"]
    invalid = [
        p for p in request.target_platforms
        if p not in valid_platforms
    ]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platforms: {invalid}. "
                   f"Choose from: {valid_platforms}"
        )

    # Validate at least one platform
    if not request.target_platforms:
        raise HTTPException(
            status_code=400,
            detail="At least one platform is required"
        )

    # Validate topic
    if not request.topic.strip():
        raise HTTPException(
            status_code=400,
            detail="Topic cannot be empty"
        )

    # Create job
    job_id    = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id":    job_id,
        "thread_id": thread_id,
        "status":    "starting",
        "phase":     "initializing",
        "progress":  [],
        "error":     None,

        # Filled after graph runs
        "formatted_posts":   {},
        "image_candidates":  {},
        "platform_results":  {},
        "raw_content":       "",
        "aggregator_summary": {}
    }

    # Run graph in background
    asyncio.create_task(
        _run_until_review(job_id, thread_id, request)
    )

    return {
        "job_id":    job_id,
        "status":    "started",
        "message":   "Generation started. Poll /api/status/{job_id} for updates."
    }


# ── Job Status ────────────────────────────────────────────────

@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    """
    Poll this endpoint to track job progress.

    Possible statuses:
    - starting          → job just created
    - running           → graph is executing
    - awaiting_review   → graph paused, ready for human review
    - publishing        → graph resumed, posting to platforms
    - done              → all done, results available
    - failed            → something went wrong
    """

    job = jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return job


# ── Submit Review ─────────────────────────────────────────────

@app.post("/api/review/{job_id}")
async def submit_review(job_id: str, review: ReviewRequest):
    """
    Submit human review decision.
    Resumes the paused LangGraph.

    Actions:
    - approve → posts go live
    - revise  → regenerates content with notes
    - reject  → cancels workflow
    """

    job = jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    if job["status"] != "awaiting_review":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not awaiting review. "
                   f"Current status: {job['status']}"
        )

    # Validate action
    valid_actions = ["approve", "revise", "reject"]
    if review.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {review.action}. "
                   f"Choose from: {valid_actions}"
        )

    # Update job status
    jobs[job_id]["status"] = "publishing"
    jobs[job_id]["phase"]  = "resuming_graph"
    jobs[job_id]["progress"].append(
        f"Human decision: {review.action}"
    )

    # Resume graph in background
    asyncio.create_task(
        _resume_after_review(job_id, review)
    )

    return {
        "job_id":  job_id,
        "status":  "publishing",
        "action":  review.action,
        "message": f"Decision '{review.action}' submitted. "
                   f"Poll /api/status/{job_id} for updates."
    }


# ── Get Available Models ──────────────────────────────────────

@app.get("/api/models")
def get_models():
    """Returns available Mistral models."""

    api_key    = os.getenv("MISTRAL_API_KEY")
    configured = bool(api_key)

    return {
        "mistral-large": {
            "label":       "Mistral Large",
            "description": "Best quality writing",
            "configured":  configured,
            "speed":       "slow",
            "cost":        "high"
        },
        "mistral-small": {
            "label":       "Mistral Small",
            "description": "Fast and affordable",
            "configured":  configured,
            "speed":       "fast",
            "cost":        "low"
        },
        "mistral-nemo": {
            "label":       "Mistral Nemo",
            "description": "Free tier",
            "configured":  configured,
            "speed":       "fastest",
            "cost":        "free"
        }
    }


# ── Cancel Job ────────────────────────────────────────────────

@app.delete("/api/job/{job_id}")
def cancel_job(job_id: str):
    """Cancels and removes a job."""

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    del jobs[job_id]

    return {
        "job_id":  job_id,
        "status":  "cancelled",
        "message": "Job removed"
    }


# ── List All Jobs ─────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs():
    """Returns all current jobs and their statuses."""

    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job["status"],
                "phase":  job["phase"]
            }
            for job_id, job in jobs.items()
        ]
    }


# ══════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ══════════════════════════════════════════════════════════════

async def _run_until_review(
    job_id:    str,
    thread_id: str,
    request:   GenerateRequest
):
    """
    Runs LangGraph until it hits the human_review interrupt.
    Updates job status at each step.
    """

    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Update progress
        _update_job(job_id, "running", "generating_content",
                    "✍️ Generating content with Mistral...")

        # Run graph — will pause at human_review interrupt
        await graph.ainvoke({
            "llm_name":           request.llm_name,
            "temperature":        request.temperature,
            "llm":                None,
            "topic":              request.topic,
            "brand_voice":        request.brand_voice,
            "target_platforms":   request.target_platforms,
            "posting_mode":       request.posting_mode,
            "image_settings":     request.image_settings,
            "image_candidates":   {},
            "chosen_images":      {},
            "raw_content":        "",
            "formatted_posts":    {},
            "platform_results":   {},
            "human_decision":     "",
            "revision_notes":     "",
            "review_count":       0,
            "errors":             [],
            "current_platform":   "",
            "aggregator_summary": {}
        }, config)

        # Graph paused — get current state
        current_state = graph.get_state(config)
        state_values  = current_state.values

        # Update job with review data
        jobs[job_id].update({
            "status":           "awaiting_review",
            "phase":            "human_review",
            "formatted_posts":  state_values.get("formatted_posts",  {}),
            "image_candidates": state_values.get("image_candidates", {}),
            "raw_content":      state_values.get("raw_content",      ""),
            "platform_results": state_values.get("platform_results", {}),
        })

        jobs[job_id]["progress"].append(
            "⏸️ Graph paused — awaiting human review"
        )

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "phase":  "error",
            "error":  str(e)
        })
        jobs[job_id]["progress"].append(f"❌ Error: {str(e)}")


async def _resume_after_review(
    job_id: str,
    review: ReviewRequest
):
    """
    Resumes the paused LangGraph with human decision.
    Handles approve, revise, and reject flows.
    """

    job       = jobs[job_id]
    thread_id = job["thread_id"]
    config    = {"configurable": {"thread_id": thread_id}}

    try:
        _update_job(job_id, "publishing", "resuming",
                    f"▶️ Resuming graph with decision: {review.action}")

        # Resume graph
        result = await graph.ainvoke(
            Command(resume={
                "action":        review.action,
                "notes":         review.notes or "",
                "image_choices": review.image_choices or {}
            }),
            config
        )

        # ── Revise: graph looped back to content_agent ─────
        if review.action == "revise":
            # Graph paused again at human_review
            current_state = graph.get_state(config)
            state_values  = current_state.values

            jobs[job_id].update({
                "status":           "awaiting_review",
                "phase":            "human_review",
                "formatted_posts":  state_values.get("formatted_posts",  {}),
                "image_candidates": state_values.get("image_candidates", {}),
                "raw_content":      state_values.get("raw_content",      ""),
                "platform_results": state_values.get("platform_results", {}),
            })

            jobs[job_id]["progress"].append(
                "🔄 Content regenerated — awaiting review again"
            )

        # ── Reject: workflow cancelled ─────────────────────
        elif review.action == "reject":
            jobs[job_id].update({
                "status": "rejected",
                "phase":  "cancelled"
            })
            jobs[job_id]["progress"].append("🚫 Post rejected")

        # ── Approve: posts published ───────────────────────
        else:
            jobs[job_id].update({
                "status":             "done",
                "phase":              "complete",
                "formatted_posts":    result.get("formatted_posts",    {}),
                "platform_results":   result.get("platform_results",   {}),
                "aggregator_summary": result.get("aggregator_summary", {})
            })
            jobs[job_id]["progress"].append("✅ Posts published!")

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "phase":  "error",
            "error":  str(e)
        })
        jobs[job_id]["progress"].append(f"❌ Error: {str(e)}")


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _update_job(
    job_id:  str,
    status:  str,
    phase:   str,
    message: str
):
    """Helper to update job status and append progress message."""

    jobs[job_id]["status"] = status
    jobs[job_id]["phase"]  = phase
    jobs[job_id]["progress"].append(message)


# ══════════════════════════════════════════════════════════════
# SERVE STREAMLIT STATIC (OPTIONAL)
# ══════════════════════════════════════════════════════════════

# Serve uploaded images so Streamlit can display them
os.makedirs("uploads",          exist_ok=True)
os.makedirs("generated_images", exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)

app.mount(
    "/generated",
    StaticFiles(directory="generated_images"),
    name="generated_images"
)