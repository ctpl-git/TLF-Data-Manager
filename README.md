# TLF Data Manager

A modular, enterprise-grade data management platform designed to store, clean, validate, search, publish, and share datasets. Built on a package-first architecture, TLF Data Manager separates core logic into reusable **Python** and **npm** packages, then composes them into a deployable platform with a rich set of backend services.

---

## Table of Contents

- [Overview](#overview)
- [Currently Available](#currently-available)
- [Architecture](#architecture)
- [Python Packages](#python-packages)
- [npm Packages](#npm-packages)
- [Platform Services](#platform-services)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

TLF Data Manager is the central data hub of the TLF ecosystem. It provides:

- **Dataset Lifecycle Management** — Create, version, update, and delete datasets with full metadata support.
- **Data Quality Assurance** — Built-in validation, cleaning, and transformation pipelines.
- **Advanced Search & Discovery** — Full-text and faceted search via Elasticsearch or Solr.
- **Secure Sharing** — Role-based access control with public/private dataset publishing.
- **Interoperability** — Import and export in CSV, JSON, Excel, Parquet, and more.
- **Module Integration** — Seamless data flow with Data Analysis, Data Explorer, and other TLF modules.

Everything below this point describes the long-term vision for this repo. For what you can actually install and use **today**, see [Currently Available](#currently-available) — the rest of this README is a roadmap, not a changelog.

---

## Currently Available

One package is built, tested, and ready to use today. Everything else in this README (the platform services, npm packages, web UI, database/search/auth infrastructure) is planned, not yet built.

| Package | Description | Install |
|---|---|---|
| [`tlf-data-cleaning`](tlf-data-cleaning/) | PDF table extraction (`PDFTableExtractor`) + composable cleaning rules (rename, strip, coerce numeric, dedupe, drop/fill missing) + a `CleaningPipeline` that chains them, optionally starting from a PDF and exporting straight to CSV. Solves the concrete problem of turning government census PDFs into the canonical schema `tlf-census-stats` expects. | `pip install tlf-data-cleaning` |

`tlf-data-cleaning` is part of the TLF ("The Living Facts") initiative and has **no runtime dependency** on `tlf-census-stats` or `tlf-statistical-summary` (in the sibling `TLF-Data-Analysis` repo) — they compose via file formats (CSV/canonical schema), not shared code.
See `tlf-data-cleaning`'s own README for the three ways to combine it with those packages.

---

## Architecture

The project follows a **package-first** design:

```
┌─────────────────────────────────────────────────────────────┐
│                    TLF Data Manager Platform                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Web UI     │  │   Admin      │  │   API Gateway    │   │
│  │  (React)     │  │   Dashboard  │  │   (FastAPI)      │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         └─────────────────┼───────────────────┘             │
│                           │                                 │
│  ┌────────────────────────┴───────────────────────────────┐ │
│  │              Platform Services (Orchestration)         │ │
│  │ Dataset Mgmt │ Search │ Auth │ Import/Export │ Publish │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Python pkgs  │  │   npm pkgs   │  │   Storage    │       │
│  │  (Backend)   │  │  (Frontend)  │  │  (DB / S3)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

Each package is **published independently**, allowing external projects to consume only the functionality they need.

---

## Python Packages

| Package | Description |
|---------|-------------|
| `tlf-data-cleaning` | ✅ **Available now.** PDF extraction + composable cleaning rules + pipeline orchestration. |
| `tlf-data-models` | Core Pydantic/SQLAlchemy models for datasets, sources, metadata, cleaning rules, and validation schemas. |
| `tlf-storage-engine` | Database abstraction layer supporting PostgreSQL, MongoDB, or object storage (S3/MinIO) with migration tools. |
| `tlf-api-core` | FastAPI-based framework for standardized CRUD endpoints, pagination, filtering, and response serialization. |
| `tlf-auth-jwt` | JWT authentication, RBAC, and permission decorators for securing endpoints. |
| `tlf-validation-engine` | Schema validation, constraint checking, and integrity enforcement. |
| `tlf-search-indexer` | Elasticsearch/Solr client wrapper for indexing and advanced querying. |
| `tlf-io-formats` | Import/export handlers for CSV, JSON, Excel, Parquet with streaming support. |
| `tlf-publisher` | Dataset sharing service generating public/private links for the Data Publisher module. |
| `tlf-testing-kit` | Shared pytest fixtures, mock data generators, and integration test helpers. |

### Installation

```bash
# What actually exists today:
pip install tlf-data-cleaning

# Planned (not yet published):
pip install tlf-data-models tlf-api-core tlf-auth-jwt
```

---

## npm Packages

*(Planned — none of these exist yet.)*

| Package | Description |
|---------|-------------|
| `@tlf/data-manager-sdk` | TypeScript client SDK for interacting with the Data Manager API. |
| `@tlf/react-data-components` | Reusable React components for dataset tables, metadata editors, and upload widgets. |
| `@tlf/auth-client` | Authentication provider and hooks for JWT login, token refresh, and route guards. |
| `@tlf/search-ui` | React components for faceted search, filters, and results display. |
| `@tlf/data-cleaning-ui` | Visual rule builder and pipeline monitor for cleaning workflows. |
| `@tlf/import-export-tools` | Browser/Node utilities for parsing and generating CSV, JSON, and Excel files. |
| `@tlf/publisher-ui` | Interface for publishing datasets and managing shareable links. |
| `@tlf/admin-dashboard` | Admin layout and widgets for user management, audit logs, and monitoring. |
| `@tlf/data-visualization` | Lightweight chart and preview components for quick dataset exploration. |

### Installation

```bash
npm install @tlf/data-manager-sdk @tlf/react-data-components
```

---

## Platform Services

*(Planned — this orchestration/deployment layer doesn't exist yet. Today, `tlf-data-cleaning` is a standalone Python package, not a service.)*

| Service | Responsibility |
|---------|----------------|
| **Dataset Management Service** | Full lifecycle: versioning, metadata tagging, storage allocation. |
| **Data Ingestion & Cleaning Service** | Handles uploads, applies cleaning rules, runs transformations. |
| **Search & Discovery Service** | Indexes content/metadata; provides keyword, faceted, and advanced query APIs. |
| **Authentication & Authorization Service** | Centralized identity provider with JWT and RBAC enforcement. |
| **Import/Export Service** | Async job queue for multi-format conversion and transfer. |
| **Data Publishing & Sharing Service** | Manages public/private links, access tokens, and Data Publisher integration. |
| **Validation & Quality Service** | Real-time and batch validation for schema compliance and integrity. |
| **Metadata & Cataloging Service** | Manages descriptions, lineage, tags, and categorization. |
| **Integration Gateway Service** | API bridge and event bus for Data Analysis, Data Explorer, and external systems. |
| **Audit & Logging Service** | Tracks access, modifications, and events for compliance and debugging. |
| **Notification Service** | Alerts on updates, cleaning completion, sharing requests, and quota limits. |
| **Storage Management Service** | Monitors usage, backups, archival policies, and multi-tier storage. |

---

## Getting Started

### Prerequisites (for the platform vision described above)

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or MongoDB 6+)
- Elasticsearch 8+ (or Solr 9+)
- Redis 7+ (for caching and job queues)

### Quick Start — using what's available today

```bash
pip install tlf-data-cleaning

# Or from source:
git clone https://github.com/ctpl-git/TLF-Data-Manager.git
cd TLF-Data-Manager
pip install -e ".[dev]"
pytest tests/
```

### Quick Start — full platform vision (not yet buildable)

```bash
# Install Node dependencies
npm install

# Run database migrations
alembic upgrade head

# Start the platform
docker-compose up
```

The API will be available at `http://localhost:8000` and the UI at `http://localhost:3000`.

---

## Development Workflow

1. **Package Development** — Work on individual Python/npm packages in `/packages/`.
2. **Local Testing** — Use `tlf-testing-kit` and storybook for isolated validation.
3. **Platform Integration** — Compose packages in `/services/` and test via Docker Compose.
4. **Publishing** — Packages are published to PyPI and npm independently using CI/CD.
5. **Deployment** — Platform services are containerized and deployed via Kubernetes or Docker Swarm.

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code style and linting
- Writing tests
- Submitting pull requests
- Reporting issues

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ by the TLF Team
</p>
