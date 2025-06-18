
---

## ✅ **🌐 Project Overview**

You are building a **modular, microservice-based data analysis system** where:

> 💡 **Users upload a CSV/XLS/XLSX file, enter natural language queries**, and the system uses **Python + LLM** to convert that query into **pandas expressions**, **executes it in a sandboxed environment**, and **displays or exports** the result.

---

## 🧩 **Defined Microservices**

| Service                        | Description                                                                 |
| ------------------------------ | --------------------------------------------------------------------------- |
| **1. File Upload Service**     | Accepts and validates file uploads, stores them temporarily                 |
| **2. Data Reader Service**     | Reads the uploaded file into a pandas DataFrame and extracts schema/preview |
| **3. LLM Query Parser**        | Converts natural language queries to secure pandas expressions              |
| **4. Code Execution Service**  | Safely executes pandas code in a **sandboxed Python environment**           |
| **5. Result Renderer Service** | Converts execution output into tables, summaries, and charts                |
| **6. Exporter Service**        | Exports output as CSV, JSON, XLSX, or PNG files                             |
| **7. Session/Context Manager** | Maintains session history, file context, and follow-up memory               |
| **8. API Gateway**             | Acts as the single entry point, routes requests to other services           |

---

## 📁 **Project Directory Structure**

We’ve outlined a **modular and production-ready structure**:

```
data-agent-system/
├── api_gateway/
├── services/
│   ├── file_upload/
│   ├── data_reader/
│   ├── llm_query_parser/
│   ├── code_executor/
│   ├── result_renderer/
│   ├── exporter/
│   └── session_manager/
├── shared/
├── workers/
├── storage/
├── k8s/                     # (optional, for Kubernetes)
├── tests/
├── docker-compose.yml
├── requirements.txt
└── .env
```

Each service will be containerized with its own `Dockerfile`.

---

## 🔒 **Sandboxing Strategy**

You're planning to **execute pandas code safely**, so we explored sandboxing options:

### Recommended:

* **Ephemeral Docker containers** per execution job (secure, scalable, well-isolated)
* Managed via **Docker SDK** or **Kubernetes Jobs**
* Code executed with **resource limits**, no network access, and strict validation

> You'll implement this when working on the execution engine part.

---

## ⚙️ **Scalability Plan**

To ensure your system can handle multiple users and large workloads:

* Use **Docker Compose** for local orchestration; **Kubernetes** for production
* Deploy **microservices independently** (scale each based on load)
* Use **Redis/Celery workers** to run execution tasks asynchronously
* Use **shared object storage** (e.g., S3 or MinIO) for files and exports
* **Stateless services** where possible; state stored in Redis or DB

---

## 📄 **User Story with Acceptance Criteria**

**User Story**:

> As a user, I want to upload a data file and ask questions in natural language so that I can get instant insights from my dataset without writing code.

**Acceptance Criteria (Single-line format)**:

* User can upload CSV, XLS, or XLSX files.
* User can preview uploaded data.
* User can enter questions in natural language.
* System responds with visual/table output.
* System can export results in multiple formats.
* Invalid files or queries return meaningful error messages.
* Code execution is secure and sandboxed.
* System supports follow-up questions using context.

---

## 🔧 **Tech Stack So Far**

| Layer            | Stack                       |
| ---------------- | --------------------------- |
| Backend Services | FastAPI / Flask             |
| LLM API          | OpenRouter / OpenAI         |
| Code Execution   | Python, Pandas, Docker      |
| Queue System     | Celery + Redis              |
| Storage          | Local FS / MinIO / S3       |
| Orchestration    | Docker Compose / Kubernetes |
| Frontend (TBD)   | Likely React or Streamlit   |
| Export Formats   | CSV, XLSX, JSON, PNG        |

---

## 🧠 What's Next?

You’ve planned everything, so now you can:

* ✅ Start **scaffolding microservices** one by one (begin with file upload + reader).
* 🔜 Later, work on **LLM integration**, **sandbox executor**, and **exporter**.
* 💡 You can request:

  * `docker-compose.yml`
  * Starter code templates
  * API design specs (OpenAPI)
  * CI/CD pipeline plan

---

