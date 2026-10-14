import os
from pathlib import Path
from uuid import uuid4

import bleach
import markdown
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from llama_index.core import Settings, SimpleDirectoryReader, SummaryIndex, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.query_engine.router_query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIRECTORY = BASE_DIR / "data" / "uploads"
UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="DocumentSummarizer", version="1.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

ALLOWED_MARKDOWN_TAGS = [
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
]
ALLOWED_MARKDOWN_ATTRIBUTES = {"a": ["href", "title"]}


def configure_models() -> None:
    """Configure Gemini models using a key stored outside source code."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY is missing. Add it to your local .env file and restart the server.",
        )
    Settings.llm = GoogleGenAI(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), api_key=api_key)
    Settings.embed_model = GoogleGenAIEmbedding(
        model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        api_key=api_key,
    )


@app.get("/", response_class=None)
async def home(request: Request):
    return templates.TemplateResponse(
        "upload_form.html",
        {"request": request, "error": None},
    )


def render_summary(summary: str) -> str:
    """Convert model Markdown to a restricted, safe HTML fragment."""
    normalized_summary = summary.replace("\\r\\n", "\n").replace("\\n", "\n")
    rendered = markdown.markdown(
        normalized_summary,
        extensions=["extra", "sane_lists", "nl2br"],
    )
    return bleach.clean(
        rendered,
        tags=ALLOWED_MARKDOWN_TAGS,
        attributes=ALLOWED_MARKDOWN_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


async def process_upload(file: UploadFile) -> dict[str, str]:
    """Validate, summarize, and clean up one uploaded PDF."""
    original_name = file.filename or "document.pdf"
    if Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

    # Use a generated filename to avoid path traversal and filename collisions.
    saved_path = UPLOAD_DIRECTORY / f"{uuid4().hex}.pdf"
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="PDF must be 20 MB or smaller.")
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")
        saved_path.write_bytes(content)

        configure_models()
        documents = SimpleDirectoryReader(input_files=[str(saved_path)]).load_data()
        if not documents:
            raise HTTPException(status_code=400, detail="No readable text was found in the PDF.")

        nodes = SentenceSplitter(chunk_size=1024).get_nodes_from_documents(documents)
        summary_index = SummaryIndex(nodes)
        vector_index = VectorStoreIndex(nodes)

        summary_tool = QueryEngineTool.from_defaults(
            query_engine=summary_index.as_query_engine(response_mode="tree_summarize"),
            description="Use this tool to summarize the uploaded document comprehensively.",
        )
        vector_tool = QueryEngineTool.from_defaults(
            query_engine=vector_index.as_query_engine(),
            description="Use this tool to find specific facts and details in the uploaded document.",
        )
        query_engine = RouterQueryEngine(
            selector=LLMSingleSelector.from_defaults(),
            query_engine_tools=[summary_tool, vector_tool],
            verbose=True,
        )
        response = await query_engine.aquery(
            "Provide an accurate, readable Markdown summary of the uploaded document. "
            "Use only information present in the document. Add concise headings such as "
            "Document Overview, Key Points, Important Details, Main Findings, and Conclusion "
            "only when they are relevant. Use bullet lists for multiple items and do not "
            "invent missing information."
        )
        summary = str(response).strip()
        if not summary:
            raise HTTPException(status_code=502, detail="The AI returned an empty summary.")
        return {
            "filename": Path(original_name).name,
            "summary": summary,
            "summary_html": render_summary(summary),
        }
    except HTTPException:
        raise
    except Exception as exc:
        # Avoid exposing credentials or full internal exception details to clients.
        print(f"Document processing failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Document processing failed. Check the VS Code terminal for the error details.",
        ) from exc
    finally:
        await file.close()
        try:
            saved_path.unlink(missing_ok=True)
        except OSError:
            pass


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Accept one PDF and return an LLM-generated summary as JSON."""
    result = await process_upload(file)
    return {"filename": result["filename"], "Summary": result["summary"]}


@app.post("/summarize/")
async def summarize_page(request: Request, file: UploadFile = File(...)):
    """Accept one PDF and render the formatted summary page."""
    try:
        result = await process_upload(file)
        return templates.TemplateResponse(
            "results.html",
            {"request": request, "result": result, "error": None},
        )
    except HTTPException as exc:
        return templates.TemplateResponse(
            "upload_form.html",
            {"request": request, "error": exc.detail},
            status_code=exc.status_code,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
