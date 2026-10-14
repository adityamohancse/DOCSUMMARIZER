<div align="center">

# DocumentSummarizer — Agentic RAG with LlamaIndex

**Turn uploaded PDF documents into concise, AI-generated summaries.**

A Python application built with FastAPI and LlamaIndex that accepts PDF uploads, splits document content into manageable text nodes, and routes a summarization query through LlamaIndex query engines.
</div>

---

## Overview

DocumentSummarizer is a document-processing application designed to make PDF content easier to review. Users upload a PDF through a lightweight web form, and the backend processes the document and returns a generated summary.

The implementation uses LlamaIndex to prepare document nodes and creates both a `SummaryIndex` and a `VectorStoreIndex`. A `RouterQueryEngine` with `LLMSingleSelector` selects between the configured query-engine tools to answer the summarization request.

The repository also includes a Dockerfile for containerized execution.

> **Implementation note:** The current `app.py` configures a Google Generative AI chat model and Google PaLM embeddings. OpenAI and Hugging Face integrations appear as commented alternatives, but they are not currently enabled as active, interchangeable providers. The README describes the checked-in implementation rather than implying that every commented option is ready to use.

## Key Features

- **PDF upload interface:** Upload a PDF from a browser using the included HTML form.
- **PDF validation:** Rejects uploads whose filename does not end in `.pdf`.
- **Document ingestion:** Loads the uploaded PDF with LlamaIndex's `SimpleDirectoryReader`.
- **Text chunking:** Splits document content into nodes with `SentenceSplitter` using a chunk size of 1,024.
- **Summary and retrieval indexes:** Builds a `SummaryIndex` and a `VectorStoreIndex` over the parsed nodes.
- **Query-engine routing:** Uses `RouterQueryEngine` and `LLMSingleSelector` to route the summary request to an appropriate query engine.
- **FastAPI backend:** Exposes the upload workflow through an HTTP endpoint.
- **Container support:** Includes a Dockerfile to run the application in a container.
- **Demo asset:** Includes an animated preview at `static/demo.gif`.

## Technology Stack

| Area | Technologies |
|---|---|
| Language | Python |
| API framework | FastAPI, Uvicorn |
| Document processing | LlamaIndex, `SimpleDirectoryReader`, `SentenceSplitter` |
| Indexing and query | `SummaryIndex`, `VectorStoreIndex`, `RouterQueryEngine` |
| LLM and embeddings in current code | Google Generative AI integration and Google PaLM embeddings integration |
| Web interface | HTML, CSS, Jinja2 templates, FastAPI static files |
| Containerization | Docker |

## Architecture

```text
User
 |
 | Upload a PDF
 v
FastAPI web interface
 |
 v
POST /upload/
 |
 +--> Validate the filename
 |
 +--> Save the uploaded PDF under data/
 |
 +--> Load the PDF with SimpleDirectoryReader
 |
 +--> Split document into nodes (SentenceSplitter)
 |
 +--> Build SummaryIndex and VectorStoreIndex
 |
 +--> Create summary and vector query engines
 |
 +--> Route query using RouterQueryEngine
 |
 v
Generated summary returned as JSON
```

## Request Flow

1. The user opens the web page at `/`.
2. The user selects a PDF and submits the upload form.
3. FastAPI receives the file at `POST /upload/`.
4. The application saves the PDF in the `data/` directory. The current implementation removes existing files in that directory before saving the new upload.
5. LlamaIndex loads the PDF and splits its content into nodes.
6. The application creates summary and vector indexes and configures their query engines.
7. `RouterQueryEngine` routes the request, and the endpoint returns the generated summary as JSON.

## Project Structure

```text
DocumentSummarizer-AgenticRAG-LlamaIndex/
├── app.py                         # FastAPI application and PDF workflow
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container configuration
├── setup.py                       # Package metadata and dependency helper
├── template.py                    # Project-file scaffold helper
├── data/
│   └── Data Quality Trial Task...pdf
├── templates/
│   └── upload_form.html            # PDF upload page
├── static/
│   ├── styles.css                  # Page styling
│   └── demo.gif                    # Demo preview
├── research/
│   └── AgentSummarizerUsingLlamaIndex.ipynb
├── .github/
│   └── workflows/
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11
- `pip`
- A Google AI API credential compatible with the configured model and embedding integrations
- Docker, if you want to run the containerized version

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd DocumentSummarizer-AgenticRAG-LlamaIndex
```

> If this project is stored under a different GitHub repository name, replace the clone URL with the URL of your repository.

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Some dependencies in the current `requirements.txt` are unpinned or sourced directly from Git. If installation fails, review the package compatibility and pin a tested set of versions before deploying.

### 4. Configure environment variables

Create a `.env` file in the project root and store credentials there. **Do not commit `.env` or paste API keys into source code.**

Example `.env.example`:

```dotenv
GOOGLE_API_KEY=replace_with_your_new_api_key
```

The current `app.py` sets a Google API key directly in source and passes an empty key to the configured model constructor. Before running this application, refactor the credential handling to read the key from the environment and pass the same configured credential to the required Google integrations.

For example, add this near the imports in `app.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is not configured")
```

Then use `GOOGLE_API_KEY` in the relevant Google model and embedding constructors, after confirming the API and model names are supported by the installed dependency versions. Add `python-dotenv` to `requirements.txt` if you use this local `.env` loading approach.

Make sure `.env` is listed in `.gitignore` (it already is in the supplied repository).

### 5. Start the application

The current `app.py` exposes a FastAPI application object named `app`.

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open the browser at:

- Web upload page: `http://127.0.0.1:8000/`
- FastAPI interactive API docs: `http://127.0.0.1:8000/docs`

### 6. Upload a PDF

1. Open the web upload page.
2. Choose a PDF file.
3. Submit the form.
4. The API returns a JSON response containing the filename and generated summary.

Example response shape:

```json
{
  "filename": "example.pdf",
  "Summary": "A generated summary of the uploaded document."
}
```

The text above illustrates the response structure; the actual summary depends on the uploaded document and configured model.

## API Reference

### `GET /`

Returns the HTML page containing the PDF upload form.

### `POST /upload/`

Accepts a multipart file upload.

**Request**

- Content type: `multipart/form-data`
- Form field: `file`
- Expected file type: PDF

**Successful response**

Returns the uploaded filename and generated summary.

**Error response**

A filename that does not end in `.pdf` results in HTTP `400` with an error detail.

> **Current behavior to be aware of:** the application replaces files in the shared `data/` directory for each upload. This is suitable only for a simple single-user demonstration, not concurrent or multi-user production use.

## Run with Docker

Build the image:

```bash
docker build -t document-summarizer .
```

Run the container:

```bash
docker run --rm -p 8000:8000 \
  -e GOOGLE_API_KEY="your_new_api_key" \
  document-summarizer
```

Then open `http://localhost:8000/`.

For PowerShell, use:

```powershell
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY="your_new_api_key" document-summarizer
```

Do not put real credentials in the Dockerfile or commit them to Git. The supplied Dockerfile currently enables Uvicorn reload; for a production deployment, remove `--reload` and use appropriate deployment, logging, and resource settings.

## Security and Production Considerations

This repository is a project/demo implementation and should be hardened before being exposed to untrusted users.

- **Rotate exposed credentials:** If a real API key was ever committed or shared, revoke it and create a replacement. Removing it from the latest file does not invalidate the exposed key.
- **Load secrets from environment variables:** Never hardcode provider keys in Python files.
- **Validate uploads:** Enforce file size limits and validate content rather than relying only on the filename extension.
- **Use safe file handling:** Generate server-side filenames and avoid trusting user-supplied paths.
- **Avoid deleting shared upload data:** The current upload route removes existing files from `data/`. Use isolated temporary storage or per-user storage if supporting multiple users.
- **Add error handling and cleanup:** Handle malformed PDFs, model/provider failures, and temporary-file cleanup explicitly.
- **Review dependency compatibility:** Pin and test compatible versions of LlamaIndex, LangChain, and provider packages.
- **Add tests and observability:** Cover upload validation, PDF processing, provider failures, and response formats before deployment.
- **Harden deployment:** Disable development reload, configure timeouts and resource limits, and use HTTPS through the deployment platform.

## Current Scope and Future Improvements

Potential next steps, not claims about existing functionality:

- Support configurable, tested LLM and embedding providers through environment-based settings.
- Add document-specific question answering and return source citations.
- Stream progress and results for large PDFs.
- Add upload size limits, MIME/content validation, and isolated temporary storage.
- Add automated tests and a GitHub Actions workflow for linting and test execution.
- Add structured logging, timeouts, and deployment-specific configuration.

## CI/CD and Cloud Deployment

The repository contains a `.github/workflows/` directory, but the supplied archive does not include an active workflow definition. Therefore, automated CI/CD and AWS ECR-to-EC2 deployment should be described as configured only after the workflow files and deployment process are present and verified.

To document a real deployment, add the public demo URL and explain the actual workflow, registry, host, secrets configuration, and release process.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make a focused change and add or update tests where appropriate.
4. Run the application and verify the affected behavior.
5. Open a pull request with a clear description of the change.

## License

See [`LICENSE`](LICENSE) for the license terms.

---

<div align="center">

**Built with Python, FastAPI, and LlamaIndex**

[GitHub Profile](https://github.com/adityamohancse) · [LinkedIn](https://www.linkedin.com/in/adityamohancse)

</div>
